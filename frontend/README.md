# FinTrustX Frontend Dashboard

Modern, lightweight, and responsive frontend dashboard for **FinTrustX: Explainable AI Platform for Secure Credit Risk Assessment and Loan Decision Intelligence**.

---

## 🎨 Overview & Design Philosophy

The FinTrustX frontend is built using **HTML5, CSS3, and Vanilla JavaScript**, providing a fast, accessible, and dependency-free experience designed for financial intelligence and credit risk underwriters.

### Key Highlights:
- **Zero Build Step**: No Node.js, npm, or Webpack required. Runs directly via any standard static HTTP server.
- **Enterprise Dark Theme**: Sophisticated fintech aesthetic featuring deep navy/slate palettes, smooth transitions, and high-contrast typography.
- **Pre-configured Quick Profiles**: 1-click test evaluation with Prime, Moderate, and Subprime applicant presets.
- **Real-Time Backend Status**: Dynamically queries the `/health` endpoint to reflect API connectivity.
- **Axiomatic SHAP Attribution**: Localized feature contribution cards detailing top positive risk factors and protective factors.
- **Dynamic Model Benchmarks**: Dynamically fetches historical test-set evaluation metrics from `/model-info`.

---

## 📁 Architecture & File Layout

```
frontend/
│
├── index.html          # Semantic HTML5 single-page application structure
├── css/
│   └── style.css       # Complete Vanilla CSS design system (tokens, cards, responsive grid)
├── js/
│   └── app.js          # Unified modular JavaScript (API client, state, form validation, SHAP UI)
└── README.md           # Documentation and execution instructions
```

---

## 🚀 Running the Full Stack Locally

### Step 1: Start the FastAPI Backend
Open a terminal in the repository root (`Credit-risk-ai/`):

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

*The API will be available at `http://127.0.0.1:8000` with Swagger docs at `http://127.0.0.1:8000/docs`.*

### Step 2: Start the Frontend Static Server
Open a second terminal in the `frontend/` directory and run:

```bash
cd frontend
python -m http.server 5500
```

### Step 3: Open in Browser
Navigate to:
- **[http://127.0.0.1:5500](http://127.0.0.1:5500)**

---

## ⚙️ API Configuration

The frontend communicates with `http://127.0.0.1:8000`. To point to a custom or deployed API URL, edit `API_BASE_URL` in [frontend/js/app.js](file:///D:/Projects/Credit-risk-ai/frontend/js/app.js#L10):

```javascript
const API_BASE_URL = "http://127.0.0.1:8000";
```

---

## 🛡️ Underwriting & Governance Disclaimer

> **IMPORTANT**: FinTrustX is a **demonstration decision-support aid** developed for automated credit risk assessment research. In enterprise lending, all model-generated recommendations must undergo human credit officer review and comply with fair lending statutes (ECOA, FCRA, GDPR, SR 11-7).
