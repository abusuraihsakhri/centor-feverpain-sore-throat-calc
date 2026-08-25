"""
FeverPAIN and Centor Clinical Decision Rules for Acute Sore Throat & Pharyngitis
Implements validated clinical prediction rules (NICE NG84, Little et al. 2013, Centor et al. 1981, McIsaac et al. 1998)
for Group A Streptococcal (GAS) pharyngitis risk stratification and antimicrobial stewardship.

Author: Dr. Abu Suraih Sakhri
License: MIT
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


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

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["prescribing_strategy"] = self.prescribing_strategy.value
        d["feverpain_tier"] = self.feverpain_tier.value
        if self.centor_tier:
            d["centor_tier"] = self.centor_tier.value
        return d


def check_red_flags(
    stridor: bool = False,
    difficulty_breathing: bool = False,
    difficulty_swallowing_saliva: bool = False,
    peritonsillar_swelling_trismus: bool = False,
    systemic_sepsis_signs: bool = False,
    severe_unilateral_pain: bool = False,
) -> RedFlagAssessment:
    """
    Evaluates clinical red flags requiring immediate emergency hospital referral
    (e.g., epiglottitis, peritonsillar abscess/quinsy, retropharyngeal abscess, sepsis).
    """
    flags = []
    if stridor:
        flags.append("Stridor or upper airway compromise (Suspect Epiglottitis / Laryngeal Edema)")
    if difficulty_breathing:
        flags.append("Respiratory distress or compromised breathing")
    if difficulty_swallowing_saliva:
        flags.append("Inability to swallow fluids/saliva or drooling")
    if peritonsillar_swelling_trismus:
        flags.append("Trismus (inability to open mouth) or visible uvular deviation (Suspect Quinsy / Peritonsillar Abscess)")
    if systemic_sepsis_signs:
        flags.append("Signs of systemic sepsis (tachycardia, hypotension, altered mental status, cyanosis)")
    if severe_unilateral_pain:
        flags.append("Severe unilateral throat pain out of proportion to exam")

    if flags:
        return RedFlagAssessment(
            has_red_flags=True,
            flags_detected=flags,
            action_required="EMERGENCY REFERRAL: Same-day hospital / ENT / emergency evaluation required. Do not rely on outpatient scoring.",
        )
    return RedFlagAssessment(has_red_flags=False, flags_detected=[], action_required=None)


def calculate_feverpain(
    fever_past_24h: bool,
    purulence_or_pus: bool,
    rapid_attendance_le_3d: bool,
    severely_inflamed_tonsils: bool,
    no_cough_or_coryza: bool,
) -> Tuple[int, str, float, SeverityTier, str]:
    """
    Calculates FeverPAIN score (0-5) based on Little et al. (BMJ 2013) & NICE NG84.
    Criteria:
      F - Fever in past 24 hours (+1)
      P - Pus on tonsils / tonsillar exudate (+1)
      A - Attend rapidly (symptoms <= 3 days) (+1)
      I - Severely Inflamed tonsils (+1)
      N - No cough or coryza (+1)
    """
    score = 0
    if bool(fever_past_24h):
        score += 1
    if bool(purulence_or_pus):
        score += 1
    if bool(rapid_attendance_le_3d):
        score += 1
    if bool(severely_inflamed_tonsils):
        score += 1
    if bool(no_cough_or_coryza):
        score += 1

    if score <= 1:
        risk_str = "13% - 18%"
        risk_num = 15.5
        tier = SeverityTier.LOW
        rec = "Low GAS probability (13-18%). Antibiotics offer little benefit. Recommend symptomatic management only."
    elif score in (2, 3):
        risk_str = "34% - 40%"
        risk_num = 37.0
        tier = SeverityTier.MODERATE
        rec = "Intermediate GAS probability (34-40%). Consider a delayed prescription or throat swab. Instruct patient to fill prescription only if symptoms worsen or do not improve in 3-5 days."
    else:  # 4 or 5
        risk_str = "62% - 65%"
        risk_num = 63.5
        tier = SeverityTier.HIGH
        rec = "High GAS probability (62-65%). Immediate antibiotic prescription or targeted delayed prescription is indicated, alongside analgesia."

    return score, risk_str, risk_num, tier, rec


def calculate_centor(
    tonsillar_exudate: bool,
    tender_anterior_cervical_nodes: bool,
    history_of_fever: bool,
    absence_of_cough: bool,
) -> Tuple[int, str, float, SeverityTier, str]:
    """
    Calculates original Centor score (0-4) (Centor et al. 1981).
    Criteria:
      1. Tonsillar exudate (+1)
      2. Tender anterior cervical adenopathy (+1)
      3. Fever by history (>38.0 C / 100.4 F) (+1)
      4. Absence of cough (+1)
    """
    score = (
        (1 if tonsillar_exudate else 0)
        + (1 if tender_anterior_cervical_nodes else 0)
        + (1 if history_of_fever else 0)
        + (1 if absence_of_cough else 0)
    )

    if score <= 1:
        risk_str = "2.5% - 6%"
        risk_num = 4.2
        tier = SeverityTier.LOW
        rec = "Low probability of streptococcal infection. No testing or antibiotics indicated."
    elif score == 2:
        risk_str = "15% - 30%"
        risk_num = 22.5
        tier = SeverityTier.MODERATE
        rec = "Intermediate probability of streptococcal infection. Perform RADT or throat culture; treat only if positive."
    elif score == 3:
        risk_str = "30% - 40%"
        risk_num = 35.0
        tier = SeverityTier.HIGH
        rec = "High probability of streptococcal infection. Perform RADT/culture, or initiate empiric antibiotic therapy in high-risk patients."
    else:  # score == 4
        risk_str = "50% - 60%"
        risk_num = 55.0
        tier = SeverityTier.HIGH
        rec = "Very high probability of streptococcal infection (>50%). Empiric antibiotic treatment or RADT with antibiotic therapy is recommended."

    return score, risk_str, risk_num, tier, rec


def calculate_mcisaac(
    centor_score: int,
    age_years: float,
) -> Tuple[int, str, float]:
    """
    Calculates Modified Centor / McIsaac score (-1 to 5) (McIsaac et al. 1998, 2004).
    Age modifiers:
      3 - 14 years: +1
      15 - 44 years: 0
      >= 45 years: -1
    """
    if age_years < 0:
        raise ValueError(f"Age cannot be negative: {age_years}")

    score = centor_score
    if 3 <= age_years <= 14:
        score += 1
    elif age_years >= 45:
        score -= 1

    # Bounds: -1 to 5
    score = max(-1, min(5, score))

    if score <= 0:
        risk_str = "1% - 2.5%"
        risk_num = 1.8
    elif score == 1:
        risk_str = "5% - 10%"
        risk_num = 7.5
    elif score == 2:
        risk_str = "11% - 17%"
        risk_num = 14.0
    elif score == 3:
        risk_str = "28% - 35%"
        risk_num = 31.5
    else:  # 4 or 5
        risk_str = "51% - 53%"
        risk_num = 52.0

    return score, risk_str, risk_num


def get_antibiotic_regimens(
    penicillin_allergic: bool = False,
    severe_penicillin_allergy: bool = False,
    age_years: Optional[float] = None,
    weight_kg: Optional[float] = None,
) -> List[AntibioticRecommendation]:
    """
    Returns evidence-based antibiotic regimens aligned with NICE NG84, IDSA, and AAP guidelines.
    """
    regimens = []

    if not penicillin_allergic:
        # First-line Penicillin V (Phenoxymethylpenicillin)
        if age_years is not None and age_years < 12:
            dose_str = "12.5 mg/kg (or 250 mg for 1-5 yrs, 500 mg for 6-11 yrs)"
            if weight_kg:
                calc_dose = min(500, round(weight_kg * 12.5))
                dose_str = f"{calc_dose} mg"
            regimens.append(
                AntibioticRecommendation(
                    drug_name="Phenoxymethylpenicillin (Penicillin V)",
                    dose=dose_str,
                    frequency="Four times daily (QDS) or twice daily (BD)",
                    duration="5 to 10 days (10 days for eradication & rheumatic fever prevention)",
                    indication="First-line therapy for non-allergic GAS pharyngitis",
                    notes="Take on an empty stomach 1 hour before or 2 hours after meals.",
                )
            )
            regimens.append(
                AntibioticRecommendation(
                    drug_name="Amoxicillin",
                    dose=f"{min(1000, round(weight_kg * 25)) if weight_kg else '25-50 mg/kg/day'} (max 1000 mg/day)",
                    frequency="Divided into 2 or 3 doses daily",
                    duration="10 days",
                    indication="First-line alternative in pediatrics (better palatability)",
                    notes="Suspension is generally better tolerated by young children.",
                )
            )
        else:
            regimens.append(
                AntibioticRecommendation(
                    drug_name="Phenoxymethylpenicillin (Penicillin V)",
                    dose="500 mg",
                    frequency="Four times daily (QDS) OR 1000 mg twice daily (BD)",
                    duration="5 to 10 days",
                    indication="First-line standard of care for acute GAS pharyngitis",
                    notes="Take on an empty stomach. 10-day course provides maximum eradication.",
                )
            )
            regimens.append(
                AntibioticRecommendation(
                    drug_name="Amoxicillin",
                    dose="500 mg",
                    frequency="Three times daily (TDS)",
                    duration="7 to 10 days",
                    indication="Alternative oral beta-lactam",
                    notes="Caution if Infectious Mononucleosis / EBV is suspected (rash risk).",
                )
            )
    else:
        # Penicillin allergic
        if severe_penicillin_allergy:
            # Macrolide or Lincosamide
            if age_years is not None and age_years < 12:
                regimens.append(
                    AntibioticRecommendation(
                        drug_name="Clarithromycin",
                        dose="7.5 mg/kg (max 250 mg)",
                        frequency="Twice daily (BD)",
                        duration="5 days",
                        indication="First-line macrolide for severe penicillin allergy (anaphylaxis/angioedema)",
                        notes="May cause GI upset. Check local macrolide resistance rates.",
                    )
                )
                regimens.append(
                    AntibioticRecommendation(
                        drug_name="Erythromycin",
                        dose="125-250 mg (based on age/weight)",
                        frequency="Four times daily (QDS)",
                        duration="5 to 10 days",
                        indication="Alternative macrolide for severe penicillin allergy",
                        notes="Take with or immediately before food.",
                    )
                )
            else:
                regimens.append(
                    AntibioticRecommendation(
                        drug_name="Clarithromycin",
                        dose="250 mg to 500 mg",
                        frequency="Twice daily (BD)",
                        duration="5 days",
                        indication="Preferred macrolide for patients with severe penicillin allergy",
                        notes="Excellent tissue penetration. Monitor for CYP3A4 drug interactions.",
                    )
                )
                regimens.append(
                    AntibioticRecommendation(
                        drug_name="Erythromycin Ethylsuccinate / Stearate",
                        dose="500 mg",
                        frequency="Twice to four times daily",
                        duration="5 to 10 days",
                        indication="Alternative macrolide for penicillin-allergic patients",
                        notes="Preferred in pregnancy if macrolide indicated.",
                    )
                )
        else:
            # Non-severe penicillin allergy (mild rash): First-generation cephalosporin or macrolide
            if age_years is not None and age_years < 12:
                regimens.append(
                    AntibioticRecommendation(
                        drug_name="Cefalexin (Cephalexin)",
                        dose="12.5-25 mg/kg (max 500 mg)",
                        frequency="Twice to four times daily",
                        duration="5 to 10 days",
                        indication="First-generation cephalosporin for non-severe penicillin allergy",
                        notes="Do NOT use if history of anaphylaxis or angioedema to beta-lactams.",
                    )
                )
            else:
                regimens.append(
                    AntibioticRecommendation(
                        drug_name="Cefalexin (Cephalexin)",
                        dose="500 mg",
                        frequency="Twice daily (BD) or 500 mg TDS",
                        duration="5 to 10 days",
                        indication="First-line cephalosporin for non-type-1 penicillin allergy",
                        notes="Safe in mild non-IgE mediated penicillin reactions.",
                    )
                )
            regimens.append(
                AntibioticRecommendation(
                    drug_name="Clarithromycin",
                    dose="250 mg to 500 mg",
                    frequency="Twice daily (BD)",
                    duration="5 days",
                    indication="Macrolide alternative",
                    notes="Recommended if any concern regarding cephalosporin cross-reactivity.",
                )
            )

    return regimens


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
    # Red flags
    stridor: bool = False,
    difficulty_breathing: bool = False,
    difficulty_swallowing_saliva: bool = False,
    peritonsillar_swelling_trismus: bool = False,
    systemic_sepsis_signs: bool = False,
    severe_unilateral_pain: bool = False,
) -> ClinicalEvaluationResult:
    """
    Comprehensive Sore Throat Clinical Assessment combining FeverPAIN, Centor, McIsaac,
    Red-Flag screening, and NICE NG84 prescribing recommendations.
    """
    # 1. Red flag assessment
    red_flag_res = check_red_flags(
        stridor=stridor,
        difficulty_breathing=difficulty_breathing,
        difficulty_swallowing_saliva=difficulty_swallowing_saliva,
        peritonsillar_swelling_trismus=peritonsillar_swelling_trismus,
        systemic_sepsis_signs=systemic_sepsis_signs,
        severe_unilateral_pain=severe_unilateral_pain,
    )

    # 2. Calculate FeverPAIN
    fp_score, fp_risk_str, fp_risk_num, fp_tier, fp_rec = calculate_feverpain(
        fever_past_24h=fever_past_24h,
        purulence_or_pus=purulence_or_pus,
        rapid_attendance_le_3d=rapid_attendance_le_3d,
        severely_inflamed_tonsils=severely_inflamed_tonsils,
        no_cough_or_coryza=no_cough_or_coryza,
    )

    # 3. Calculate Centor (if relevant parameters given)
    c_nodes = tender_anterior_cervical_nodes if tender_anterior_cervical_nodes is not None else False
    c_score, c_risk_str, c_risk_num, c_tier, c_rec = calculate_centor(
        tonsillar_exudate=purulence_or_pus,
        tender_anterior_cervical_nodes=c_nodes,
        history_of_fever=fever_past_24h,
        absence_of_cough=no_cough_or_coryza,
    )

    # 4. Calculate McIsaac if age is available
    mc_score, mc_risk_str, mc_risk_num = (None, None, None)
    if age_years is not None:
        mc_score, mc_risk_str, mc_risk_num = calculate_mcisaac(c_score, age_years)

    # 5. Determine Prescribing Strategy & Recommendations
    if red_flag_res.has_red_flags:
        strategy = PrescribingStrategy.URGENT_REFERRAL
        action_summary = "URGENT REFERRAL: Immediate hospital / emergency evaluation required due to clinical red flags."
        rationale = f"Patient exhibits critical red flags: {', '.join(red_flag_res.flags_detected)}. Routine outpatient criteria superseded."
        antibiotics = []
    elif fp_score >= 4 or (c_score >= 3 and fp_score >= 3):
        strategy = PrescribingStrategy.IMMEDIATE_ANTIBIOTIC
        action_summary = f"Immediate antibiotic prescription recommended (FeverPAIN {fp_score}/5, Strep risk {fp_risk_str})."
        rationale = f"High probability of Group A Strep pharyngitis ({fp_risk_str}). Evidence indicates statistically significant symptom reduction and complication prevention with antibiotics."
        antibiotic_objs = get_antibiotic_regimens(
            penicillin_allergic=penicillin_allergic,
            severe_penicillin_allergy=severe_penicillin_allergy,
            age_years=age_years,
            weight_kg=weight_kg,
        )
        antibiotics = [asdict(a) for a in antibiotic_objs]
    elif fp_score in (2, 3):
        strategy = PrescribingStrategy.DELAYED_PRESCRIPTION
        action_summary = f"Delayed/back-up prescription or point-of-care RADT recommended (FeverPAIN {fp_score}/5, Strep risk {fp_risk_str})."
        rationale = f"Moderate likelihood of GAS ({fp_risk_str}). Provide back-up antibiotic script with clear instructions to only fill if symptoms worsen or fail to improve after 3-5 days."
        antibiotic_objs = get_antibiotic_regimens(
            penicillin_allergic=penicillin_allergic,
            severe_penicillin_allergy=severe_penicillin_allergy,
            age_years=age_years,
            weight_kg=weight_kg,
        )
        antibiotics = [asdict(a) for a in antibiotic_objs]
    else:
        strategy = PrescribingStrategy.NO_ANTIBIOTIC
        action_summary = f"No antibiotic indicated (FeverPAIN {fp_score}/5, Strep risk {fp_risk_str}). Symptomatic relief only."
        rationale = f"Low probability of bacterial pharyngitis ({fp_risk_str}). Viral etiology most likely. Antibiotics provide negligible benefit and carry adverse effect / resistance risks."
        antibiotics = []

    symptomatic_care = [
        "Adequate hydration and warm or cold soothing liquids.",
        "Analgesia: Paracetamol (Acetaminophen) and/or Ibuprofen for pain and fever relief.",
        "Medicated lozenges containing local anesthetic or anti-inflammatory agents.",
        "Salt water gargling (warm water with 1/2 teaspoon salt) for older children and adults.",
        "Safety netting: Advise patient to seek urgent care if they develop breathing difficulty, drooling, inability to swallow, or neck swelling.",
    ]

    return ClinicalEvaluationResult(
        feverpain_score=fp_score,
        feverpain_strep_risk_pct=fp_risk_str,
        feverpain_risk_numeric=fp_risk_num,
        feverpain_tier=fp_tier,
        feverpain_recommendation=fp_rec,
        centor_score=c_score,
        centor_strep_risk_pct=c_risk_str,
        centor_risk_numeric=c_risk_num,
        centor_tier=c_tier,
        mcisaac_score=mc_score,
        mcisaac_strep_risk_pct=mc_risk_str,
        prescribing_strategy=strategy,
        action_summary=action_summary,
        antibiotic_options=antibiotics,
        symptomatic_care=symptomatic_care,
        red_flag_assessment=asdict(red_flag_res),
        rationale=rationale,
    )


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """
    Unified entry point for backward compatibility and automated assessment pipelines.
    Accepts boolean or string/numeric parameters.
    """
    def _to_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val > 0
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "y", "t", "positive")
        return False

    def _to_float(val: Any) -> Optional[float]:
        if val is None or val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    fever = _to_bool(kwargs.get("fever_past_24h") or kwargs.get("fever") or kwargs.get("history_of_fever"))
    pus = _to_bool(kwargs.get("purulence_or_pus") or kwargs.get("pus") or kwargs.get("tonsillar_exudate") or kwargs.get("exudate"))
    rapid = _to_bool(kwargs.get("rapid_attendance_le_3d") or kwargs.get("rapid_attendance") or kwargs.get("symptoms_le_3d") or kwargs.get("rapid_onset"))
    inflamed = _to_bool(kwargs.get("severely_inflamed_tonsils") or kwargs.get("inflamed_tonsils") or kwargs.get("severe_inflammation"))
    no_cough = _to_bool(kwargs.get("no_cough_or_coryza") or kwargs.get("no_cough") or kwargs.get("absence_of_cough"))

    tender_nodes = _to_bool(kwargs.get("tender_anterior_cervical_nodes") or kwargs.get("tender_nodes") or kwargs.get("lymphadenopathy")) if any(k in kwargs for k in ("tender_anterior_cervical_nodes", "tender_nodes", "lymphadenopathy")) else None

    age = _to_float(kwargs.get("age_years") or kwargs.get("age"))
    weight = _to_float(kwargs.get("weight_kg") or kwargs.get("weight"))
    pen_allergy = _to_bool(kwargs.get("penicillin_allergic") or kwargs.get("penicillin_allergy"))
    sev_pen_allergy = _to_bool(kwargs.get("severe_penicillin_allergy"))

    # Red flags
    stridor = _to_bool(kwargs.get("stridor"))
    diff_breath = _to_bool(kwargs.get("difficulty_breathing"))
    diff_swallow = _to_bool(kwargs.get("difficulty_swallowing_saliva") or kwargs.get("drooling"))
    trismus = _to_bool(kwargs.get("peritonsillar_swelling_trismus") or kwargs.get("trismus") or kwargs.get("quinsy"))
    sepsis = _to_bool(kwargs.get("systemic_sepsis_signs") or kwargs.get("sepsis"))
    unilateral_pain = _to_bool(kwargs.get("severe_unilateral_pain"))

    res = evaluate_sore_throat(
        fever_past_24h=fever,
        purulence_or_pus=pus,
        rapid_attendance_le_3d=rapid,
        severely_inflamed_tonsils=inflamed,
        no_cough_or_coryza=no_cough,
        tender_anterior_cervical_nodes=tender_nodes,
        age_years=age,
        weight_kg=weight,
        penicillin_allergic=pen_allergy,
        severe_penicillin_allergy=sev_pen_allergy,
        stridor=stridor,
        difficulty_breathing=diff_breath,
        difficulty_swallowing_saliva=diff_swallow,
        peritonsillar_swelling_trismus=trismus,
        systemic_sepsis_signs=sepsis,
        severe_unilateral_pain=unilateral_pain,
    )
    return res.to_dict()


def process_batch_csv(input_csv: str, output_csv: str) -> int:
    """Processes a CSV file of sore throat cases and writes scored output."""
    with open(input_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return 0

    out_rows = []
    for r in rows:
        eval_res = calculate_metrics(**r)
        merged = dict(r)
        merged["feverpain_score"] = eval_res["feverpain_score"]
        merged["feverpain_risk"] = eval_res["feverpain_strep_risk_pct"]
        merged["centor_score"] = eval_res.get("centor_score", "")
        merged["mcisaac_score"] = eval_res.get("mcisaac_score", "")
        merged["prescribing_strategy"] = eval_res["prescribing_strategy"]
        merged["action_summary"] = eval_res["action_summary"]
        out_rows.append(merged)

    fieldnames = list(out_rows[0].keys())
    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)
