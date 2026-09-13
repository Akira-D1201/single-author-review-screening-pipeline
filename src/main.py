#!/usr/bin/env python3
"""
Title and abstract screening script for systematic reviews and meta-analyses.

This script combines rule-based PICOS keyword matching with optional LLM
API assistance. It is designed for the early screening stage.

The comparator (C) is kept in the final eligibility framework, but it is
NOT hard-excluded during title/abstract screening. Records without comparator
signals are flagged as "pending_full_text" and sent to full-text screening.

Requirements:
    pandas
    openpyxl
    openai
    python-dotenv

Usage:
    # Run with local rule-based screening only
    python src/main.py --input records.xlsx --output screening_results.xlsx

    # Run with API assistance (requires .env file)
    python src/main.py --input records.xlsx --output screening_results.xlsx --use_api
"""

import argparse
import os
import re
import json
from typing import List, Optional, Tuple

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Column aliases
# ---------------------------------------------------------------------------

COLUMN_ALIASES = {
    "title": ["title", "article title", "ti", "标题", "题名", "篇名"],
    "abstract": ["abstract", "ab", "摘要", "文摘"],
    "authors": ["authors", "author", "au", "作者"],
    "year": ["year", "publication year", "py", "年份", "发表年份"],
    "doi": ["doi", "digital object identifier"],
    "pmid": ["pmid", "pubmed id", "pubmed pmid"],
}


# ---------------------------------------------------------------------------
# Keyword lists (Rule-based screening)
# ---------------------------------------------------------------------------

POPULATION_TERMS = [
    "older adults", "older adult", "elderly", "aged", "senior", "seniors",
    "geriatric", "geriatrics", "cognitive impairment", "cognitive decline",
    "dementia", "mild cognitive impairment", "mci", "alzheimer",
    "alzheimer's disease", "老年人", "老人", "高龄", "认知障碍", "认知衰退",
    "痴呆", "轻度认知障碍", "阿尔茨海默",
]

INTERVENTION_TERMS = [
    "non-pharmacological", "nonpharmacological", "non-drug",
    "non-drug intervention", "exercise", "physical activity",
    "cognitive training", "cognitive stimulation", "reminiscence therapy",
    "music therapy", "diet", "nutrition", "mindfulness", "tai chi", "yoga",
    "acupuncture", "behavioral intervention", "behavioural intervention",
    "psychosocial", "occupational therapy", "multicomponent", "multi-component",
    "非药物", "非药物治疗", "运动", "体育锻炼", "认知训练", "认知刺激",
    "回忆疗法", "音乐疗法", "饮食", "营养", "正念", "太极", "瑜伽",
    "针灸", "行为干预", "心理社会", "作业疗法", "多组分", "多成分",
]

COMPARATOR_TERMS = [
    "control", "controls", "comparator", "comparison group", "usual care",
    "routine care", "standard care", "waitlist", "waiting list", "placebo",
    "sham", "active control", "attention control", "no intervention",
    "对照", "对照组", "比较组", "常规护理", "常规照护", "标准护理",
    "等待名单", "候补名单", "安慰剂", "假刺激", "主动对照", "注意力对照",
    "无干预",
]

NO_COMPARATOR_TERMS = [
    "single-arm", "single arm", "uncontrolled", "no control group",
    "case series", "case report", "before-after", "pre-post",
    "self-controlled", "单臂", "无对照组", "病例系列", "病例报告",
    "自身前后", "前后自身",
]

STUDY_DESIGN_TERMS = [
    "randomized controlled trial", "randomised controlled trial", "rct",
    "randomized", "randomised", "controlled trial", "clinical trial",
    "randomized clinical trial", "randomised clinical trial",
    "随机对照", "随机", "对照试验", "临床试验",
]

RCT_TERMS = [
    "randomized controlled trial", "randomised controlled trial", "rct",
    "randomized clinical trial", "randomised clinical trial",
    "随机对照", "随机对照试验",
]

OUTCOME_TERMS = [
    "cognitive function", "cognition", "memory", "executive function",
    "attention", "mmse", "moca", "adas-cog", "认知功能", "认知",
    "记忆", "执行功能", "注意力", "简易智力状态检查", "蒙特利尔认知评估",
]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def contains_term(text: str, term: str) -> bool:
    """Return True if the term appears in the text."""
    term_lower = term.lower()
    if re.search(r"[\u4e00-\u9fff]", term_lower):
        return term_lower in text
    pattern = r"(?<![a-z0-9])" + re.escape(term_lower) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def find_matches(text: str, terms: List[str]) -> List[str]:
    """Return all terms that appear in the text."""
    return [term for term in terms if contains_term(text, term)]


