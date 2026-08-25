"""
Unit test suite for FeverPAIN & Centor Sore Throat Calculator.
Tests FeverPAIN scoring, Centor criteria, McIsaac age modifiers, red flags,
antimicrobial stewardship recommendations, and batch processing.
"""

import csv
import json
import os
import tempfile
import unittest
from unittest.mock import patch
import io

from feverpain_calc import (
    calculate_centor,
    calculate_feverpain,
    calculate_mcisaac,
    calculate_metrics,
    check_red_flags,
    evaluate_sore_throat,
    get_antibiotic_regimens,
    process_batch_csv,
    PrescribingStrategy,
    SeverityTier,
)
from cli import main as cli_main


class TestFeverPAINCalculator(unittest.TestCase):
    def test_feverpain_score_zero(self):
        score, risk_str, risk_num, tier, rec = calculate_feverpain(
            fever_past_24h=False,
            purulence_or_pus=False,
            rapid_attendance_le_3d=False,
            severely_inflamed_tonsils=False,
            no_cough_or_coryza=False,
        )
        self.assertEqual(score, 0)
        self.assertEqual(tier, SeverityTier.LOW)
        self.assertEqual(risk_str, "13% - 18%")
        self.assertAlmostEqual(risk_num, 15.5)

    def test_feverpain_score_one(self):
        score, risk_str, risk_num, tier, rec = calculate_feverpain(
            fever_past_24h=True,
            purulence_or_pus=False,
            rapid_attendance_le_3d=False,
            severely_inflamed_tonsils=False,
            no_cough_or_coryza=False,
        )
        self.assertEqual(score, 1)
        self.assertEqual(tier, SeverityTier.LOW)

    def test_feverpain_score_two(self):
        score, risk_str, risk_num, tier, rec = calculate_feverpain(
            fever_past_24h=True,
            purulence_or_pus=True,
            rapid_attendance_le_3d=False,
            severely_inflamed_tonsils=False,
            no_cough_or_coryza=False,
        )
        self.assertEqual(score, 2)
        self.assertEqual(tier, SeverityTier.MODERATE)
        self.assertEqual(risk_str, "34% - 40%")

    def test_feverpain_score_three(self):
        score, risk_str, risk_num, tier, rec = calculate_feverpain(
            fever_past_24h=True,
            purulence_or_pus=True,
            rapid_attendance_le_3d=True,
            severely_inflamed_tonsils=False,
            no_cough_or_coryza=False,
        )
        self.assertEqual(score, 3)
        self.assertEqual(tier, SeverityTier.MODERATE)

    def test_feverpain_score_four(self):
        score, risk_str, risk_num, tier, rec = calculate_feverpain(
            fever_past_24h=True,
            purulence_or_pus=True,
            rapid_attendance_le_3d=True,
            severely_inflamed_tonsils=True,
            no_cough_or_coryza=False,
        )
        self.assertEqual(score, 4)
        self.assertEqual(tier, SeverityTier.HIGH)
        self.assertEqual(risk_str, "62% - 65%")

    def test_feverpain_score_five(self):
        score, risk_str, risk_num, tier, rec = calculate_feverpain(
            fever_past_24h=True,
            purulence_or_pus=True,
            rapid_attendance_le_3d=True,
            severely_inflamed_tonsils=True,
            no_cough_or_coryza=True,
        )
        self.assertEqual(score, 5)
        self.assertEqual(tier, SeverityTier.HIGH)


class TestCentorAndMcIsaac(unittest.TestCase):
    def test_centor_scores(self):
        score0, _, _, tier0, _ = calculate_centor(False, False, False, False)
        self.assertEqual(score0, 0)
        self.assertEqual(tier0, SeverityTier.LOW)

        score2, risk2, _, tier2, _ = calculate_centor(True, True, False, False)
        self.assertEqual(score2, 2)
        self.assertEqual(tier2, SeverityTier.MODERATE)
        self.assertEqual(risk2, "15% - 30%")

        score4, risk4, _, tier4, _ = calculate_centor(True, True, True, True)
        self.assertEqual(score4, 4)
        self.assertEqual(tier4, SeverityTier.HIGH)
        self.assertEqual(risk4, "50% - 60%")

    def test_mcisaac_age_modifiers(self):
        # Child 3-14 yrs: +1
        score_child, risk_child, _ = calculate_mcisaac(centor_score=2, age_years=8)
        self.assertEqual(score_child, 3)

        # Adult 15-44 yrs: 0
        score_adult, risk_adult, _ = calculate_mcisaac(centor_score=2, age_years=25)
        self.assertEqual(score_adult, 2)

        # Elderly >=45 yrs: -1
        score_elderly, risk_elderly, _ = calculate_mcisaac(centor_score=2, age_years=60)
        self.assertEqual(score_elderly, 1)

    def test_mcisaac_bounds(self):
        # Min bound -1
        score_min, _, _ = calculate_mcisaac(centor_score=0, age_years=70)
        self.assertEqual(score_min, -1)

        # Max bound 5
        score_max, _, _ = calculate_mcisaac(centor_score=4, age_years=10)
        self.assertEqual(score_max, 5)

    def test_mcisaac_negative_age_raises(self):
        with self.assertRaises(ValueError):
            calculate_mcisaac(centor_score=2, age_years=-5)


