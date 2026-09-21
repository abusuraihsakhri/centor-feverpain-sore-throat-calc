export function feverPainScore(data) {
  return [data.fever, data.purulence, data.rapid, data.inflamed, data.noCough]
    .reduce((sum, value) => sum + (Boolean(value) ? 1 : 0), 0);
}

export function centorScore(data) {
  return [data.purulence, data.nodes, data.fever, data.noCough]
    .reduce((sum, value) => sum + (Boolean(value) ? 1 : 0), 0);
}

export function feverPainBand(score) {
  if (score <= 1) {
    return {
      risk: "13–18%",
      strategy: "NO_ANTIBIOTIC",
      heading: "No antibiotic",
      guidance: "Do not offer an antibiotic. Provide self-care and safety-netting advice."
    };
  }
  if (score <= 3) {
    return {
      risk: "34–40%",
      strategy: "DELAYED_PRESCRIPTION",
      heading: "No antibiotic or back-up prescription",
      guidance: "Consider no antibiotic or a back-up prescription. If issued, use it if symptoms do not start to improve within 3–5 days or worsen rapidly or significantly."
    };
  }
  return {
    risk: "62–65%",
    strategy: "IMMEDIATE_ANTIBIOTIC",
    heading: "Immediate or back-up prescription",
    guidance: "Consider an immediate antibiotic or a back-up prescription, taking adverse effects and the low absolute risk of complications into account."
  };
}

export function centorBand(score) {
  if (score <= 2) {
    return {
      strategy: "NO_ANTIBIOTIC",
      heading: "No antibiotic",
      guidance: "Centor 0–2: do not offer an antibiotic on the basis of the score alone."
    };
  }
  return {
    strategy: "IMMEDIATE_ANTIBIOTIC",
    heading: "Immediate or back-up prescription",
    guidance: "Centor 3–4: consider an immediate or back-up antibiotic prescription."
  };
}

export function hasRedFlags(data) {
  return [data.stridor, data.breathing, data.swallowing, data.trismus, data.sepsis, data.unilateral]
    .some(Boolean);
}

export function antibioticOption({ penicillinAllergy, age, weight }) {
  const parsedAge = Number.isFinite(age) ? age : null;
  const parsedWeight = Number.isFinite(weight) ? weight : null;

  if (parsedAge !== null && parsedAge < 1 / 12) {
    return "No dosing recommendation is provided here for infants under 1 month; use specialist/BNF guidance.";
  }

  if (!penicillinAllergy) {
    let dose = "500 mg four times daily or 1,000 mg twice daily";
    if (parsedAge !== null && parsedAge < 12) {
      if (parsedAge >= 6) dose = "250 mg four times daily or 500 mg twice daily";
      else if (parsedAge >= 1) dose = "125 mg four times daily or 250 mg twice daily";
      else dose = "62.5 mg four times daily or 125 mg twice daily";
    }
    return `Phenoxymethylpenicillin: ${dose} for 5–10 days.`;
  }

  let dose = "250–500 mg twice daily";
  if (parsedAge !== null && parsedAge < 12) {
    if (parsedWeight === null) return "Clarithromycin: enter weight for the NICE paediatric weight-band dose.";
    if (parsedWeight < 8) dose = "7.5 mg/kg twice daily";
    else if (parsedWeight < 12) dose = "62.5 mg twice daily";
    else if (parsedWeight < 20) dose = "125 mg twice daily";
    else if (parsedWeight < 30) dose = "187.5 mg twice daily";
    else if (parsedWeight <= 40) dose = "250 mg twice daily";
    else return "Clarithromycin: check BNF/local formulary for a child over 40 kg.";
  }
  return `Clarithromycin: ${dose} for 5 days (not the pregnancy-specific alternative).`;
}

export function evaluate(data) {
  const fp = feverPainScore(data);
  const centor = centorScore(data);
  const redFlag = hasRedFlags(data);
  const rule = data.rule === "centor" ? "centor" : "feverpain";

  if (redFlag) {
    return {
      rule,
      fp,
      centor,
      urgent: true,
      heading: "Urgent clinical assessment",
      guidance: "A selected red flag may indicate serious illness or a suppurative complication. Do not rely on routine sore-throat scoring.",
      risk: null,
      strategy: "URGENT_REFERRAL",
      antibiotic: null,
      note: "Escalate according to local urgent-care pathways and clinical judgement."
    };
  }

  const band = rule === "centor" ? centorBand(centor) : feverPainBand(fp);
  const antibiotic = band.strategy === "NO_ANTIBIOTIC"
    ? null
    : antibioticOption(data);

  let note = "Use one rule consistently; do not combine FeverPAIN and Centor thresholds into a hybrid rule.";
  if (Number.isFinite(data.age) && data.age < 3 && rule === "feverpain") {
    note = "FeverPAIN was not tested in people under 3 years. Use age-appropriate paediatric assessment.";
  } else if (Number.isFinite(data.age) && data.age < 5 && data.fever) {
    note = "NICE NG84 directs children under 5 with fever to the fever-in-under-5s guideline.";
  }

  return {
    rule,
    fp,
    centor,
    urgent: false,
    heading: band.heading,
    guidance: band.guidance,
    risk: rule === "feverpain" ? band.risk : null,
    strategy: band.strategy,
    antibiotic,
    note
  };
}
