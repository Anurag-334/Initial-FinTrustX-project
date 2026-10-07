/**
 * =========================================================
 * FINTRUSTX — Frontend Application Script
 * Connects directly to FastAPI backend (XGBoost + SHAP)
 * Author: Anurag Kashyap
 * =========================================================
 */

// Central API Base URL Configuration
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? "http://127.0.0.1:8000" 
  : (window.location.origin || "http://127.0.0.1:8000");

// API Key for Security
const API_KEY = "dev_api_key_123";

// Utility to escape HTML and prevent XSS
function escapeHtml(unsafe) {
  if (unsafe == null) return "";
  return unsafe
    .toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Fallback Benchmark Metrics (Test-set)
const DEFAULT_METRICS = {
  "ROC AUC": 0.7610,
  "Average Precision": 0.2507,
  "Recall": 0.6697,
  "F1 Score": 0.2724,
};

// Preset Demo Profiles
const PRESET_PROFILES = {
  prime: {
    SK_ID_CURR: 100003,
    NAME_CONTRACT_TYPE: "Cash loans",
    CODE_GENDER: "F",
    FLAG_OWN_CAR: "Y",
    FLAG_OWN_REALTY: "Y",
    CNT_CHILDREN: 0,
    AMT_INCOME_TOTAL: 270000,
    AMT_CREDIT: 450000,
    AMT_ANNUITY: 28000,
    AMT_GOODS_PRICE: 450000,
    NAME_INCOME_TYPE: "Commercial associate",
    NAME_EDUCATION_TYPE: "Higher education",
    NAME_FAMILY_STATUS: "Married",
    NAME_HOUSING_TYPE: "House / apartment",
    age_years: 42,
    employed_years: 8.5,
    EXT_SOURCE_1: 0.78,
    EXT_SOURCE_2: 0.82,
    EXT_SOURCE_3: 0.86,
    OCCUPATION_TYPE: "Managers",
    ORGANIZATION_TYPE: "Bank",
    REGION_RATING_CLIENT: 1
  },
  moderate: {
    SK_ID_CURR: 100045,
    NAME_CONTRACT_TYPE: "Cash loans",
    CODE_GENDER: "M",
    FLAG_OWN_CAR: "N",
    FLAG_OWN_REALTY: "Y",
    CNT_CHILDREN: 1,
    AMT_INCOME_TOTAL: 150000,
    AMT_CREDIT: 400000,
    AMT_ANNUITY: 24000,
    AMT_GOODS_PRICE: 380000,
    NAME_INCOME_TYPE: "Working",
    NAME_EDUCATION_TYPE: "Secondary / secondary special",
    NAME_FAMILY_STATUS: "Married",
    NAME_HOUSING_TYPE: "House / apartment",
    age_years: 34,
    employed_years: 3.2,
    EXT_SOURCE_1: 0.46,
    EXT_SOURCE_2: 0.52,
    EXT_SOURCE_3: 0.41,
    OCCUPATION_TYPE: "Laborers",
    ORGANIZATION_TYPE: "Business Entity Type 3",
    REGION_RATING_CLIENT: 2
  },
  subprime: {
    SK_ID_CURR: 100002,
    NAME_CONTRACT_TYPE: "Cash loans",
    CODE_GENDER: "M",
    FLAG_OWN_CAR: "N",
    FLAG_OWN_REALTY: "N",
    CNT_CHILDREN: 2,
    AMT_INCOME_TOTAL: 90000,
    AMT_CREDIT: 600000,
    AMT_ANNUITY: 35000,
    AMT_GOODS_PRICE: 550000,
    NAME_INCOME_TYPE: "Working",
    NAME_EDUCATION_TYPE: "Secondary / secondary special",
    NAME_FAMILY_STATUS: "Single / not married",
    NAME_HOUSING_TYPE: "Rented apartment",
    age_years: 26,
    employed_years: 0.8,
    EXT_SOURCE_1: 0.08,
    EXT_SOURCE_2: 0.26,
    EXT_SOURCE_3: 0.14,
    OCCUPATION_TYPE: "Laborers",
    ORGANIZATION_TYPE: "Construction",
    REGION_RATING_CLIENT: 3
  }
};

/**
 * Initialize Application on DOM Ready
 */
document.addEventListener("DOMContentLoaded", () => {
  initializeApp();
});

function initializeApp() {
  // Check API Health immediately & periodically
  checkApiHealth();
  setInterval(checkApiHealth, 25000);

  // Load Model Info & Benchmarks
  loadModelInfo();

  // Attach Form Handlers
  const form = document.getElementById("assessment-form");
  if (form) {
    form.addEventListener("submit", handleFormSubmission);
  }

  // Preset Profile Buttons
  document.querySelectorAll(".btn-preset").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const profile = btn.dataset.profile;
      loadPresetProfile(profile);
    });
  });

  // Range Sliders Value Updates
  const sliders = [
    { id: "slider-ext1", valId: "val-ext1" },
    { id: "slider-ext2", valId: "val-ext2" },
    { id: "slider-ext3", valId: "val-ext3" },
  ];

  sliders.forEach(({ id, valId }) => {
    const slider = document.getElementById(id);
    const badge = document.getElementById(valId);
    if (slider && badge) {
      slider.addEventListener("input", () => {
        badge.textContent = Number(slider.value).toFixed(2);
      });
    }
  });

  // Reset Button
  const resetBtn = document.getElementById("btn-reset-form");
  if (resetBtn) {
    resetBtn.addEventListener("click", resetAssessment);
  }

  // Load default prime profile for immediate testability
  loadPresetProfile("prime");
}

