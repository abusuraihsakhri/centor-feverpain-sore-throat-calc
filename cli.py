#!/usr/bin/env python3
"""Command-line interface for the FeverPAIN/Centor sore-throat calculator."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from feverpain_calc import evaluate_sore_throat, process_batch_csv


def format_evaluation_output(result: dict) -> str:
    lines = ["=" * 72, "FEVERPAIN / CENTOR SORE-THROAT DECISION SUPPORT", "=" * 72]
    red_flags = result.get("red_flag_assessment", {})
    if red_flags.get("has_red_flags"):
        lines.append("\nURGENT ASSESSMENT")
        lines.extend(f"- {flag}" for flag in red_flags.get("flags_detected", []))
        lines.append(f"\n{red_flags.get('action_required', '')}")
        return "\n".join(lines)

    lines.extend(
        [
            f"\nDecision rule: {result['decision_rule'].title()}",
            f"FeverPAIN Score: {result['feverpain_score']} / 5 ({result['feverpain_strep_risk_pct']})",
            f"Centor Score: {result['centor_score']} / 4",
        ]
    )
    if result.get("mcisaac_score") is not None:
        lines.append(f"McIsaac Score: {result['mcisaac_score']}")

    labels = {
        "NO_ANTIBIOTIC": "NO ANTIBIOTIC",
        "DELAYED_PRESCRIPTION": "NO ANTIBIOTIC OR BACK-UP PRESCRIPTION",
        "IMMEDIATE_ANTIBIOTIC": "IMMEDIATE OR BACK-UP PRESCRIPTION",
        "URGENT_REFERRAL": "URGENT ASSESSMENT",
    }
    strategy = result["prescribing_strategy"]
    lines.extend(
        [
            f"\nStrategy: {labels.get(strategy, strategy)}",
            result["action_summary"],
            f"Rationale: {result['rationale']}",
        ]
    )

    if result.get("antibiotic_options"):
        lines.append("\nNICE NG84 antibiotic option (when prescribing is clinically appropriate):")
        for item in result["antibiotic_options"]:
            lines.append(f"- {item['drug_name']}: {item['dose']} for {item['duration']}")
            lines.append(f"  {item['notes']}")

    lines.append("\nSelf-care / safety netting:")
    lines.extend(f"- {item}" for item in result.get("symptomatic_care", []))
    lines.append(f"\nNote: {result.get('guidance_note', '')}")
    lines.append("Clinical support only; use current local guidance and clinical judgement.")
    return "\n".join(lines)


def _prompt_yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in {"y", "yes", "1", "true", "t"}:
            return True
        if answer in {"n", "no", "0", "false", "f"}:
            return False
        print("Please enter y or n.")


def _prompt_float(question: str, default: Optional[float] = None) -> Optional[float]:
    while True:
        value = input(f"{question} [{default if default is not None else 'optional'}]: ").strip()
        if not value:
            return default
        try:
            number = float(value)
        except ValueError:
            print("Enter a valid number.")
            continue
        if number < 0:
            print("Value cannot be negative.")
            continue
        return number


def interactive_mode() -> int:
    print("FeverPAIN / Centor sore-throat assessment")
    decision_rule = input("Decision rule [feverpain/centor] (default feverpain): ").strip().lower() or "feverpain"
    if decision_rule not in {"feverpain", "centor"}:
        print("Invalid decision rule.")
        return 2

    print("\nRed flags")
    stridor = _prompt_yes_no("Stridor or upper-airway compromise?")
    difficulty_breathing = _prompt_yes_no("Breathing difficulty?")
    difficulty_swallowing = _prompt_yes_no("Drooling or unable to swallow fluids/saliva?")
    trismus = _prompt_yes_no("Trismus or marked asymmetric peritonsillar swelling?")
    sepsis = _prompt_yes_no("Severe systemic illness / possible sepsis?")

    print("\nCriteria")
    fever = _prompt_yes_no("Fever in the past 24 hours?")
    purulence = _prompt_yes_no("Tonsillar purulence/exudate?")
    rapid = _prompt_yes_no("Symptoms for 3 days or less?")
    inflamed = _prompt_yes_no("Severely inflamed tonsils?")
    no_cough = _prompt_yes_no("No cough or coryza?")
    nodes = _prompt_yes_no("Tender anterior cervical lymph nodes?")
    age = _prompt_float("Age in years")
    weight = _prompt_float("Weight in kg")
    penicillin_allergy = _prompt_yes_no("Penicillin allergy or intolerance?")

    result = evaluate_sore_throat(
        fever_past_24h=fever,
        purulence_or_pus=purulence,
        rapid_attendance_le_3d=rapid,
        severely_inflamed_tonsils=inflamed,
        no_cough_or_coryza=no_cough,
        tender_anterior_cervical_nodes=nodes,
        age_years=age,
        weight_kg=weight,
        penicillin_allergic=penicillin_allergy,
        stridor=stridor,
        difficulty_breathing=difficulty_breathing,
        difficulty_swallowing_saliva=difficulty_swallowing,
        peritonsillar_swelling_trismus=trismus,
        systemic_sepsis_signs=sepsis,
        decision_rule=decision_rule,
    ).to_dict()
    print("\n" + format_evaluation_output(result))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="centor-feverpain-sore-throat-calc",
        description="FeverPAIN and Centor sore-throat decision support aligned with NICE NG84.",
    )
    subparsers = parser.add_subparsers(dest="command")

    evaluate = subparsers.add_parser("eval", help="Evaluate one presentation")
    evaluate.add_argument("--decision-rule", choices=["feverpain", "centor"], default="feverpain")
    evaluate.add_argument("--fever", action="store_true")
    evaluate.add_argument("--pus", action="store_true")
    evaluate.add_argument("--rapid-onset", action="store_true")
    evaluate.add_argument("--inflamed", action="store_true")
    evaluate.add_argument("--no-cough", action="store_true")
    evaluate.add_argument("--tender-nodes", action="store_true")
    evaluate.add_argument("--age", type=float)
    evaluate.add_argument("--weight", type=float)
    evaluate.add_argument("--penicillin-allergy", action="store_true")
    evaluate.add_argument("--severe-penicillin-allergy", action="store_true")
    evaluate.add_argument("--stridor", action="store_true")
    evaluate.add_argument("--difficulty-breathing", action="store_true")
    evaluate.add_argument("--difficulty-swallowing", action="store_true")
    evaluate.add_argument("--trismus", action="store_true")
    evaluate.add_argument("--sepsis", action="store_true")
    evaluate.add_argument("--severe-unilateral-pain", action="store_true")
    evaluate.add_argument("--json", action="store_true")

    subparsers.add_parser("interactive", help="Run an interactive assessment")
    batch = subparsers.add_parser("batch", help="Process a CSV file")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="scored_sore_throat_batch.csv")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "interactive":
        return interactive_mode()
    if args.command == "batch":
        count = process_batch_csv(args.input, args.output)
        print(f"Processed {count} record(s): {args.output}")
        return 0

    result = evaluate_sore_throat(
        fever_past_24h=args.fever,
        purulence_or_pus=args.pus,
        rapid_attendance_le_3d=args.rapid_onset,
        severely_inflamed_tonsils=args.inflamed,
        no_cough_or_coryza=args.no_cough,
        tender_anterior_cervical_nodes=args.tender_nodes,
        age_years=args.age,
        weight_kg=args.weight,
        penicillin_allergic=args.penicillin_allergy,
        severe_penicillin_allergy=args.severe_penicillin_allergy,
        stridor=args.stridor,
        difficulty_breathing=args.difficulty_breathing,
        difficulty_swallowing_saliva=args.difficulty_swallowing,
        peritonsillar_swelling_trismus=args.trismus,
        systemic_sepsis_signs=args.sepsis,
        severe_unilateral_pain=args.severe_unilateral_pain,
        decision_rule=args.decision_rule,
    ).to_dict()
    print(json.dumps(result, indent=2) if args.json else format_evaluation_output(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