class TestRedFlagsAndTriage(unittest.TestCase):
    def test_no_red_flags(self):
        rf = check_red_flags()
        self.assertFalse(rf.has_red_flags)
        self.assertEqual(len(rf.flags_detected), 0)

    def test_stridor_red_flag(self):
        rf = check_red_flags(stridor=True)
        self.assertTrue(rf.has_red_flags)
        self.assertTrue(any("Stridor" in f for f in rf.flags_detected))

    def test_quinsy_trismus_red_flag(self):
        rf = check_red_flags(peritonsillar_swelling_trismus=True)
        self.assertTrue(rf.has_red_flags)
        self.assertTrue(any("Trismus" in f for f in rf.flags_detected))

    def test_multiple_red_flags(self):
        rf = check_red_flags(difficulty_breathing=True, systemic_sepsis_signs=True)
        self.assertTrue(rf.has_red_flags)
        self.assertEqual(len(rf.flags_detected), 2)


class TestComprehensiveEvaluation(unittest.TestCase):
    def test_low_risk_case(self):
        res = evaluate_sore_throat(
            fever_past_24h=False,
            purulence_or_pus=False,
            rapid_attendance_le_3d=False,
            severely_inflamed_tonsils=False,
            no_cough_or_coryza=False,
        )
        self.assertEqual(res.feverpain_score, 0)
        self.assertEqual(res.prescribing_strategy, PrescribingStrategy.NO_ANTIBIOTIC)
        self.assertEqual(len(res.antibiotic_options), 0)
        self.assertTrue(len(res.symptomatic_care) > 0)

    def test_moderate_risk_case(self):
        res = evaluate_sore_throat(
            fever_past_24h=True,
            purulence_or_pus=True,
            rapid_attendance_le_3d=False,
            severely_inflamed_tonsils=False,
            no_cough_or_coryza=False,
        )
        self.assertEqual(res.feverpain_score, 2)
        self.assertEqual(res.prescribing_strategy, PrescribingStrategy.DELAYED_PRESCRIPTION)
        self.assertTrue(len(res.antibiotic_options) > 0)

    def test_high_risk_case(self):
        res = evaluate_sore_throat(
            fever_past_24h=True,
            purulence_or_pus=True,
            rapid_attendance_le_3d=True,
            severely_inflamed_tonsils=True,
            no_cough_or_coryza=True,
        )
        self.assertEqual(res.feverpain_score, 5)
        self.assertEqual(res.prescribing_strategy, PrescribingStrategy.IMMEDIATE_ANTIBIOTIC)
        self.assertTrue(len(res.antibiotic_options) > 0)

    def test_red_flag_overrides_score(self):
        # Even with low score, red flag forces URGENT_REFERRAL
        res = evaluate_sore_throat(
            fever_past_24h=False,
            purulence_or_pus=False,
            rapid_attendance_le_3d=False,
            severely_inflamed_tonsils=False,
            no_cough_or_coryza=False,
            stridor=True,
        )
        self.assertEqual(res.prescribing_strategy, PrescribingStrategy.URGENT_REFERRAL)
        self.assertTrue(res.red_flag_assessment["has_red_flags"])