/**
 * 1. Check API Health (GET /health)
 */
async function checkApiHealth() {
  const badge = document.getElementById("status-indicator");
  const text = document.getElementById("status-text");

  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: { "Accept": "application/json", "X-API-Key": API_KEY }
    });

    if (response.ok) {
      const data = await response.json();
      if (badge && text) {
        badge.className = "status-indicator online";
        text.textContent = `API Online (${data.model ? data.model.toUpperCase() : 'XGBOOST'})`;
      }
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (err) {
    if (badge && text) {
      badge.className = "status-indicator offline";
      text.textContent = "API Offline";
    }
  }
}

/**
 * 2. Load Model Info & Metrics (GET /model-info)
 */
async function loadModelInfo() {
  try {
    const response = await fetch(`${API_BASE_URL}/model-info`, {
      method: "GET",
      headers: { "Accept": "application/json", "X-API-Key": API_KEY }
    });

    if (response.ok) {
      const data = await response.json();
      const metrics = data.performance_metrics || DEFAULT_METRICS;
      renderBenchmarkCards(metrics);
    } else {
      renderBenchmarkCards(DEFAULT_METRICS);
    }
  } catch (err) {
    renderBenchmarkCards(DEFAULT_METRICS);
  }
}

function renderBenchmarkCards(metrics) {
  const rocAuc = metrics["ROC AUC"] || metrics["roc_auc"] || DEFAULT_METRICS["ROC AUC"];
  const prAuc = metrics["Average Precision"] || metrics["pr_auc"] || DEFAULT_METRICS["Average Precision"];
  const recall = metrics["Recall"] || metrics["recall"] || DEFAULT_METRICS["Recall"];
  const f1 = metrics["F1 Score"] || metrics["f1"] || DEFAULT_METRICS["F1 Score"];

  document.getElementById("metric-roc-auc").textContent = Number(rocAuc).toFixed(4);
  document.getElementById("metric-pr-auc").textContent = Number(prAuc).toFixed(4);
  document.getElementById("metric-recall").textContent = `${(Number(recall) * 100).toFixed(2)}%`;
  document.getElementById("metric-f1").textContent = Number(f1).toFixed(4);
}

/**
 * 3. Load Preset Profile into Form
 */
