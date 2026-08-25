# FeverPAIN & Centor Sore Throat Calculator

A production-grade, zero-dependency Python implementation of the **FeverPAIN Score**, **Centor Criteria**, and **Modified Centor (McIsaac) Score** for acute sore throat evaluation and antimicrobial stewardship.

Implements clinical decision rules aligned with **NICE Guideline NG84** (*Sore throat (acute): antimicrobial prescribing*), **Little et al. (BMJ 2013)**, **Centor et al. (Med Decis Making 1981)**, and **McIsaac et al. (CMAJ 1998)**.

---

## Clinical Background & Evidence

Acute sore throat (pharyngitis/tonsillitis) is one of the most common presentations in primary care and emergency departments. The vast majority of episodes are viral in etiology (rhinovirus, coronavirus, adenovirus, Epstein-Barr virus), for which antibiotics provide negligible benefit while contributing to antimicrobial resistance and adverse drug events.

**Group A Streptococcal (GAS)** pharyngitis (*Streptococcus pyogenes*) represents ~10–30% of pediatric and ~5–15% of adult sore throats. Validated clinical scoring systems allow clinicians to estimate GAS likelihood and safely withhold or delay antibiotic prescriptions.

---

## Scoring Systems & Decision Rules

### 1. FeverPAIN Score (0–5 Points)
Validated in the PRISM trial (*Little et al., BMJ 2013;347:f4376*):

| Item | Criterion | Score |
| :--- | :--- | :---: |
| **F** | **F**ever in the past 24 hours (reported or measured >37.5 °C) | +1 |
| **P** | **P**us on tonsils / tonsillar exudate | +1 |
| **A** | **A**ttend rapidly (symptom duration $\le 3$ days) | +1 |
| **I** | Severely **I**nflamed tonsils (marked erythema or swelling) | +1 |
| **N** | **N**o cough or coryza (absence of cough and runny nose) | +1 |

#### FeverPAIN Stratification & Prescribing Strategy (NICE NG84):
- **Score 0–1 (13%–18% Strep Probability)**: **No antibiotic prescription**. Recommend symptomatic relief (paracetamol, ibuprofen, hydration, lozenges).
- **Score 2–3 (34%–40% Strep Probability)**: **Delayed (back-up) prescription** or consider Rapid Antigen Detection Test (RADT) / throat culture. Instruct patient to collect antibiotics only if symptoms worsen or do not begin improving within 3–5 days.
- **Score 4–5 (62%–65% Strep Probability)**: **Immediate antibiotic prescription** (or delayed script depending on clinical context and frailty).

---

### 2. Centor Criteria (0–4 Points)
Published by *Centor et al., Med Decis Making 1981;1(3):239-246*:

1. Tonsillar exudate (+1)
2. Tender anterior cervical lymphadenopathy (+1)
3. History of fever (>38.0 °C / 100.4 °F) (+1)
4. Absence of cough (+1)

---

### 3. Modified Centor (McIsaac) Score (-1 to 5 Points)
Adds age-based risk weighting (*McIsaac et al., CMAJ 1998;158(1):75-83*):

- **Age 3–14 years**: +1 point
- **Age 15–44 years**: 0 points
- **Age $\ge 45$ years**: -1 point

---

## Emergency Red Flags

Outpatient scoring systems are contraindicated if emergency red flags are present. The tool automatically detects and escalates:
- Stridor, respiratory distress, or upper airway obstruction (suspect epiglottitis).
- Trismus (difficulty opening mouth) or severe asymmetric palatal swelling / uvular deviation (suspect peritonsillar abscess / quinsy).
- Inability to swallow liquids/saliva or drooling.
- Signs of systemic sepsis (tachycardia, hypotension, cyanosis, altered mental state).

---

## Antibiotic Stewardship & Regimens (NICE NG84 / IDSA)

| Scenario | Recommended Drug | Dosage & Regimen | Duration |
| :--- | :--- | :--- | :--- |
| **First-Line** | Phenoxymethylpenicillin (Penicillin V) | Adult: 500 mg QDS or 1000 mg BD<br>Pediatric: 12.5 mg/kg QDS (or age-banded) | 5–10 days |
| **First-Line Alternative** | Amoxicillin | Adult: 500 mg TDS<br>Pediatric: 25–50 mg/kg/day in 2–3 divided doses | 7–10 days |
| **Penicillin Allergy (Mild/Rash)** | Cefalexin (Cephalexin) | Adult: 500 mg BD/TDS<br>Pediatric: 12.5–25 mg/kg BD | 5–10 days |
| **Severe Penicillin Allergy (Anaphylaxis)** | Clarithromycin or Erythromycin | Clarithromycin 250–500 mg BD (Adult) / 7.5 mg/kg BD (Peds) | 5 days |