class TestAntibioticPrescribing(unittest.TestCase):
    def test_first_line_penicillin_adult(self):
        regimens = get_antibiotic_regimens(penicillin_allergic=False, age_years=35)
        drug_names = [r.drug_name for r in regimens]
        self.assertTrue(any("Penicillin V" in d for d in drug_names))
        self.assertTrue(any("Amoxicillin" in d for d in drug_names))

    def test_first_line_penicillin_pediatric_with_weight(self):
        regimens = get_antibiotic_regimens(penicillin_allergic=False, age_years=6, weight_kg=20)
        self.assertTrue(len(regimens) >= 2)
        # Check dose string contains weight calculated dose
        pen_v = next(r for r in regimens if "Penicillin V" in r.drug_name)
        self.assertIn("250 mg", pen_v.dose)

    def test_non_severe_penicillin_allergy(self):
        regimens = get_antibiotic_regimens(penicillin_allergic=True, severe_penicillin_allergy=False, age_years=40)
        drug_names = [r.drug_name for r in regimens]
        self.assertTrue(any("Cefalexin" in d or "Cephalexin" in d for d in drug_names))
        self.assertTrue(any("Clarithromycin" in d for d in drug_names))

    def test_severe_penicillin_allergy(self):
        regimens = get_antibiotic_regimens(penicillin_allergic=True, severe_penicillin_allergy=True, age_years=40)
        drug_names = [r.drug_name for r in regimens]
        # No cephalosporins
        self.assertFalse(any("Cefalexin" in d or "Cephalexin" in d for d in drug_names))
        self.assertTrue(any("Clarithromycin" in d for d in drug_names))
        self.assertTrue(any("Erythromycin" in d for d in drug_names))


class TestMetricsAndBatch(unittest.TestCase):
    def test_calculate_metrics_wrapper_string_values(self):
        data = {
            "fever_past_24h": "true",
            "purulence_or_pus": "yes",
            "rapid_attendance_le_3d": "1",
            "severely_inflamed_tonsils": "false",
            "no_cough_or_coryza": "0",
            "age": "28",
        }
        res = calculate_metrics(**data)
        self.assertEqual(res["feverpain_score"], 3)
        self.assertEqual(res["prescribing_strategy"], "DELAYED_PRESCRIPTION")
        self.assertEqual(res["mcisaac_score"], 2)

    def test_batch_csv_processing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, "input.csv")
            out_path = os.path.join(tmpdir, "output.csv")

            with open(in_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["patient_id", "fever_past_24h", "purulence_or_pus", "rapid_attendance_le_3d", "severely_inflamed_tonsils", "no_cough_or_coryza", "age"],
                )
                writer.writeheader()
                writer.writerow({"patient_id": "P01", "fever_past_24h": "1", "purulence_or_pus": "1", "rapid_attendance_le_3d": "1", "severely_inflamed_tonsils": "1", "no_cough_or_coryza": "1", "age": "12"})
                writer.writerow({"patient_id": "P02", "fever_past_24h": "0", "purulence_or_pus": "0", "rapid_attendance_le_3d": "0", "severely_inflamed_tonsils": "0", "no_cough_or_coryza": "0", "age": "50"})

            count = process_batch_csv(in_path, out_path)
            self.assertEqual(count, 2)

            with open(out_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                out_rows = list(reader)
                self.assertEqual(len(out_rows), 2)
                self.assertEqual(out_rows[0]["feverpain_score"], "5")
                self.assertEqual(out_rows[0]["prescribing_strategy"], "IMMEDIATE_ANTIBIOTIC")
                self.assertEqual(out_rows[1]["feverpain_score"], "0")
                self.assertEqual(out_rows[1]["prescribing_strategy"], "NO_ANTIBIOTIC")


class TestCLI(unittest.TestCase):
    def test_cli_eval_json(self):
        captured_output = io.StringIO()
        with patch("sys.stdout", new=captured_output):
            ret = cli_main(["eval", "--fever", "--pus", "--rapid-onset", "--inflamed", "--no-cough", "--json"])
            self.assertEqual(ret, 0)
        output = captured_output.getvalue()
        data = json.loads(output)
        self.assertEqual(data["feverpain_score"], 5)
        self.assertEqual(data["prescribing_strategy"], "IMMEDIATE_ANTIBIOTIC")

    def test_cli_eval_formatted(self):
        captured_output = io.StringIO()
        with patch("sys.stdout", new=captured_output):
            ret = cli_main(["eval", "--fever", "--pus"])
            self.assertEqual(ret, 0)
        output = captured_output.getvalue()
        self.assertIn("FeverPAIN Score:", output)
        self.assertIn("DELAYED / BACK-UP PRESCRIPTION", output)


if __name__ == "__main__":
    unittest.main()
