import { evaluate } from "./scoring.mjs";

const form = document.querySelector("#assessment-form");
const resultCard = document.querySelector("#result-card");
const themeButton = document.querySelector("#theme-toggle");
const resetButton = document.querySelector("#reset-button");
const centorOnly = document.querySelectorAll("[data-centor-only]");
const feverPainOnly = document.querySelectorAll("[data-feverpain-only]");

function checked(id) {
  return document.querySelector(`#${id}`).checked;
}

function numberValue(id) {
  const raw = document.querySelector(`#${id}`).value.trim();
  if (!raw) return Number.NaN;
  return Number(raw);
}

function collect() {
  return {
    rule: new FormData(form).get("rule") || "feverpain",
    fever: checked("fever"),
    purulence: checked("purulence"),
    rapid: checked("rapid"),
    inflamed: checked("inflamed"),
    noCough: checked("no-cough"),
    nodes: checked("nodes"),
    stridor: checked("stridor"),
    breathing: checked("breathing"),
    swallowing: checked("swallowing"),
    trismus: checked("trismus"),
    sepsis: checked("sepsis"),
    unilateral: checked("unilateral"),
    age: numberValue("age"),
    weight: numberValue("weight"),
    penicillinAllergy: checked("penicillin-allergy")
  };
}

function render(result) {
  resultCard.classList.toggle("urgent", result.urgent);
  resultCard.querySelector("[data-result-title]").textContent = result.heading;
  resultCard.querySelector("[data-result-guidance]").textContent = result.guidance;
  resultCard.querySelector("[data-fp-score]").textContent = `${result.fp}/5`;
  resultCard.querySelector("[data-centor-score]").textContent = `${result.centor}/4`;
  resultCard.querySelector("[data-active-rule]").textContent = result.rule === "centor" ? "Centor" : "FeverPAIN";
  resultCard.querySelector("[data-risk]").textContent = result.risk || "—";
  resultCard.querySelector("[data-note]").textContent = result.note;

  const antibiotic = resultCard.querySelector("[data-antibiotic]");
  const antibioticRow = antibiotic.closest(".result-detail");
  if (result.antibiotic) {
    antibiotic.textContent = result.antibiotic;
    antibioticRow.hidden = false;
  } else {
    antibiotic.textContent = "";
    antibioticRow.hidden = true;
  }

  resultCard.dataset.state = "ready";
  resultCard.setAttribute("aria-live", "polite");
}

function updateRuleVisibility() {
  const rule = new FormData(form).get("rule") || "feverpain";
  feverPainOnly.forEach((node) => node.classList.toggle("muted-control", rule !== "feverpain"));
  centorOnly.forEach((node) => node.classList.toggle("muted-control", rule !== "centor"));
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = collect();
  if (Number.isFinite(data.age) && data.age < 0) {
    document.querySelector("#age").focus();
    return;
  }
  if (Number.isFinite(data.weight) && data.weight <= 0) {
    document.querySelector("#weight").focus();
    return;
  }
  render(evaluate(data));
});

form.addEventListener("change", (event) => {
  if (event.target.name === "rule") updateRuleVisibility();
});

resetButton.addEventListener("click", () => {
  form.reset();
  updateRuleVisibility();
  resultCard.dataset.state = "empty";
  resultCard.classList.remove("urgent");
  resultCard.querySelector("[data-result-title]").textContent = "Ready to analyse";
  resultCard.querySelector("[data-result-guidance]").textContent = "Select the criteria, choose a decision rule, then press Analyse.";
  resultCard.querySelector("[data-fp-score]").textContent = "—";
  resultCard.querySelector("[data-centor-score]").textContent = "—";
  resultCard.querySelector("[data-active-rule]").textContent = "—";
  resultCard.querySelector("[data-risk]").textContent = "—";
  resultCard.querySelector("[data-note]").textContent = "No patient-identifiable data are stored or transmitted by this page.";
  resultCard.querySelector("[data-antibiotic]").closest(".result-detail").hidden = true;
});

themeButton.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  themeButton.setAttribute("aria-pressed", String(next === "dark"));
  themeButton.textContent = next === "dark" ? "Light" : "Dark";
});

updateRuleVisibility();