function loadPresetProfile(profileKey) {
  const profile = PRESET_PROFILES[profileKey];
  if (!profile) return;

  const form = document.getElementById("assessment-form");
  if (!form) return;

  for (const [key, val] of Object.entries(profile)) {
    const field = form.elements[key];
    if (field) {
      field.value = val;
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  // Ensure preset's SK_ID_CURR correctly populates into the SK_ID_CURR input field
  if (profile.SK_ID_CURR !== undefined && form.elements['SK_ID_CURR']) {
    form.elements['SK_ID_CURR'].value = profile.SK_ID_CURR;
  }

  showToast(`Loaded ${profileKey.toUpperCase()} applicant profile.`, "info");
}

/**
 * 4. Collect Form Data & Map to API Request Schema
 */
function collectFormData() {
  const form = document.getElementById("assessment-form");
  const formData = new FormData(form);
  const raw = Object.fromEntries(formData.entries());

  const ageYears = parseFloat(raw.age_years) || 35;
  const employedYears = parseFloat(raw.employed_years) || 3;

  const payload = {
    NAME_CONTRACT_TYPE: raw.NAME_CONTRACT_TYPE || "Cash loans",
    CODE_GENDER: raw.CODE_GENDER || "M",
    FLAG_OWN_CAR: raw.FLAG_OWN_CAR || "N",
    FLAG_OWN_REALTY: raw.FLAG_OWN_REALTY || "Y",
    CNT_CHILDREN: parseInt(raw.CNT_CHILDREN) || 0,
    AMT_INCOME_TOTAL: parseFloat(raw.AMT_INCOME_TOTAL),
    AMT_CREDIT: parseFloat(raw.AMT_CREDIT),
    AMT_ANNUITY: parseFloat(raw.AMT_ANNUITY),
    AMT_GOODS_PRICE: parseFloat(raw.AMT_GOODS_PRICE),
    NAME_INCOME_TYPE: raw.NAME_INCOME_TYPE || "Working",
    NAME_EDUCATION_TYPE: raw.NAME_EDUCATION_TYPE || "Secondary / secondary special",
    NAME_FAMILY_STATUS: raw.NAME_FAMILY_STATUS || "Married",
    NAME_HOUSING_TYPE: raw.NAME_HOUSING_TYPE || "House / apartment",
    DAYS_BIRTH: -1 * Math.round(ageYears * 365.25),
    DAYS_EMPLOYED: -1 * Math.round(employedYears * 365.25),
    EXT_SOURCE_1: parseFloat(raw.EXT_SOURCE_1),
    EXT_SOURCE_2: parseFloat(raw.EXT_SOURCE_2),
    EXT_SOURCE_3: parseFloat(raw.EXT_SOURCE_3),
    REGION_RATING_CLIENT: parseInt(raw.REGION_RATING_CLIENT) || 2,
    OCCUPATION_TYPE: raw.OCCUPATION_TYPE || "Laborers",
    ORGANIZATION_TYPE: raw.ORGANIZATION_TYPE || "Business Entity Type 3",
  };

  const rawId = form.elements['SK_ID_CURR']?.value?.trim();
  if (rawId && !isNaN(parseInt(rawId, 10))) {
    payload.SK_ID_CURR = parseInt(rawId, 10);
  }

  return payload;
}

/**
 * 5. Validate Form Inputs Client-Side
 */
function validateForm(data) {
  const errors = [];

  if (data.SK_ID_CURR !== undefined && data.SK_ID_CURR !== null && (isNaN(data.SK_ID_CURR) || data.SK_ID_CURR <= 0)) {
    errors.push("Applicant ID must be a positive integer.");
  }

  if (isNaN(data.AMT_INCOME_TOTAL) || data.AMT_INCOME_TOTAL <= 0) {
    errors.push("Annual Income must be a positive number.");
  }
  if (isNaN(data.AMT_CREDIT) || data.AMT_CREDIT <= 0) {
    errors.push("Credit Amount Requested must be a positive number.");
  }
  if (isNaN(data.AMT_ANNUITY) || data.AMT_ANNUITY <= 0) {
    errors.push("Loan Annuity must be a positive number.");
  }
  if (isNaN(data.AMT_GOODS_PRICE) || data.AMT_GOODS_PRICE <= 0) {
    errors.push("Goods Price must be a positive number.");
  }
  if (isNaN(data.DAYS_BIRTH) || data.DAYS_BIRTH > -6570 || data.DAYS_BIRTH < -36525) {
    errors.push("Applicant Age must be between 18 and 100 years.");
  }
  if (isNaN(data.DAYS_EMPLOYED) || data.DAYS_EMPLOYED > 0) {
    errors.push("Employment Duration must be a valid number (non-positive in DAYS_EMPLOYED schema).");
  }
  if (isNaN(data.EXT_SOURCE_1) || isNaN(data.EXT_SOURCE_2) || isNaN(data.EXT_SOURCE_3)) {
    errors.push("Credit Bureau Scores (EXT_SOURCE_1-3) must be valid numbers.");
  }

  return errors;
}

/**
 * 6. Submit Prediction to Backend (POST /predict?explain=true)
 */
async function submitPrediction(payload) {
  const url = `${API_BASE_URL}/predict?explain=true&threshold=0.50`;
  
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "X-API-Key": API_KEY
    },
    body: JSON.stringify(payload)
  });

  const data = await response.json();

  if (!response.ok) {
    if (response.status === 422 && data && data.details) {
      const fieldErrors = data.details.map(d => `${d.loc ? d.loc.slice(1).join('.') : 'field'}: ${d.msg}`).join(', ');
      throw new Error(`Validation Error: ${fieldErrors}`);
    }
    throw new Error(data.message || data.detail || `Error ${response.status}: Failed to generate prediction.`);
  }

  return data;
}

