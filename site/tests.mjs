import assert from "node:assert/strict";
import { antibioticOption, centorScore, evaluate, feverPainBand, feverPainScore } from "./scoring.mjs";

const blank = {
  rule: "feverpain", fever: false, purulence: false, rapid: false, inflamed: false,
  noCough: false, nodes: false, stridor: false, breathing: false, swallowing: false,
  trismus: false, sepsis: false, unilateral: false, age: Number.NaN, weight: Number.NaN,
  penicillinAllergy: false
};

assert.equal(feverPainScore(blank), 0);
assert.equal(centorScore(blank), 0);
assert.equal(feverPainBand(3).strategy, "DELAYED_PRESCRIPTION");
assert.equal(feverPainBand(4).strategy, "IMMEDIATE_ANTIBIOTIC");

const hybridCase = { ...blank, fever: true, purulence: true, nodes: true };
assert.equal(evaluate(hybridCase).strategy, "DELAYED_PRESCRIPTION");
assert.equal(evaluate({ ...hybridCase, rule: "centor" }).strategy, "IMMEDIATE_ANTIBIOTIC");

assert.equal(evaluate({ ...blank, stridor: true }).strategy, "URGENT_REFERRAL");
assert.match(antibioticOption({ penicillinAllergy: false, age: 7, weight: 25 }), /250 mg four times daily/);
assert.match(antibioticOption({ penicillinAllergy: true, age: 7, weight: 18 }), /125 mg twice daily/);

console.log("Browser scoring tests passed");
