# Centor & FeverPAIN Sore Throat Antibiotic Stewardship Calculator

> **Domain:** Primary Care, Emergency Medicine & Antimicrobial Stewardship  
> **Clinical Guidelines:** NICE NG84 (Sore throat: antimicrobial prescribing), Little et al. (BMJ 2013), Centor et al. (Med Decis Making 1981), McIsaac et al. (CMAJ 1998)

---

## 📖 Clinical Overview

The **Centor & FeverPAIN Sore Throat Calculator** stratifies the risk of Group A Streptococcal (GAS) pharyngitis in patients presenting with acute sore throat. It guides evidence-based antimicrobial prescribing, mitigates inappropriate antibiotic usage for viral self-limiting infections, identifies red flag surgical complications (quinsy, peritonsillar abscess, epiglottitis), and tailors first-line antibiotic regimens based on age, weight, and penicillin allergy status.

### Criteria & Scoring Systems

#### 1. FeverPAIN Score (NICE NG84 Primary Recommendation)
- **F**ever in past 24 hours (+1)
- **P**urulence (pus on tonsils) (+1)
- **A**ttend rapidly (presentation $\le 3$ days from symptom onset) (+1)
- **I**nflamed severely (tonsils severely inflamed) (+1)
- **N**o cough or coryza (+1)

| FeverPAIN Score | GAS Likelihood | NICE Antimicrobial Strategy |
|:---|:---|:---|
| **0 – 1** | 13% – 18% | **No antibiotic**: Self-care and analgesia (paracetamol / ibuprofen) |
| **2 – 3** | 34% – 40% | **Delayed / Back-up prescription**: Re-evaluate if no improvement in 3–5 days or consider RADT |
| **4 – 5** | 62% – 65% | **Immediate antibiotic prescription**: Penicillin V / Phenoxymethylpenicillin (or Clarithromycin / Erythromycin if allergic) |

#### 2. Modified Centor (McIsaac) Score
- Tonsillar exudate (+1)
- Tender anterior cervical lymphadenopathy (+1)
- Absence of cough (+1)
- History of fever / temperature > 38°C (+1)
- Age Modifier:
  - 3 to 14 years: +1
  - 15 to 44 years: 0
  - $\ge 45$ years: -1

---

## 💻 CLI Quickstart & Usage

### 1. Evaluate Individual Patient Presentation
```bash
python cli.py eval --fever --purulence --rapid --inflamed --no-cough --nodes --age 24 --weight 70
```

### 2. Interactive Guided Clinical Questionnaire
```bash
python cli.py interactive
```

### 3. Batch Process Patient Presentation Cohort
```bash
python cli.py batch -i sample.csv -o out_results.csv
```

---

## 🧪 Verification & Testing

Execute comprehensive unit tests via pytest:
```bash
python -m pytest -p no:zarr
```
