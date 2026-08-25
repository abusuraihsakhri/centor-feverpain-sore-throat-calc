#!/usr/bin/env python3
"""
CLI for FeverPAIN & Centor Sore Throat Calculator
Provides interactive questionnaires, single-case evaluation, batch CSV processing, and JSON output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from feverpain_calc import (
    calculate_metrics,
    evaluate_sore_throat,
    process_batch_csv,
    PrescribingStrategy,
)


def format_evaluation_output(res: dict) -> str:
    """Renders human-readable clinical summary."""
    lines = []
    lines.append("=" * 72)
    lines.append("  FEVERPAIN & CENTOR CLINICAL DECISION SUPPORT - SORE THROAT")
    lines.append("  Guideline Reference: NICE NG84 / Little et al. (2013) / Centor (1981)")
    lines.append("=" * 72)

    # Red flag warning if present
    rf = res.get("red_flag_assessment", {})
    if rf.get("has_red_flags"):
        lines.append("\n  [!] CRITICAL ALERT: RED FLAGS DETECTED")
        for flag in rf.get("flags_detected", []):
            lines.append(f"      * {flag}")
        lines.append(f"\n  ACTION REQUIRED: {rf.get('action_required')}")
        lines.append("=" * 72)
        return "\n".join(lines)

    lines.append(f"\n  [Scores & Risk Stratification]")
    lines.append(f"  * FeverPAIN Score:      {res['feverpain_score']} / 5  ({res['feverpain_tier']})")
    lines.append(f"  * GAS Probability (FP): {res['feverpain_strep_risk_pct']}")
    if res.get("centor_score") is not None:
        lines.append(f"  * Centor Score:         {res['centor_score']} / 4  (Strep risk: {res.get('centor_strep_risk_pct', 'N/A')})")
    if res.get("mcisaac_score") is not None:
        lines.append(f"  * McIsaac (Mod Centor): {res['mcisaac_score']} / 5  (Strep risk: {res.get('mcisaac_strep_risk_pct', 'N/A')})")

    strat = res["prescribing_strategy"]
    strat_colors = {
        "NO_ANTIBIOTIC": "NO ANTIBIOTICS RECOMMENDED",
        "DELAYED_PRESCRIPTION": "DELAYED / BACK-UP PRESCRIPTION",
        "IMMEDIATE_ANTIBIOTIC": "IMMEDIATE ANTIBIOTIC THERAPY",
        "URGENT_REFERRAL": "URGENT HOSPITAL REFERRAL",
    }
    lines.append(f"\n  [Prescribing Strategy]: [{strat_colors.get(strat, strat)}]")
    lines.append(f"  Summary:  {res['action_summary']}")
    lines.append(f"  Rationale: {res.get('rationale', '')}")

    antibiotics = res.get("antibiotic_options", [])
    if antibiotics:
        lines.append(f"\n  [Recommended Antimicrobial Regimens]:")
        for idx, abx in enumerate(antibiotics, start=1):
            lines.append(f"    {idx}. {abx['drug_name']}")
            lines.append(f"       Dose:      {abx['dose']} {abx['frequency']}")
            lines.append(f"       Duration:  {abx['duration']}")
            lines.append(f"       Notes:     {abx['notes']}")

    symptomatic = res.get("symptomatic_care", [])
    if symptomatic:
        lines.append(f"\n  [Symptomatic & Supportive Care Advice]:")
        for sym in symptomatic:
            lines.append(f"    - {sym}")

    lines.append("=" * 72)
    return "\n".join(lines)


def interactive_mode():
    """Runs interactive terminal assessment with clinical prompts."""
    print("=" * 72)
    print("  FEVERPAIN SORE THROAT CLINICAL ASSESSMENT - INTERACTIVE MODE")
    print("=" * 72)

    def prompt_yes_no(question: str) -> bool:
        while True:
            ans = input(f"{question} (y/n): ").strip().lower()
            if ans in ("y", "yes", "1", "t", "true"):
                return True
            if ans in ("n", "no", "0", "f", "false"):
                return False
            print("Please enter 'y' for yes or 'n' for no.")

    def prompt_float(question: str, default: Optional[float] = None) -> Optional[float]:
        while True:
            val = input(f"{question} [{default if default is not None else 'optional'}]: ").strip()
            if not val:
                return default
            try:
                num = float(val)
                if num < 0:
                    print("Value cannot be negative.")
                    continue
                return num
            except ValueError:
                print("Invalid number, please try again.")

    print("\n--- 1. Emergency Red-Flag Screening ---")
    stridor = prompt_yes_no("Does patient have stridor, breathing difficulty, or upper airway obstruction?")
    swallow_saliva = prompt_yes_no("Is patient drooling or unable to swallow liquids/saliva?")
    trismus = prompt_yes_no("Is there trismus (difficulty opening mouth) or severe asymmetric tonsillar swelling?")
    sepsis = prompt_yes_no("Are there systemic sepsis signs (marked tachycardia, hypotension, cyanosis)?")

    if stridor or swallow_saliva or trismus or sepsis:
        res = evaluate_sore_throat(
            stridor=stridor,
            difficulty_swallowing_saliva=swallow_saliva,
            peritonsillar_swelling_trismus=trismus,
            systemic_sepsis_signs=sepsis,
        )
        print(format_evaluation_output(res.to_dict()))
        return

    print("\n--- 2. FeverPAIN Criteria ---")
    fever = prompt_yes_no("F - Fever in the past 24 hours (reported or measured >37.5C)?")
    purulence = prompt_yes_no("P - Pus / purulent exudate on tonsils?")
    rapid = prompt_yes_no("A - Attend rapidly (symptoms present for <= 3 days)?")
    inflamed = prompt_yes_no("I - Severely inflamed tonsils (marked erythema/edema)?")
    no_cough = prompt_yes_no("N - No cough or coryza (absence of cough & runny nose)?")

    print("\n--- 3. Patient Demographics & Additional Exam ---")
    age = prompt_float("Patient age in years", default=30.0)
    weight = prompt_float("Patient weight in kg (for pediatric dosing)", default=None)
    tender_nodes = prompt_yes_no("Tender anterior cervical lymphadenopathy present?")

    print("\n--- 4. Allergy Assessment ---")
    pen_allergic = prompt_yes_no("Is the patient allergic to Penicillin?")
    sev_pen_allergic = False
    if pen_allergic:
        sev_pen_allergic = prompt_yes_no("Did the penicillin reaction involve anaphylaxis, angioedema, or hives?")

    eval_obj = evaluate_sore_throat(
        fever_past_24h=fever,
        purulence_or_pus=purulence,
        rapid_attendance_le_3d=rapid,
        severely_inflamed_tonsils=inflamed,
        no_cough_or_coryza=no_cough,
        tender_anterior_cervical_nodes=tender_nodes,
        age_years=age,
        weight_kg=weight,
        penicillin_allergic=pen_allergic,
        severe_penicillin_allergy=sev_pen_allergic,
    )

    print("\n" + format_evaluation_output(eval_obj.to_dict()))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="centor-feverpain-sore-throat-calc",
        description="FeverPAIN and Centor Sore Throat Antibiotic Stewardship Calculator (NICE NG84)",
    )
    subparsers = parser.add_subparsers(dest="command")

    # eval / single command
    p_eval = subparsers.add_parser("eval", help="Evaluate individual patient sore throat presentation")
    p_eval.add_argument("--fever", action="store_true", help="Fever in past 24 hours")
    p_eval.add_argument("--pus", action="store_true", help="Pus on tonsils / tonsillar exudate")
    p_eval.add_argument("--rapid-onset", action="store_true", help="Rapid attendance (<= 3 days of symptom onset)")
    p_eval.add_argument("--inflamed", action="store_true", help="Severely inflamed tonsils")
    p_eval.add_argument("--no-cough", action="store_true", help="No cough or coryza")
    p_eval.add_argument("--tender-nodes", action="store_true", help="Tender anterior cervical lymph nodes")
    p_eval.add_argument("--age", type=float, default=None, help="Patient age in years")
    p_eval.add_argument("--weight", type=float, default=None, help="Patient weight in kg")
    p_eval.add_argument("--penicillin-allergy", action="store_true", help="Patient is allergic to penicillin")
    p_eval.add_argument("--severe-penicillin-allergy", action="store_true", help="Severe anaphylactic penicillin allergy")
    p_eval.add_argument("--stridor", action="store_true", help="Red flag: Stridor present")
    p_eval.add_argument("--trismus", action="store_true", help="Red flag: Trismus / suspect quinsy")
    p_eval.add_argument("--sepsis", action="store_true", help="Red flag: Sepsis signs present")
    p_eval.add_argument("--json", action="store_true", help="Output results as JSON")

    # interactive command
    subparsers.add_parser("interactive", help="Start interactive step-by-step clinical evaluation questionnaire")

    # batch command
    p_batch = subparsers.add_parser("batch", help="Batch process patient CSV records")
    p_batch.add_argument("-i", "--input", required=True, help="Path to input CSV file")
    p_batch.add_argument("-o", "--output", default="scored_sore_throat_batch.csv", help="Path to output CSV file")

    args = parser.parse_args(argv)

    if args.command == "interactive" or (args.command is None and len(sys.argv) == 1):
        interactive_mode()
        return 0

    if args.command == "eval":
        res = evaluate_sore_throat(
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
            peritonsillar_swelling_trismus=args.trismus,
            systemic_sepsis_signs=args.sepsis,
        )
        res_dict = res.to_dict()
        if args.json:
            print(json.dumps(res_dict, indent=2))
        else:
            print(format_evaluation_output(res_dict))
        return 0

    if args.command == "batch":
        count = process_batch_csv(args.input, args.output)
        print(f"Successfully processed {count} records from {args.input} -> {args.output}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
