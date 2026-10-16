# Example & Test Manuscripts

This directory contains benchmark manuscripts and test fixtures used for automated validation testing in CatScan.

---

## 1. JACoW (Particle Accelerator Conferences)

| File | Type | Category | Description |
| :--- | :--- | :--- | :--- |
| `JACoW_MSWord_Style_Guide.docx` | Word (`.docx`) | Benchmark | Official JACoW Word template and style guide. Zero title errors. |
| `word_jacow_issues.docx` | Word (`.docx`) | Test Fixture | JACoW Word document containing intentional title capitalization errors. |
| `paper.tex` | LaTeX (`.tex`) | Benchmark | Official JACoW LaTeX template manuscript. |
| `latex_jacow_perfect.tex` | LaTeX (`.tex`) | Benchmark | Clean JACoW LaTeX manuscript (0 issues, valid citations). |
| `latex_jacow_issues.tex` | LaTeX (`.tex`) | Test Fixture | JACoW LaTeX manuscript with 5 intentional citation violations (`et al.`, DOI format, volume/issue, prefix). |

---

## 2. PASJ (Particle Accelerator Society of Japan)

| File | Type | Category | Description |
| :--- | :--- | :--- | :--- |
| `PASJ_Sample_Paper.docx` | Word (`.docx`) | Benchmark | Official PASJ 2026 Japanese Word manuscript template (`TeXtemplate2026.docx`). Zero errors across all 10 sections. |
| `word_pasj_issues.docx` | Word (`.docx`) | Test Fixture | PASJ Word manuscript with intentional violations (missing English title, full-width author comma, Japanese in abstract, full-width punctuation). |
| `PASJ_Sample_Paper.tex` | LaTeX (`.tex`) | Benchmark | Official PASJ 2026 LaTeX template manuscript (`TeXtemplate2026.tex`). Clean reference list. |
| `latex_pasj_perfect.tex` | LaTeX (`.tex`) | Benchmark | Standard PASJ Japanese compliant LaTeX test case (0 issues). |
| `latex_pasj_issues.tex` | LaTeX (`.tex`) | Test Fixture | PASJ LaTeX manuscript containing 14 intentional violations (documentclass, missing Japanese title, full-width delimiter, Japanese abstract, figure caption rules, punctuation). |

---

## 3. Usage in Automated Tests

These files are loaded as test fixtures in `backend/tests/`:
- `test_example_suite.py`: End-to-end regression tests verifying that benchmark papers pass and issue papers trigger expected errors.
- `test_pasj_validation.py`: Verification of PASJ Word and LaTeX checkers against official templates.
- `scripts/populate_indico_papers.py`: Populates an Indico event with all 9 papers for live integration testing.
