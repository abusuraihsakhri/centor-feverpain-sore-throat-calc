# Centor Feverpain Sore Throat Calc

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

FeverPAIN and Centor Clinical Decision Rules for Acute Sore Throat & Pharyngitis
Implements validated clinical prediction rules (NICE NG84, Little et al. 2013, Centor et al. 1981, McIsaac et al. 1998)
for Group A Streptococcal (GAS) pharyngitis risk stratification and antimicrobial stewardship.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`PrescribingStrategy`** — dedicated module for prescribing strategy evaluation and state verification.
- **`SeverityTier`** — dedicated module for severity tier evaluation and state verification.
- **`RedFlagAssessment`** — dedicated module for red flag assessment evaluation and state verification.
- **`AntibioticRecommendation`** — dedicated module for antibiotic recommendation evaluation and state verification.
- **`ClinicalEvaluationResult`** — dedicated module for clinical evaluation result evaluation and state verification.

---

## 📐 Mathematical Formulation & Logic

```text
  Calculates FeverPAIN score (0-5) based on Little et al. (BMJ 2013) & NICE NG84.
  score = 0
  Calculates original Centor score (0-4) (Centor et al. 1981).
  score = (
  elif score == 2:
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --- <value> --fever <value> --pus <value> --rapid-onset <value>
```

### Parameter Reference
- `---`: Specifies input measurement or parameter value.
- `--fever`: Specifies input measurement or parameter value.
- `--pus`: Specifies input measurement or parameter value.
- `--rapid-onset`: Specifies input measurement or parameter value.
- `--inflamed`: Specifies input measurement or parameter value.
- `--no-cough`: Specifies input measurement or parameter value.
- `--tender-nodes`: Specifies input measurement or parameter value.
- `--age`: Specifies input measurement or parameter value.
- `--weight`: Specifies input measurement or parameter value.
- `--penicillin-allergy`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `patient_id` | Parameter / observation metric | Required |
| `fever_past_24h` | Parameter / observation metric | Required |
| `purulence_or_pus` | Parameter / observation metric | Required |
| `rapid_attendance_le_3d` | Parameter / observation metric | Required |
| `severely_inflamed_tonsils` | Parameter / observation metric | Required |
| `no_cough_or_coryza` | Parameter / observation metric | Required |
| `tender_anterior_cervical_nodes` | Parameter / observation metric | Required |
| `age` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t centor-feverpain-sore-throat-calc .
docker run -p 8000:8000 centor-feverpain-sore-throat-calc
```