def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    """Find the first matching column name from a list of aliases."""
    lower_map = {str(col).strip().lower(): col for col in df.columns}
    for alias in aliases:
        key = alias.strip().lower()
        if key in lower_map:
            return lower_map[key]
    return None


def read_input(path: str, sheet: Optional[str] = None) -> pd.DataFrame:
    """Read a CSV or Excel input file."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        try:
            return pd.read_csv(path)
        except UnicodeDecodeError:
            try:
                return pd.read_csv(path, encoding="gbk")
            except UnicodeDecodeError:
                return pd.read_csv(path, encoding="gb18030")
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path, sheet_name=sheet if sheet else 0)
    raise ValueError("Unsupported input format. Use .csv, .xlsx, or .xls.")


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize title, abstract, and optional metadata columns."""
    title_col = find_column(df, COLUMN_ALIASES["title"])
    abstract_col = find_column(df, COLUMN_ALIASES["abstract"])

    if title_col is None and abstract_col is None:
        raise ValueError("No title or abstract column found. Please check the input file.")

    out = pd.DataFrame()
    out["record_id"] = range(1, len(df) + 1)
    out["title"] = df[title_col].fillna("").astype(str) if title_col else ""
    out["abstract"] = df[abstract_col].fillna("").astype(str) if abstract_col else ""

    optional_columns = {
        "authors": COLUMN_ALIASES["authors"],
        "year": COLUMN_ALIASES["year"],
        "doi": COLUMN_ALIASES["doi"],
        "pmid": COLUMN_ALIASES["pmid"],
    }
    for out_col, aliases in optional_columns.items():
        col = find_column(df, aliases)
        out[out_col] = df[col].fillna("").astype(str) if col else ""

    out["text"] = (out["title"] + " " + out["abstract"]).str.lower()
    return out


# ---------------------------------------------------------------------------
# Rule-based logic
# ---------------------------------------------------------------------------

def determine_c_status(c_mentioned: bool, s_mentioned: bool, rct_mentioned: bool, explicit_no_c: bool) -> str:
    """Determine comparator status for title and abstract screening."""
    if explicit_no_c:
        return "explicit_no_comparator"
    if c_mentioned:
        return "possible"
    if rct_mentioned:
        return "likely_via_rct_design"
    if s_mentioned:
        return "possible_via_study_design"
    return "pending_full_text"


def determine_s_status(s_mentioned: bool) -> str:
    """Determine study design status for title and abstract screening."""
    return "mentioned" if s_mentioned else "pending_full_text"


def make_rule_decision(row: pd.Series) -> Tuple[str, str]:
    """Make a title and abstract screening decision based on rules."""
    if row["explicit_no_comparator"]:
        return ("Exclude", "Explicit no comparator / single-arm / case series")
    if not row["P_mentioned"] and not row["I_mentioned"]:
        return ("Exclude", "No population or intervention signal in title/abstract")
    if row["P_mentioned"] and row["I_mentioned"]:
        return ("Full-text screening", "Population and intervention signals present; confirm C/O/S in full text")
    return ("Full-text screening (uncertain)", "Some PICOS signals missing; do not exclude at title/abstract stage")


# ---------------------------------------------------------------------------
# Optional API logic
# ---------------------------------------------------------------------------

def get_api_client() -> Optional[OpenAI]:
    """Initialize the OpenAI-compatible API client if key is available."""
    if not OPENAI_AVAILABLE:
        print("Warning: openai package not installed. API screening disabled.")
        return None
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Warning: DEEPSEEK_API_KEY not found in environment. API screening disabled.")
        return None
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )


