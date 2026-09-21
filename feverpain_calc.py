"""FeverPAIN and Centor clinical decision support for acute sore throat.

The module implements the FeverPAIN and Centor criteria and maps them to the
antimicrobial-prescribing categories in NICE NG84. It is intended for clinical
support and software/testing use, not as a substitute for clinical assessment.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PrescribingStrategy(str, Enum):
    NO_ANTIBIOTIC = "NO_ANTIBIOTIC"
    DELAYED_PRESCRIPTION = "DELAYED_PRESCRIPTION"
    IMMEDIATE_ANTIBIOTIC = "IMMEDIATE_ANTIBIOTIC"
    URGENT_REFERRAL = "URGENT_REFERRAL"


class SeverityTier(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RedFlagAssessment:
    has_red_flags: bool
    flags_detected: List[str] = field(default_factory=list)
    action_required: Optional[str] = None


@dataclass
class AntibioticRecommendation:
    drug_name: str
    dose: str
    frequency: str
    duration: str
    indication: str
    notes: str


@dataclass
class ClinicalEvaluationResult:
    feverpain_score: int
    feverpain_strep_risk_pct: str
    feverpain_risk_numeric: float
    feverpain_tier: SeverityTier
    feverpain_recommendation: str

    centor_score: Optional[int] = None
    centor_strep_risk_pct: Optional[str] = None
    centor_risk_numeric: Optional[float] = None
    centor_tier: Optional[SeverityTier] = None

    mcisaac_score: Optional[int] = None
    mcisaac_strep_risk_pct: Optional[str] = None

    prescribing_strategy: PrescribingStrategy = PrescribingStrategy.NO_ANTIBIOTIC
    action_summary: str = ""
    antibiotic_options: List[Dict[str, str]] = field(default_factory=list)
    symptomatic_care: List[str] = field(default_factory=list)
    red_flag_assessment: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    decision_rule: str = "feverpain"
    guidance_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["prescribing_strategy"] = self.prescribing_strategy.value
        data["feverpain_tier"] = self.feverpain_tier.value
        if self.centor_tier:
            data["centor_tier"] = self.centor_tier.value
        return data


def check_red_flags(
    stridor: bool = False,
    difficulty_breathing: bool = False,
    difficulty_swallowing_saliva: bool = False,
    peritonsillar_swelling_trismus: bool = False,
    systemic_sepsis_signs: bool = False,
    severe_unilateral_pain: bool = False,
) -> RedFlagAssessment:
    """Return red flags that should supersede routine outpatient scoring."""
    flags: List[str] = []
    if stridor:
        flags.append("Stridor or upper-airway compromise")
    if difficulty_breathing:
        flags.append("Respiratory distress or compromised breathing")
    if difficulty_swallowing_saliva:
        flags.append("Unable to swallow fluids/saliva or drooling")
    if peritonsillar_swelling_trismus:
        flags.append("Trismus or marked asymmetric peritonsillar swelling")
    if systemic_sepsis_signs:
        flags.append("Signs of severe systemic illness or possible sepsis")
    if severe_unilateral_pain:
        flags.append("Severe unilateral throat pain concerning for a suppurative complication")

    if flags:
        return RedFlagAssessment(
            has_red_flags=True,
            flags_detected=flags,
            action_required=(
                "Urgent clinical assessment is required. Do not rely on FeverPAIN or "
                "Centor scoring when a serious illness or suppurative complication is suspected."
            ),
        )
    return RedFlagAssessment(False, [], None)


def calculate_feverpain(
    fever_past_24h: bool,
    purulence_or_pus: bool,
    rapid_attendance_le_3d: bool,
    severely_inflamed_tonsils: bool,
    no_cough_or_coryza: bool,
) -> Tuple[int, str, float, SeverityTier, str]:
    """Calculate FeverPAIN (0-5) and return NICE-aligned guidance text."""
    score = sum(
        bool(value)
        for value in (
            fever_past_24h,
            purulence_or_pus,
            rapid_attendance_le_3d,
            severely_inflamed_tonsils,
            no_cough_or_coryza,
        )
    )

    if score <= 1:
        return (
            score,
            "13% - 18%",
            15.5,
            SeverityTier.LOW,
            "NICE NG84: do not offer an antibiotic; give self-care and safety-netting advice.",
        )
    if score <= 3:
        return (
            score,
            "34% - 40%",
            37.0,
            SeverityTier.MODERATE,
            "NICE NG84: consider no antibiotic or a back-up antibiotic prescription.",
        )
    return (
        score,
        "62% - 65%",
        63.5,
        SeverityTier.HIGH,
        "NICE NG84: consider an immediate antibiotic or a back-up antibiotic prescription.",
    )


def calculate_centor(
    tonsillar_exudate: bool,
    tender_anterior_cervical_nodes: bool,
    history_of_fever: bool,
    absence_of_cough: bool,
) -> Tuple[int, str, float, SeverityTier, str]:
    """Calculate the original Centor score (0-4).

    Approximate probability ranges are retained for backward compatibility;
    NICE NG84 treatment categories are based on score bands rather than these
    probability estimates.
    """
    score = sum(
        bool(value)
        for value in (
            tonsillar_exudate,
            tender_anterior_cervical_nodes,
            history_of_fever,
            absence_of_cough,
        )
    )

    if score <= 1:
        risk_str, risk_num, tier = "2.5% - 6%", 4.2, SeverityTier.LOW
    elif score == 2:
        risk_str, risk_num, tier = "15% - 30%", 22.5, SeverityTier.MODERATE
    elif score == 3:
        risk_str, risk_num, tier = "30% - 40%", 35.0, SeverityTier.HIGH
    else:
        risk_str, risk_num, tier = "50% - 60%", 55.0, SeverityTier.HIGH

    if score <= 2:
        recommendation = "NICE NG84: do not offer an antibiotic on the basis of Centor 0-2 alone."
    else:
        recommendation = "NICE NG84: consider an immediate or back-up antibiotic prescription for Centor 3-4."
    return score, risk_str, risk_num, tier, recommendation


def calculate_mcisaac(centor_score: int, age_years: float) -> Tuple[int, str, float]:
    """Calculate the Modified Centor/McIsaac score (-1 to 5)."""
    if age_years < 0:
        raise ValueError(f"Age cannot be negative: {age_years}")

    score = centor_score
    if 3 <= age_years <= 14:
        score += 1
    elif age_years >= 45:
        score -= 1
    score = max(-1, min(5, score))

    if score <= 0:
        return score, "1% - 2.5%", 1.8
    if score == 1:
        return score, "5% - 10%", 7.5
    if score == 2:
        return score, "11% - 17%", 14.0
    if score == 3:
        return score, "28% - 35%", 31.5
    return score, "51% - 53%", 52.0


def _phenoxymethylpenicillin_regimen(age_years: Optional[float]) -> Optional[AntibioticRecommendation]:
    if age_years is not None and age_years < 0:
        raise ValueError("Age cannot be negative")
    if age_years is not None and age_years < (1 / 12):
        return None

    if age_years is None or age_years >= 12:
        dose = "500 mg four times daily OR 1,000 mg twice daily"
    elif age_years >= 6:
        dose = "250 mg four times daily OR 500 mg twice daily"
    elif age_years >= 1:
        dose = "125 mg four times daily OR 250 mg twice daily"
    else:
        dose = "62.5 mg four times daily OR 125 mg twice daily"

    return AntibioticRecommendation(
        drug_name="Phenoxymethylpenicillin (Penicillin V)",
        dose=dose,
        frequency="Use one of the age-appropriate schedules above",
        duration="5 to 10 days",
        indication="NICE NG84 first-choice oral antibiotic when an antibiotic is indicated",
        notes=(
            "Five days may be sufficient for symptomatic cure; a 10-day course may increase "
            "microbiological cure. Verify suitability, contraindications and local formulary/BNF guidance."
        ),
    )


def _clarithromycin_regimen(
    age_years: Optional[float], weight_kg: Optional[float]
) -> Optional[AntibioticRecommendation]:
    if age_years is not None and age_years < 0:
        raise ValueError("Age cannot be negative")
    if weight_kg is not None and weight_kg <= 0:
        raise ValueError("Weight must be greater than zero")
    if age_years is not None and age_years < (1 / 12):
        return None

    if age_years is None or age_years >= 12:
        dose = "250 mg to 500 mg twice daily"
    elif weight_kg is None:
        dose = "Use NICE/BNF weight-band dosing; weight is required for children under 12"
    elif weight_kg < 8:
        dose = "7.5 mg/kg twice daily"
    elif weight_kg < 12:
        dose = "62.5 mg twice daily"
    elif weight_kg < 20:
        dose = "125 mg twice daily"
    elif weight_kg < 30:
        dose = "187.5 mg twice daily"
    elif weight_kg <= 40:
        dose = "250 mg twice daily"
    else:
        dose = "Check BNF/local formulary for dosing in a child over 40 kg"

    return AntibioticRecommendation(
        drug_name="Clarithromycin",
        dose=dose,
        frequency="Twice daily",
        duration="5 days",
        indication="NICE NG84 alternative first choice for penicillin allergy or intolerance (not pregnancy)",
        notes=(
            "Pregnancy requires separate prescribing review; NICE prefers erythromycin when a macrolide "
            "is needed in pregnancy. Check interactions, contraindications and local formulary/BNF guidance."
        ),
    )


def get_antibiotic_regimens(
    penicillin_allergic: bool = False,
    severe_penicillin_allergy: bool = False,
    age_years: Optional[float] = None,
    weight_kg: Optional[float] = None,
) -> List[AntibioticRecommendation]:
    """Return NICE NG84 antibiotic options only.

    severe_penicillin_allergy is retained for API compatibility; NICE NG84
    uses clarithromycin as the alternative first choice for penicillin allergy
    or intolerance (outside pregnancy).
    """
    if severe_penicillin_allergy:
        penicillin_allergic = True

    regimen = (
        _clarithromycin_regimen(age_years, weight_kg)
        if penicillin_allergic
        else _phenoxymethylpenicillin_regimen(age_years)
    )
    return [regimen] if regimen else []


def _strategy_for_feverpain(score: int) -> PrescribingStrategy:
    if score <= 1:
        return PrescribingStrategy.NO_ANTIBIOTIC
    if score <= 3:
        return PrescribingStrategy.DELAYED_PRESCRIPTION
    return PrescribingStrategy.IMMEDIATE_ANTIBIOTIC


def _strategy_for_centor(score: int) -> PrescribingStrategy:
    if score <= 2:
        return PrescribingStrategy.NO_ANTIBIOTIC
    return PrescribingStrategy.IMMEDIATE_ANTIBIOTIC


def evaluate_sore_throat(
    fever_past_24h: bool = False,
    purulence_or_pus: bool = False,
    rapid_attendance_le_3d: bool = False,
    severely_inflamed_tonsils: bool = False,
    no_cough_or_coryza: bool = False,
    tender_anterior_cervical_nodes: Optional[bool] = None,
    age_years: Optional[float] = None,
    weight_kg: Optional[float] = None,
    penicillin_allergic: bool = False,
    severe_penicillin_allergy: bool = False,
    stridor: bool = False,
    difficulty_breathing: bool = False,
    difficulty_swallowing_saliva: bool = False,
    peritonsillar_swelling_trismus: bool = False,
    systemic_sepsis_signs: bool = False,
    severe_unilateral_pain: bool = False,
    decision_rule: str = "feverpain",
) -> ClinicalEvaluationResult:
    """Evaluate an acute sore-throat presentation using one explicit NICE rule."""
    rule = decision_rule.strip().lower()
    if rule not in {"feverpain", "centor"}:
        raise ValueError("decision_rule must be 'feverpain' or 'centor'")
    if age_years is not None and age_years < 0:
        raise ValueError("Age cannot be negative")
    if weight_kg is not None and weight_kg <= 0:
        raise ValueError("Weight must be greater than zero")
    if severe_penicillin_allergy:
        penicillin_allergic = True

    red_flags = check_red_flags(
        stridor=stridor,
        difficulty_breathing=difficulty_breathing,
        difficulty_swallowing_saliva=difficulty_swallowing_saliva,
        peritonsillar_swelling_trismus=peritonsillar_swelling_trismus,
        systemic_sepsis_signs=systemic_sepsis_signs,
        severe_unilateral_pain=severe_unilateral_pain,
    )

    fp_score, fp_risk_str, fp_risk_num, fp_tier, fp_rec = calculate_feverpain(
        fever_past_24h,
        purulence_or_pus,
        rapid_attendance_le_3d,
        severely_inflamed_tonsils,
        no_cough_or_coryza,
    )
    centor_score, centor_risk_str, centor_risk_num, centor_tier, _ = calculate_centor(
        purulence_or_pus,
        bool(tender_anterior_cervical_nodes),
        fever_past_24h,
        no_cough_or_coryza,
    )

    mcisaac_score = None
    mcisaac_risk = None
    if age_years is not None:
        mcisaac_score, mcisaac_risk, _ = calculate_mcisaac(centor_score, age_years)

    if red_flags.has_red_flags:
        strategy = PrescribingStrategy.URGENT_REFERRAL
        action_summary = "Urgent clinical assessment required; routine sore-throat scoring is superseded."
        rationale = "One or more red flags for serious illness or a suppurative complication were selected."
        antibiotic_options: List[Dict[str, str]] = []
    else:
        if rule == "feverpain":
            strategy = _strategy_for_feverpain(fp_score)
            score_text = f"FeverPAIN {fp_score}/5"
            if strategy == PrescribingStrategy.NO_ANTIBIOTIC:
                action_summary = f"{score_text}: do not offer an antibiotic; provide self-care and safety-netting advice."
                rationale = "NICE NG84 classifies FeverPAIN 0-1 as unlikely to benefit from antibiotics."
            elif strategy == PrescribingStrategy.DELAYED_PRESCRIPTION:
                action_summary = f"{score_text}: consider no antibiotic or a back-up antibiotic prescription."
                rationale = (
                    "NICE NG84 classifies FeverPAIN 2-3 as a group that may be more likely to benefit; "
                    "most people improve within about a week without antibiotics."
                )
            else:
                action_summary = f"{score_text}: consider an immediate or back-up antibiotic prescription."
                rationale = (
                    "NICE NG84 classifies FeverPAIN 4-5 as most likely to benefit, while still advising "
                    "consideration of adverse effects and the low absolute risk of complications."
                )
        else:
            strategy = _strategy_for_centor(centor_score)
            score_text = f"Centor {centor_score}/4"
            if strategy == PrescribingStrategy.NO_ANTIBIOTIC:
                action_summary = f"{score_text}: do not offer an antibiotic on the basis of the score alone."
                rationale = "NICE NG84 classifies Centor 0-2 as unlikely to benefit from antibiotics."
            else:
                action_summary = f"{score_text}: consider an immediate or back-up antibiotic prescription."
                rationale = "NICE NG84 classifies Centor 3-4 as most likely to benefit from antibiotics."

        antibiotic_options = []
        if strategy in {PrescribingStrategy.DELAYED_PRESCRIPTION, PrescribingStrategy.IMMEDIATE_ANTIBIOTIC}:
            antibiotic_options = [
                asdict(item)
                for item in get_antibiotic_regimens(
                    penicillin_allergic=penicillin_allergic,
                    severe_penicillin_allergy=severe_penicillin_allergy,
                    age_years=age_years,
                    weight_kg=weight_kg,
                )
            ]

    symptomatic_care = [
        "Explain that acute sore throat usually lasts around 1 week and often resolves without antibiotics.",
        "Consider paracetamol or, if suitable, ibuprofen for pain or fever.",
        "Maintain adequate fluid intake.",
        "Medicated lozenges may reduce pain modestly in adults.",
        "Seek medical help if symptoms worsen rapidly or significantly, do not start to improve after 1 week, or the person becomes systemically very unwell.",
    ]

    if rule == "feverpain" and age_years is not None and age_years < 3:
        guidance_note = "FeverPAIN was not tested in people under 3 years; use age-appropriate paediatric assessment."
    elif age_years is not None and age_years < 5 and fever_past_24h:
        guidance_note = "NICE NG84 directs children under 5 with fever to the fever-in-under-5s guideline."
    else:
        guidance_note = "Use one scoring rule consistently; do not combine FeverPAIN and Centor thresholds into a hybrid rule."

    return ClinicalEvaluationResult(
        feverpain_score=fp_score,
        feverpain_strep_risk_pct=fp_risk_str,
        feverpain_risk_numeric=fp_risk_num,
        feverpain_tier=fp_tier,
        feverpain_recommendation=fp_rec,
        centor_score=centor_score,
        centor_strep_risk_pct=centor_risk_str,
        centor_risk_numeric=centor_risk_num,
        centor_tier=centor_tier,
        mcisaac_score=mcisaac_score,
        mcisaac_strep_risk_pct=mcisaac_risk,
        prescribing_strategy=strategy,
        action_summary=action_summary,
        antibiotic_options=antibiotic_options,
        symptomatic_care=symptomatic_care,
        red_flag_assessment=asdict(red_flags),
        rationale=rationale,
        decision_rule=rule,
        guidance_note=guidance_note,
    )


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "t", "positive"}
    return False


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _first_present(kwargs: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in kwargs:
            return kwargs[key]
    return None


def calculate_metrics(**kwargs: Any) -> Dict[str, Any]:
    """Backward-compatible dictionary entry point with robust alias handling."""
    fever = _to_bool(_first_present(kwargs, "fever_past_24h", "fever", "history_of_fever"))
    pus = _to_bool(_first_present(kwargs, "purulence_or_pus", "pus", "tonsillar_exudate", "exudate"))
    rapid = _to_bool(_first_present(kwargs, "rapid_attendance_le_3d", "rapid_attendance", "symptoms_le_3d", "rapid_onset"))
    inflamed = _to_bool(_first_present(kwargs, "severely_inflamed_tonsils", "inflamed_tonsils", "severe_inflammation"))
    no_cough = _to_bool(_first_present(kwargs, "no_cough_or_coryza", "no_cough", "absence_of_cough"))

    tender_value = _first_present(kwargs, "tender_anterior_cervical_nodes", "tender_nodes", "lymphadenopathy")
    tender_nodes = _to_bool(tender_value) if tender_value is not None else None

    age = _to_float(_first_present(kwargs, "age_years", "age"))
    weight = _to_float(_first_present(kwargs, "weight_kg", "weight"))
    pen_allergy = _to_bool(_first_present(kwargs, "penicillin_allergic", "penicillin_allergy"))
    severe_pen_allergy = _to_bool(_first_present(kwargs, "severe_penicillin_allergy"))

    return evaluate_sore_throat(
        fever_past_24h=fever,
        purulence_or_pus=pus,
        rapid_attendance_le_3d=rapid,
        severely_inflamed_tonsils=inflamed,
        no_cough_or_coryza=no_cough,
        tender_anterior_cervical_nodes=tender_nodes,
        age_years=age,
        weight_kg=weight,
        penicillin_allergic=pen_allergy,
        severe_penicillin_allergy=severe_pen_allergy,
        stridor=_to_bool(_first_present(kwargs, "stridor")),
        difficulty_breathing=_to_bool(_first_present(kwargs, "difficulty_breathing")),
        difficulty_swallowing_saliva=_to_bool(_first_present(kwargs, "difficulty_swallowing_saliva", "drooling")),
        peritonsillar_swelling_trismus=_to_bool(_first_present(kwargs, "peritonsillar_swelling_trismus", "trismus", "quinsy")),
        systemic_sepsis_signs=_to_bool(_first_present(kwargs, "systemic_sepsis_signs", "sepsis")),
        severe_unilateral_pain=_to_bool(_first_present(kwargs, "severe_unilateral_pain")),
        decision_rule=str(_first_present(kwargs, "decision_rule") or "feverpain"),
    ).to_dict()


def process_batch_csv(input_csv: str, output_csv: str) -> int:
    """Score CSV rows and append compact result fields."""
    with open(input_csv, mode="r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Input CSV must contain a header row")
        rows = list(reader)

    if not rows:
        return 0

    out_rows: List[Dict[str, Any]] = []
    for row in rows:
        result = calculate_metrics(**row)
        merged = dict(row)
        merged.update(
            feverpain_score=result["feverpain_score"],
            feverpain_risk=result["feverpain_strep_risk_pct"],
            centor_score=result.get("centor_score", ""),
            mcisaac_score=result.get("mcisaac_score", ""),
            decision_rule=result["decision_rule"],
            prescribing_strategy=result["prescribing_strategy"],
            action_summary=result["action_summary"],
        )
        out_rows.append(merged)

    with open(output_csv, mode="w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)
