import pandas as pd
import time
import os
from openai import OpenAI
from dotenv import load_dotenv

# Set TEST_RUN_MAX = 200 for small test; set to None to process full dataset
# ====================== Configuration Section ======================
# Local input/output files (stored locally, NOT pushed to GitHub)
INPUT_CSV = "zotero_all.csv"
OUTPUT_CSV = "screen_mci_new_asreview_ready.csv"

LOG1 = "screen_log1.csv"
LOG2 = "screen_log2.csv"
TEMP_A = "_temp_a.csv"
TEMP_B = "_temp_b.csv"

MODEL = "deepseek-flash"
SLEEP_SEC = 0.7
TEST_RUN_MAX = None   # Set 200 for test sample; None for full run
# =================================================================

# Load secret key from local .env file, .env will NOT be committed to GitHub
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

if not API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY not found in local .env file!")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

PROMPT = """Inclusion criteria (ALL four items must be satisfied for output: include):
1. Population: older adults with Mild Cognitive Impairment (MCI)
2. Intervention: non‑pharmacological behavioral interventions (exercise, cognitive training, mindfulness, multi‑domain combined intervention, etc.)
3. Study design: original randomized controlled trial (RCT), RCT must be explicitly stated in abstract
4. Outcome: cognitive‑function‑related outcomes

Exclusion rule: output exclude if ANY exclusion item is matched, no need to check inclusion criteria.
Exclusion list: reviews, meta‑analyses, systematic reviews, case reports, study protocols, animal experiments, brain stimulation interventions, pharmacological/drug interventions, non‑MCI populations, non‑RCT studies.

Decision rules:
Sufficient information + satisfy all four inclusion criteria → include
Sufficient information + hit any exclusion item → exclude
Insufficient information for confident judgement → uncertain

Only output one single word: include / exclude / uncertain. Do NOT add any extra explanation.
"""

# Local blacklist keywords: skip LLM API call if matched
BLACK_WORDS = [
    "meta‑analysis", "meta analysis", "systematic review", "system review",
    "review", "meta分析", "系统综述",
    "animal", "rat", "mouse", "mice", "大鼠", "小鼠", "动物实验",
    "alzheimer", "阿尔茨海默",
    "drug", "pharmacological", "药物", "pharmaceutical",
    "case report", "case series", "病例报告", "病例系列"
]


def call_llm(title: str, abstract: str) -> str:
    text = f"Title:{title}\nAbstract:{abstract}"
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": PROMPT + "\n" + text}],
            temperature=0.0,
            max_tokens=10
        )
        ans = resp.choices[0].message.content.strip().lower()
        if ans in ("include", "exclude", "uncertain"):
            return ans
        return "uncertain"
    except Exception as e:
        print(f"API Exception:{e}")
        return "uncertain"


def safe_save(df, path_a, path_b):
    """Double backup: save dataframe to two separate csv files to avoid data loss"""
    df.to_csv(path_a, index=False, encoding="utf-8-sig")
    df.to_csv(path_b, index=False, encoding="utf-8-sig")


def main():
    # Resume from previous breakpoint if log files exist
    if os.path.exists(LOG1) and os.path.exists(LOG2):
        df = pd.read_csv(LOG1, encoding="utf-8-sig")
        print(f"Log files detected, resume previous run, processed records: {len(df)}")
    else:
        df_raw = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
        df = df_raw.copy()
        df["ai_decision"] = ""
        df["label_included"] = ""
        safe_save(df, LOG1, LOG2)

    total_rows = len(df)
    cnt = 0
    for idx, row in df.iterrows():
        # Skip records already processed
        if row["ai_decision"] != "":
            continue

        if TEST_RUN_MAX is not None and cnt >= TEST_RUN_MAX:
            print("Reach TEST_RUN_MAX threshold, sample run finished")
            break

        t = str(row["Title"]) if pd.notna(row["Title"]) else ""
        a = str(row["Abstract Note"]) if pd.notna(row["Abstract Note"]) else ""
        full_low = (t + " " + a).lower()

        dec = None
        # Case 1: empty title or empty abstract
        if len(t.strip()) == 0 or len(a.strip()) == 0:
            print(f"idx={idx} Empty title or abstract → uncertain")
            dec = "uncertain"
        # Case 2: hit local blacklist keywords, skip LLM API
        elif any(w in full_low for w in BLACK_WORDS):
            print(f"idx={idx} Hit blacklist keywords → exclude, skip API call")
            dec = "exclude"
        # Case3: send request to DeepSeek LLM
        else:
            print(f"idx={idx} Call DeepSeek LLM API")
            dec = call_llm(t, a)
            time.sleep(SLEEP_SEC)

        df.at[idx, "ai_decision"] = dec
        if dec == "include":
            df.at[idx, "label_included"] = 1
        elif dec == "exclude":
            df.at[idx, "label_included"] = 0
        else:
            df.at[idx, "label_included"] = ""

        cnt += 1
        safe_save(df, LOG1, LOG2)

    # Export final output file ready for ASReview‑LAB import
    safe_save(df, OUTPUT_CSV, TEMP_A)
    print("\n======== Processing Complete =========")
    print(f"Output file path: {OUTPUT_CSV}")
    print(df["ai_decision"].value_counts())


if __name__ == "__main__":
    main()