/**
 * Form Submit Event Handler
 */
async function handleFormSubmission(e) {
  e.preventDefault();
  const form = e.target;
  const submitBtn = document.getElementById("btn-submit-assessment");

  const payload = collectFormData();
  const validationErrors = validateForm(payload);

  if (validationErrors.length > 0) {
    showToast(validationErrors[0], "error");
    return;
  }

  // Set UI to Loading State
  const emptyState = document.getElementById("empty-state");
  const loadingState = document.getElementById("loading-state");
  const resultContent = document.getElementById("result-content");

  if (emptyState) emptyState.style.display = "none";
  if (resultContent) resultContent.style.display = "none";
  if (loadingState) loadingState.style.display = "block";
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Analyzing applicant...';
  }

  try {
    const result = await submitPrediction(payload);
    displayPredictionResult(result);
    showToast("Credit risk assessment successfully generated.", "success");
  } catch (error) {
    if (loadingState) loadingState.style.display = "none";
    if (emptyState) emptyState.style.display = "block";
    displayApiError(error.message);
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Assess Credit Risk';
    }
  }
}

/**
 * 7. Display Prediction Results in UI
 */
function displayPredictionResult(result) {
  const loadingState = document.getElementById("loading-state");
  const emptyState = document.getElementById("empty-state");
  const resultContent = document.getElementById("result-content");

  if (loadingState) loadingState.style.display = "none";
  if (emptyState) emptyState.style.display = "none";
  if (resultContent) resultContent.style.display = "block";

  // Decision Banner & Risk Tier Pill
  const heroBanner = document.getElementById("decision-hero");
  const decisionText = document.getElementById("decision-text");
  const tierBadge = document.getElementById("tier-badge");

  const dec = result.loan_decision || "Manual Review";
  const cat = result.risk_category || "Moderate Risk";

  if (decisionText) decisionText.textContent = dec;
  if (tierBadge) tierBadge.textContent = cat;

  const heroSubtitle = document.querySelector("#decision-hero .decision-hero-text span");
  if (heroSubtitle) {
    if (result.applicant_id) {
      heroSubtitle.innerHTML = `Underwriting Recommendation &bull; <span style="color: #38bdf8; font-family: var(--font-mono);">ID #${escapeHtml(result.applicant_id)}</span>`;
    } else {
      heroSubtitle.textContent = "Underwriting Recommendation";
    }
  }

  if (heroBanner && tierBadge) {
    if (cat === "Low Risk" || dec.includes("Approved")) {
      heroBanner.className = "decision-hero approved";
      tierBadge.className = "tier-badge low";
    } else if (cat === "Moderate Risk" || dec.includes("Review")) {
      heroBanner.className = "decision-hero review";
      tierBadge.className = "tier-badge moderate";
    } else {
      heroBanner.className = "decision-hero rejected";
      tierBadge.className = "tier-badge critical";
    }
  }

  // KPI Metrics
  const probPercent = (result.default_probability * 100).toFixed(1);
  document.getElementById("res-probability").textContent = `${probPercent}%`;
  document.getElementById("res-score").textContent = result.risk_score ? result.risk_score.toFixed(1) : probPercent;
  document.getElementById("res-threshold").textContent = (result.threshold_used || 0.50).toFixed(2);

  // Horizontal Progress Fill
  const progressFill = document.getElementById("progress-fill");
  if (progressFill) {
    progressFill.style.width = `${Math.min(100, Math.max(0, probPercent))}%`;
    if (cat === "Low Risk") {
      progressFill.style.background = "var(--risk-low)";
    } else if (cat === "Moderate Risk") {
      progressFill.style.background = "var(--risk-moderate)";
    } else {
      progressFill.style.background = "linear-gradient(90deg, #f59e0b 0%, #e11d48 100%)";
    }
  }

  // Render SHAP Feature Explanation
  displayExplanation(result.explanation);
}