---

## Project Structure

```
centor-feverpain-sore-throat-calc/
├── feverpain_calc.py        # Core pure-Python clinical calculation engine
├── cli.py                   # Full interactive, argument, and batch CLI
├── test_feverpain_calc.py   # Comprehensive unit test suite (26+ tests)
├── benchmark_dataset.json   # Validated clinical benchmark test cases
├── sample.csv               # Sample batch processing input CSV
├── Dockerfile               # Production container definition
├── docker-compose.yml       # Container orchestration
└── README.md                # Clinical documentation and usage manual
```

---

## Installation & Requirements

Pure standard library implementation with zero external dependencies. Compatible with Python 3.10+.

```bash
git clone https://github.com/abusuraihsakhri/centor-feverpain-sore-throat-calc.git
cd centor-feverpain-sore-throat-calc
```

---

## CLI Usage Guide

### 1. Interactive Clinical Consultation Mode
Guides clinicians step-by-step through red flags, FeverPAIN criteria, demographics, and allergy checks:
```bash
python cli.py interactive
```

### 2. Direct Single-Patient Evaluation
```bash
# Evaluate severe case (fever + pus + rapid onset + severe inflammation + no cough)
python cli.py eval --fever --pus --rapid-onset --inflamed --no-cough --age 24

# Output structured JSON for EHR integration
python cli.py eval --fever --pus --rapid-onset --inflamed --no-cough --age 24 --json
```

### 3. Patient with Penicillin Allergy
```bash
python cli.py eval --fever --pus --rapid-onset --inflamed --no-cough --penicillin-allergy --severe-penicillin-allergy
```

### 4. Batch CSV Processing
Score a dataset of patient records in bulk:
```bash
python cli.py batch -i sample.csv -o scored_output.csv
```

---

## Programmatic Python API

```python
from feverpain_calc import evaluate_sore_throat, PrescribingStrategy

result = evaluate_sore_throat(
    fever_past_24h=True,
    purulence_or_pus=True,
    rapid_attendance_le_3d=True,
    severely_inflamed_tonsils=True,
    no_cough_or_coryza=True,
    age_years=28,
    penicillin_allergic=False,
)

print(f"FeverPAIN Score: {result.feverpain_score}/5")
print(f"Prescribing Strategy: {result.prescribing_strategy.value}")
print(f"Strep Risk: {result.feverpain_strep_risk_pct}")
for abx in result.antibiotic_options:
    print(f"Antibiotic: {abx['drug_name']} - {abx['dose']} {abx['frequency']}")
```

---

## Unit Testing

Run the test suite with standard `unittest` or `pytest`:

```bash
python -m unittest discover -s . -p "test_*.py" -v
```

Test coverage includes:
- Discrete FeverPAIN scores 0 through 5 boundary and probability checks.
- Centor 0–4 criteria and McIsaac pediatric/elderly age adjustments (-1, 0, +1).
- Emergency red flags (stridor, trismus/quinsy, drooling, sepsis).
- Weight-adjusted pediatric and adult dosing regimens.
- Type-1 vs non-Type-1 penicillin allergy antimicrobial substitutions.
- CSV batch processing workflows and CLI argument parsing.

---

## References

1. **NICE Guideline NG84** (2018). *Sore throat (acute): antimicrobial prescribing*. National Institute for Health and Care Excellence.
2. **Little P, et al.** (2013). *Clinical score for managing sore throat in primary care (PRISM): a prospective validation study*. BMJ; 347:f4376.
3. **Centor RM, et al.** (1981). *The diagnosis of strep throat in adults in the emergency room*. Medical Decision Making; 1(3):239–246.
4. **McIsaac WJ, et al.** (1998). *A clinical score to reduce unnecessary antibiotic use in patients with sore throat*. CMAJ; 158(1):75–83.

---

## License

MIT License. Developed for clinical decision support and antimicrobial stewardship research.
