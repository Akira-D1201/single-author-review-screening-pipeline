# PICOS-based Title and Abstract Screening Script

A lightweight, auditable Python script for title and abstract screening in a systematic review and meta-analysis.

This script was developed for a systematic review on non-pharmacological interventions for cognitive decline in older adults. It is used at the title and abstract screening stage, before full-text screening.

---

## Background

Systematic reviews require screening thousands of records. Manual screening is time-consuming and difficult to reproduce. This script was written to make the first screening stage faster, more consistent, and more transparent.

It is not intended to replace human reviewers. It is a support tool that flags potential records and produces an auditable decision log.

---

## What This Script Does

- Reads a CSV or Excel file containing titles and abstracts.
- Matches predefined PICOS keyword lists against titles and abstracts.
- Flags records for population, intervention, comparator, outcome, and study design.
- Produces an auditable decision log for each record.
- Sends uncertain records to full-text screening instead of excluding them early.

---

## Key Features

- **PICOS-based keyword matching**: separate keyword lists for population, intervention, comparator, outcome, and study design.
- **Flexible comparator handling**: the comparator is not used as a hard exclusion criterion at the title and abstract stage.
- **Study design and RCT detection**: flags randomized controlled trials and other study designs.
- **Auditable output**: each record includes a decision, a reason, and the matched terms.
- **Reproducible**: keyword lists and decision rules are defined in the code.
- **Lightweight**: only requires pandas and openpyxl.
- **No API key required**: runs locally without external services.

---

## Comparator Handling

During title and abstract screening, many records do not mention a comparator in the abstract even when they have one in the full text. Excluding these records early can lead to missed eligible studies.

To reduce this risk, the script does not use the comparator as a hard exclusion criterion. Instead, records without comparator signals are flagged as `pending_full_text` and passed to full-text screening.

Possible `C_status` values:

- `possible`: comparator terms were found
- `likely_via_rct_design`: RCT terms were found, so a comparator is likely
- `possible_via_study_design`: study design terms were found
- `pending_full_text`: no comparator signal found, sent to full text
- `explicit_no_comparator`: single-arm, uncontrolled, or case series

Only records with `explicit_no_comparator` are excluded at this stage.

---

## Study Design Handling

Possible `S_status` values:

- `mentioned`: study design terms were found
- `pending_full_text`: no study design signal found

---

## Requirements

Install dependencies:

pip install -r requirements.txt

Required packages:

- pandas
- openpyxl

---

## Usage

For Excel input:

python screening.py --input records.xlsx --output screening_results.xlsx

For CSV input:

python screening.py --input records.csv --output screening_results.csv

If the Excel file has multiple sheets:

python screening.py --input records.xlsx --output screening_results.xlsx --sheet Sheet1

---

## Input Columns

The script detects common column names automatically.

Expected columns:

- title
- abstract
- authors
- year
- doi
- pmid

At least one of title or abstract is required.

---

## Output Fields

- `record_id`
- `title`
- `abstract`
- `P_mentioned`: population terms found
- `I_mentioned`: intervention terms found
- `C_mentioned`: comparator terms found
- `O_mentioned`: outcome terms found
- `S_mentioned`: study design terms found
- `RCT_mentioned`: RCT terms found
- `explicit_no_comparator`: record explicitly states no comparator
- `C_status`: comparator status
- `S_status`: study design status
- `decision`: screening decision
- `reason`: reason for the decision
- `matched_P`, `matched_I`, `matched_C`, `matched_O`, `matched_S`, `matched_RCT`

---

## Limitations

- Keyword matching is rule-based and does not understand context.
- Some eligible records may be missed if the abstract does not contain the expected terms.
- Final inclusion decisions require full-text screening by human reviewers.
- The keyword lists are tailored to this specific review question and may need adaptation for other topics.
- This script is a screening support tool, not a substitute for human judgment.

---

## Reproducibility

The keyword lists, decision rules, and output structure are defined in the script and can be reused or adapted for other systematic reviews.

---

## Context

This script was developed as part of a systematic review and meta-analysis on non-pharmacological interventions for cognitive decline in older adults. The review also includes an activation likelihood estimation (ALE) analysis to examine shared neural correlates across interventions.

---

## License

For academic research use.
