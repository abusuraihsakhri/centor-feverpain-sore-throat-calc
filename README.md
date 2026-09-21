# FeverPAIN & Centor Sore Throat Calculator

### [Open the Live Application →](https://abusuraihsakhri.github.io/centor-feverpain-sore-throat-calc/)

A compact browser and Python implementation of the FeverPAIN and Centor clinical criteria for acute sore throat, with antimicrobial-prescribing categories aligned to NICE NG84.

## Features

- FeverPAIN (0–5) and Centor (0–4) scoring.
- Explicit choice of decision rule; the thresholds are not combined into a hybrid score.
- Red-flag screening that supersedes routine scoring when serious illness or a suppurative complication is suspected.
- NICE NG84 prescribing categories and first-choice antibiotic information when a prescription is being considered.
- Responsive browser interface with light and dark modes.
- Python CLI, interactive assessment and batch CSV processing.
- Unit tests for scoring, decision-rule separation, antibiotic age/weight bands, aliases, CLI output and browser logic.

## Clinical scope

This is clinical decision support, not a diagnostic or prescribing system. Acute sore throat is commonly self-limiting. NICE recommends FeverPAIN or Centor to identify people more likely to benefit from antibiotics, while advising urgent reassessment when symptoms suggest a more serious condition.

FeverPAIN was not tested in children under 3 years, and NICE directs children under 5 with fever to its fever-in-under-5s guidance. Antibiotic selection also requires review of allergies, pregnancy, interactions, renal/hepatic function, local resistance patterns and current BNF/local formulary guidance.

## Browser use

Open the live application link above. The browser version is static HTML/CSS/JavaScript; it does not require a backend or Pyodide. Patient inputs are processed locally in the browser and are not transmitted or stored by the application.

## Python use

Evaluate one case:

```bash
python cli.py eval --fever --pus --rapid-onset --inflamed --no-cough --age 24
```

Use Centor as the active NICE decision rule:

```bash
python cli.py eval --decision-rule centor --fever --pus --tender-nodes --age 24
```

Batch-score a CSV file:

```bash
python cli.py batch -i sample.csv -o results.csv
```

## Testing

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node site/tests.mjs
```

GitHub Actions runs the Python suite on Python 3.10–3.13 and also checks the browser scoring module.

## References

- NICE NG84: *Sore throat (acute): antimicrobial prescribing* — https://www.nice.org.uk/guidance/ng84
- Little P, et al. BMJ. 2013;347:f5806 — https://doi.org/10.1136/bmj.f5806
- Centor RM, et al. Med Decis Making. 1981;1(3):239-246.
- McIsaac WJ, et al. CMAJ. 1998;158(1):75-83.

## License

MIT. See `LICENSE`.