def api_screen_record(client: OpenAI, title: str, abstract: str) -> Tuple[str, str]:
    """Use LLM API to screen a single record."""
    prompt = f"""
    You are an expert systematic review screener. 
    Your task is to screen the following title and abstract based on the PICOS criteria:
    - Population: Older adults with cognitive decline or dementia.
    - Intervention: Non-pharmacological interventions (e.g., exercise, cognitive training).
    - Comparator: Any control group (usual care, waitlist, placebo). If not mentioned, assume it might exist.
    - Outcome: Cognitive function (e.g., MMSE, MoCA).
    - Study Design: Randomized controlled trials (RCTs).

    IMPORTANT: Do NOT exclude the record just because the comparator is not mentioned in the abstract. If it's an RCT, flag it for full-text screening.

    Title: {title}
    Abstract: {abstract}

    Return a JSON object with two keys: "decision" (either "Exclude" or "Full-text screening") and "reason" (a brief explanation).
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful systematic review screening assistant. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("decision", "Full-text screening"), result.get("reason", "API decision")
    except Exception as e:
        print(f"API error: {e}. Falling back to rule-based decision.")
        return "Full-text screening (uncertain)", "API error, fallback to full-text"


# ---------------------------------------------------------------------------
# Main screening pipeline
# ---------------------------------------------------------------------------

def screen_dataframe(df: pd.DataFrame, use_api: bool = False) -> pd.DataFrame:
    """Run title and abstract screening and return a structured result table."""
    df = prepare_dataframe(df)

    term_groups = {
        "P": POPULATION_TERMS,
        "I": INTERVENTION_TERMS,
        "C": COMPARATOR_TERMS,
        "O": OUTCOME_TERMS,
        "S": STUDY_DESIGN_TERMS,
    }

    for prefix, terms in term_groups.items():
        matches = df["text"].apply(lambda text: find_matches(text, terms))
        df[f"matched_{prefix}"] = matches.apply(lambda items: "; ".join(items))
        df[f"{prefix}_mentioned"] = matches.apply(bool)

    rct_matches = df["text"].apply(lambda text: find_matches(text, RCT_TERMS))
    df["matched_RCT"] = rct_matches.apply(lambda items: "; ".join(items))
    df["RCT_mentioned"] = rct_matches.apply(bool)

    df["explicit_no_comparator"] = df["text"].apply(
        lambda text: any(contains_term(text, term) for term in NO_COMPARATOR_TERMS)
    )

    df["C_status"] = df.apply(
        lambda row: determine_c_status(
            row["C_mentioned"],
            row["S_mentioned"],
            row["RCT_mentioned"],
            row["explicit_no_comparator"],
        ),
        axis=1,
    )
    df["S_status"] = df["S_mentioned"].apply(determine_s_status)

    # Initialize API client if requested
    client = get_api_client() if use_api else None

    decisions = []
    for _, row in df.iterrows():
        rule_decision, rule_reason = make_rule_decision(row)
        
        # If API is enabled and rule-based decision is uncertain, use API
        if client and "uncertain" in rule_decision:
            api_decision, api_reason = api_screen_record(client, row["title"], row["abstract"])
            decisions.append((api_decision, f"API: {api_reason} (Rule: {rule_reason})"))
        else:
            decisions.append((rule_decision, rule_reason))

    df["decision"] = [d[0] for d in decisions]
    df["reason"] = [d[1] for d in decisions]

    output_columns = [
        "record_id", "title", "abstract", "authors", "year", "doi", "pmid",
        "P_mentioned", "I_mentioned", "C_mentioned", "O_mentioned", "S_mentioned",
        "RCT_mentioned", "explicit_no_comparator", "C_status", "S_status",
        "decision", "reason",
        "matched_P", "matched_I", "matched_C", "matched_O", "matched_S", "matched_RCT",
    ]

    for col in output_columns:
        if col not in df.columns:
            df[col] = ""

    return df[output_columns]


def save_output(df: pd.DataFrame, output_path: str) -> None:
    """Save screening results to CSV or Excel."""
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".csv":
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return
    if ext in [".xlsx", ".xls"]:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Screening_Results", index=False)
            summary = df["decision"].value_counts().reset_index()
            summary.columns = ["decision", "count"]
            summary.to_excel(writer, sheet_name="Summary", index=False)
        return
    raise ValueError("Unsupported output format. Use .csv, .xlsx, or .xls.")


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Title and abstract screening for systematic review and meta-analysis.")
    parser.add_argument("--input", required=True, help="Input CSV or Excel file.")
    parser.add_argument("--output", required=True, help="Output CSV or Excel file.")
    parser.add_argument("--sheet", default=None, help="Excel sheet name or index. Default: first sheet.")
    parser.add_argument("--use_api", action="store_true", help="Use LLM API for uncertain records.")
    args = parser.parse_args()

    print(f"Reading input file: {args.input}")
    raw_df = read_input(args.input, sheet=args.sheet)
    print(f"Loaded {len(raw_df)} records.")

    screened_df = screen_dataframe(raw_df, use_api=args.use_api)
    save_output(screened_df, args.output)

    print(f"Saved screening results to: {args.output}")
    print("Decision summary:")
    print(screened_df["decision"].value_counts().to_string())


if __name__ == "__main__":
    main()
