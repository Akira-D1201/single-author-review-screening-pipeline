# AI‑assisted screening pipeline for single‑author systematic reviews
Auxiliary Python scripts for preliminary literature screening for ongoing systematic‑review projects.

## Project Background
Traditional PRISMA guidelines recommend dual‑independent screening to reduce false‑negative risks, which creates practical challenges for single‑author systematic reviews.
PRISMA‑trAIce is the official AI‑extension reporting standard for evidence synthesis. It permits automated tools for preliminary screening under key constraints: final inclusion‑exclusion decisions must be human‑operated, and all screening rules should be fully documented for reproducibility.

This workflow is designed for single‑author review scenarios to mitigate false‑negative risks caused by hard keyword exclusion.

## Workflow
1. Load bibliographic CSV exported from reference‑management software
2. Negative‑keyword coarse filtering: remove obviously irrelevant records
3. LLM‑driven preliminary screening
4. Secondary positive‑keyword rescue re‑check:
All records discarded by negative‑keyword filtering are re‑evaluated using predefined positive topic keywords.
Records matching positive keywords are flagged for manual review, to recover studies mistakenly eliminated by negative keyword rules.
Records with zero positive‑keyword matches are marked low‑risk for false‑negatives and discarded.
5. Export processed CSV output compatible with ASReview‑LAB for final manual screening

> Important Note
Automation and large‑language models are **only pre‑screening aids**. All final inclusion or exclusion judgements must be completed manually by researchers.

## Repository Structure
- `src/`: Core pipeline source code
- `demo/`: Contains artificially generated demonstration metadata only. **No real bibliographic data included.**

## Installation
Run this command inside your terminal:
`pip install -r requirements.txt`

## Usage
1. Prepare your bibliographic CSV export file from reference manager
2. Modify keyword lists inside script configuration block
3. Set environment variable for LLM API key locally via system environment or local `.env` file
4. Execute main screening script
5. Obtain output CSV file ready for importing into ASReview‑LAB

## Known Limitations & Risk Warnings
1. Keyword‑based filtering performance fully depends on your keyword lists. Poorly‑defined keywords will introduce high false‑positive or false‑negative rates.
2. LLM outputs are non‑deterministic. LLM suggestions cannot replace human inspection.
3. Real literature datasets shall never be committed to this repository due to copyright restrictions.
4. API credentials must be loaded from environment variables or local `.env`. Hard‑coding secrets in source code and pushing to public repository will lead to credential leakage.
5. This is research‑oriented auxiliary code, **not production‑grade software**. No performance guarantee for screening results. End‑users take full responsibility for all outputs.

## Reference
PRISMA‑trAIce reporting guideline for AI‑assisted systematic reviews.