/**
 * 8. Display SHAP Feature Explanations
 */
function displayExplanation(explanation) {
  const container = document.getElementById("shap-factors-container");
  if (!container) return;

  if (!explanation || (!explanation.top_risk_factors?.length && !explanation.protective_factors?.length)) {
    container.innerHTML = '<p style="color: var(--text-subtle); font-size: 0.85rem;">No localized SHAP explanations available for this assessment.</p>';
    return;
  }

  let html = '';

  // Top Risk Factors (+SHAP)
  if (explanation.top_risk_factors && explanation.top_risk_factors.length > 0) {
    explanation.top_risk_factors.slice(0, 3).forEach(factor => {
      html += `
        <div class="factor-card risk">
          <div>
            <div class="factor-name">${escapeHtml(formatFeatureLabel(factor.feature))}</div>
            <span style="font-size: 0.7rem; color: var(--text-subtle);">${escapeHtml(factor.impact)}</span>
          </div>
          <span class="factor-impact">+${Math.abs(factor.contribution).toFixed(3)}</span>
        </div>
      `;
    });
  }

  // Top Protective Factors (-SHAP)
  if (explanation.protective_factors && explanation.protective_factors.length > 0) {
    explanation.protective_factors.slice(0, 3).forEach(factor => {
      html += `
        <div class="factor-card protect">
          <div>
            <div class="factor-name">${escapeHtml(formatFeatureLabel(factor.feature))}</div>
            <span style="font-size: 0.7rem; color: var(--text-subtle);">${escapeHtml(factor.impact)}</span>
          </div>
          <span class="factor-impact">-${Math.abs(factor.contribution).toFixed(3)}</span>
        </div>
      `;
    });
  }

  container.innerHTML = html;
}

/**
 * 9. Display Error Notice
 */
function displayApiError(message) {
  showToast(message, "error");
}

/**
 * 10. Reset Form & Results
 */
function resetAssessment() {
  const form = document.getElementById("assessment-form");
  if (form) form.reset();

  const emptyState = document.getElementById("empty-state");
  const resultContent = document.getElementById("result-content");
  const loadingState = document.getElementById("loading-state");

  if (emptyState) emptyState.style.display = "block";
  if (resultContent) resultContent.style.display = "none";
  if (loadingState) loadingState.style.display = "none";

  const heroSubtitle = document.querySelector("#decision-hero .decision-hero-text span");
  if (heroSubtitle) {
    heroSubtitle.textContent = "Underwriting Recommendation";
  }

  showToast("Assessment form reset.", "info");
}

/**
 * Helper: Format Raw Feature Names to Clean Titles
 */
function formatFeatureLabel(name) {
  return name
    .replace(/^num__/, '')
    .replace(/^cat__/, '')
    .replace(/_/g, ' ')
    .replace(/DAYS BIRTH/, 'Applicant Age')
    .replace(/DAYS EMPLOYED/, 'Employment Duration')
    .replace(/EXT SOURCE 1/, 'Credit Bureau Score 1')
    .replace(/EXT SOURCE 2/, 'Credit Bureau Score 2')
    .replace(/EXT SOURCE 3/, 'Credit Bureau Score 3')
    .replace(/AMT CREDIT/, 'Credit Requested')
    .replace(/AMT INCOME TOTAL/, 'Annual Income')
    .replace(/AMT ANNUITY/, 'Loan Annuity')
    .replace(/AMT GOODS PRICE/, 'Goods Price');
}

/**
 * Helper: Toast Notifications
 */
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.25s ease";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}
