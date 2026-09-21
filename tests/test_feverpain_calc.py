import csv
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from cli import main as cli_main
from feverpain_calc import (
    PrescribingStrategy,
    SeverityTier,
    calculate_centor,
    calculate_feverpain,
    calculate_mcisaac,
    calculate_metrics,
    check_red_flags,
    evaluate_sore_throat,
    get_antibiotic_regimens,
    process_batch_csv,
)


class TestScores(unittest.TestCase):
    def test_feverpain_bands(self):
        cases = [
            ((0, 0, 0, 0, 0), 0, SeverityTier.LOW),
            ((1, 1, 0, 0, 0), 2, SeverityTier.MODERATE),
            ((1, 1, 1, 1, 1), 5, SeverityTier.HIGH),
        ]
        for inputs, expected_score, expected_tier in cases:
            score, _, _, tier, _ = calculate_feverpain(*inputs)
            self.assertEqual(score, expected_score)
            self.assertEqual(tier, expected_tier)

    def test_centor(self):
        self.assertEqual(calculate_centor(False, False, False, False)[0], 0)
        self.assertEqual(calculate_centor(True, True, True, True)[0], 4)

    def test_mcisaac_modifiers_and_negative_age(self):
        self.assertEqual(calculate_mcisaac(2, 8)[0], 3)
        self.assertEqual(calculate_mcisaac(2, 25)[0], 2)
        self.assertEqual(calculate_mcisaac(2, 60)[0], 1)
        with self.assertRaises(ValueError):
            calculate_mcisaac(2, -1)


class TestDecisionRules(unittest.TestCase):
    def test_feverpain_default_no_antibiotic(self):
        result = evaluate_sore_throat().to_dict()
        self.assertEqual(result["decision_rule"], "feverpain")
        self.assertEqual(result["prescribing_strategy"], "NO_ANTIBIOTIC")

    def test_feverpain_2_3_back_up_category(self):
        result = evaluate_sore_throat(fever_past_24h=True, purulence_or_pus=True)
        self.assertEqual(result.prescribing_strategy, PrescribingStrategy.DELAYED_PRESCRIPTION)
        self.assertIn("consider no antibiotic or a back-up", result.action_summary.lower())

    def test_feverpain_4_5_immediate_or_backup(self):
        result = evaluate_sore_throat(
            fever_past_24h=True,
            purulence_or_pus=True,
            rapid_attendance_le_3d=True,
            severely_inflamed_tonsils=True,
        )
        self.assertEqual(result.prescribing_strategy, PrescribingStrategy.IMMEDIATE_ANTIBIOTIC)
        self.assertIn("immediate or back-up", result.action_summary.lower())

    def test_centor_rule_is_not_hybridized_with_feverpain(self):
        kwargs = dict(
            fever_past_24h=True,
            purulence_or_pus=True,
            tender_anterior_cervical_nodes=True,
        )
        fp = evaluate_sore_throat(**kwargs, decision_rule="feverpain")
        centor = evaluate_sore_throat(**kwargs, decision_rule="centor")
        self.assertEqual(fp.feverpain_score, 2)
        self.assertEqual(fp.prescribing_strategy, PrescribingStrategy.DELAYED_PRESCRIPTION)
        self.assertEqual(centor.centor_score, 3)
        self.assertEqual(centor.prescribing_strategy, PrescribingStrategy.IMMEDIATE_ANTIBIOTIC)

    def test_invalid_rule(self):
        with self.assertRaises(ValueError):
            evaluate_sore_throat(decision_rule="hybrid")

    def test_red_flag_supersedes_scoring(self):
        result = evaluate_sore_throat(stridor=True)
        self.assertEqual(result.prescribing_strategy, PrescribingStrategy.URGENT_REFERRAL)
        self.assertTrue(result.red_flag_assessment["has_red_flags"])


class TestAntibiotics(unittest.TestCase):
    def test_adult_nice_first_choice(self):
        regimens = get_antibiotic_regimens(age_years=30)
        self.assertEqual(len(regimens), 1)
        self.assertEqual(regimens[0].drug_name, "Phenoxymethylpenicillin (Penicillin V)")
        self.assertIn("500 mg four times daily", regimens[0].dose)

    def test_child_age_band(self):
        regimen = get_antibiotic_regimens(age_years=7)[0]
        self.assertIn("250 mg four times daily", regimen.dose)
        self.assertIn("500 mg twice daily", regimen.dose)

    def test_penicillin_allergy_is_clarithromycin(self):
        regimen = get_antibiotic_regimens(penicillin_allergic=True, age_years=30)[0]
        self.assertEqual(regimen.drug_name, "Clarithromycin")
        self.assertIn("250 mg to 500 mg twice daily", regimen.dose)

    def test_child_clarithromycin_requires_weight_band(self):
        regimen = get_antibiotic_regimens(penicillin_allergic=True, age_years=7, weight_kg=18)[0]
        self.assertEqual(regimen.dose, "125 mg twice daily")

    def test_invalid_weight(self):
        with self.assertRaises(ValueError):
            get_antibiotic_regimens(penicillin_allergic=True, age_years=7, weight_kg=0)


class TestAliasesAndBatch(unittest.TestCase):
    def test_explicit_false_value_is_not_overridden_by_alias(self):
        result = calculate_metrics(fever_past_24h=0, fever=1)
        self.assertEqual(result["feverpain_score"], 0)

    def test_string_aliases(self):
        result = calculate_metrics(
            fever="true",
            pus="yes",
            rapid_onset="1",
            severe_inflammation="false",
            no_cough="0",
            age="28",
        )
        self.assertEqual(result["feverpain_score"], 3)
        self.assertEqual(result["mcisaac_score"], 2)

    def test_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "input.csv")
            dst = os.path.join(tmpdir, "output.csv")
            with open(src, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["patient_id", "fever", "pus"])
                writer.writeheader()
                writer.writerow({"patient_id": "P1", "fever": "1", "pus": "1"})
            self.assertEqual(process_batch_csv(src, dst), 1)
            with open(dst, encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["feverpain_score"], "2")
            self.assertEqual(row["decision_rule"], "feverpain")


class TestCLI(unittest.TestCase):
    def test_json_output(self):
        output = io.StringIO()
        with patch("sys.stdout", new=output):
            self.assertEqual(cli_main(["eval", "--fever", "--pus", "--json"]), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["feverpain_score"], 2)

    def test_centor_cli(self):
        output = io.StringIO()
        with patch("sys.stdout", new=output):
            self.assertEqual(
                cli_main(["eval", "--decision-rule", "centor", "--fever", "--pus", "--tender-nodes"]),
                0,
            )
        self.assertIn("Centor 3/4", output.getvalue())


if __name__ == "__main__":
    unittest.main()
