# FinTrustX — Project Architecture & Status Reference

> **Purpose**: This file is the single source of truth for any AI agent or developer
> working on this codebase. It captures the full architecture, current implementation
> status, design patterns, module-level APIs, and performance benchmarks.
> Last updated: 2026-10-05.

---

## Quick Facts

| Key | Value |
|-----|-------|
| **Project Name** | FinTrustX |
| **Full Title** | Explainable AI Platform for Secure Credit Risk Assessment and Loan Decision Intelligence |
| **Domain** | Credit Risk Assessment / Loan Default Prediction |
| **Dataset** | Home Credit Default Risk — `application_train.csv` + `bureau.csv` + `previous_application.csv` |
| **Dataset Size** | 307,511 loan applications (train), 61,503 held-out test |
| **Default Rate** | 8.07% (severe 11:1 class imbalance) |
| **Total Raw Features** | 121 core columns + 98 historical aggregated columns |
| **Total Engineered Features** | 341 (after preprocessing pipeline) |
| **Target Column** | `TARGET` (0 = no default, 1 = default) |
| **Python Version** | >= 3.11 |
| **Primary Metric** | ROC-AUC |
| **Champion Model (API)** | Augmented XGBoost (ROC-AUC: 0.7793, served via FastAPI + SQLite Feature Store) |
| **Best Benchmark Model** | Augmented XGBoost (ROC-AUC: 0.7793) |
| **Random Seed** | 42 (global) |
| **API Framework** | FastAPI + Uvicorn |
| **Frontend** | Vanilla HTML/CSS/JS dashboard |
| **Author** | Anurag Kashyap |
| **GitHub** | `AnuragKashyap-dev/Credit-risk-ai` |

---

## Directory Structure

```
Credit-risk-ai/
├── api/                              # FastAPI REST API (production serving layer)
│   ├── main.py                       # App entrypoint, lifespan, all route definitions
│   ├── config.py                     # API-specific settings (title, CORS, thresholds)
│   ├── schemas.py                    # Pydantic request/response models
│   ├── feature_store.py              # SQLite client for real-time historical feature lookup
│   ├── model_loader.py               # Singleton artifact loader (XGBoost + pipeline)
│   ├── predictor.py                  # XGBoostPredictor: preprocessing + inference
│   ├── explainability.py             # SHAP-based local attribution for API responses
│   ├── preprocessing.py              # API-side feature transformation utilities
│   ├── dependencies.py               # FastAPI dependency injection wiring
│   ├── utils.py                      # API utility helpers
│   ├── requirements.txt              # API-specific dependencies
│   ├── routers/
│   │   ├── health.py                 # Health check router
│   │   └── predict.py                # Prediction router
│   ├── services/
│   │   ├── model_service.py          # Model info & health business logic
│   │   ├── prediction_service.py     # Single & batch prediction orchestration
│   │   └── explanation_service.py    # SHAP explanation business logic
│   └── tests/
│       ├── test_health.py            # Health & metadata endpoint tests
│       ├── test_model_loading.py     # Artifact loading & singleton tests
│       └── test_prediction.py        # Prediction, batch, explanation, validation tests
│
├── data/
│   ├── raw/                          # Raw Kaggle CSV files
│   │   ├── application_train.csv
│   │   ├── bureau.csv
│   │   └── previous_application.csv
│   ├── processed/                    # Processed parquet partitions
│   ├── feature_store.db              # SQLite Feature Store for real-time inference (356k rows)
│   └── processed_train.parquet       # Training features (341 cols)
│
├── scripts/
│   ├── run_data_pipeline.py          # E2E pipeline to aggregate Kaggle datasets
│   └── seed_feature_store.py         # Seeds data/feature_store.db from processed features
│
├── frontend/                         # Static dashboard UI
│   ├── index.html                    # Main HTML page (~22KB)
│   ├── css/style.css                 # Stylesheet (~21KB)
│   ├── js/app.js                     # JavaScript application logic (~17KB)
│   └── README.md                     # Frontend documentation
│
├── models/                           # Serialized model artifacts
│   ├── best_model.joblib             # Champion model (currently Random Forest from early run)
│   ├── xgboost.joblib                # XGBoost — actively served in API (~803KB)
│   ├── catboost.joblib               # CatBoost model (~477KB)
│   ├── decision_tree.joblib          # Decision Tree (~44KB)
│   ├── random_forest.joblib          # Random Forest (~83MB)
│   ├── neural_network.keras          # Deep Neural Network (~556KB)
│   ├── preprocessing_pipeline.joblib # Fitted ColumnTransformer (~19KB)
│   ├── decision_tree.json            # Optuna best params for DT
│   ├── random_forest.json            # Optuna best params for RF
│   └── preprocessed_feature_names.csv # 245 output feature names
│
├── notebooks/                        # Sequential analysis pipeline
│   ├── 01_EDA.ipynb                  # Exploratory Data Analysis & missingness audit
│   ├── 02_Preprocessing.ipynb        # Feature engineering & transformation pipeline
│   ├── 03_ML_Models.ipynb            # ML training, Optuna tuning & baselines
│   ├── 04_DL_Model.ipynb             # Deep learning neural network training
│   ├── 05_Explainable_AI.ipynb       # SHAP, LIME & Counterfactual explanations
│   └── 06_Model_Comparison.ipynb     # Final comparison, ROC/PR & champion selection
│
├── reports/                          # Generated evaluation artifacts
│   ├── model_comparison.csv          # Standardized metric benchmark (4 models)
│   ├── business_metrics.csv          # Credit-risk default capture metrics
│   ├── threshold_analysis.csv        # Multi-threshold sweep (0.1–0.9)
│   ├── model_ranking.csv             # Multi-dimensional ranking table
│   ├── model_metrics.csv             # DT & RF detailed metrics with timing
│   ├── best_model_selection.csv      # Early champion selection record
│   ├── feature_importance.csv        # 246 features ranked by importance
│   └── explainability/               # SHAP, LIME, DiCE report artifacts
│
├── src/                              # Core Python package
│   ├── __init__.py                   # Package marker
│   ├── config.py                     # Central configuration hub
│   ├── data_loader.py                # Data ingestion & profiling
│   ├── preprocessing.py              # Sklearn pipeline builder
│   ├── feature_engineering.py        # Domain feature transformers
│   ├── evaluate.py                   # EvaluationEngine (11 metrics + business KPIs)
│   ├── utils.py                      # Seeding, I/O, logging, timing utilities
│   ├── explainability.py             # Empty stub (logic moved to explainability/)
│   ├── visualization.py              # Empty stub (plots handled in evaluate.py)
│   ├── models/                       # Model wrappers (BaseModel hierarchy)
│   ├── training/                     # ML & DL training orchestrators
│   ├── inference/                    # Prediction pipeline (Predictor + InferenceEngine)
│   ├── explainability/               # XAI framework (SHAP, LIME, DiCE, IG)
│   └── tunning/                      # Optuna tuning engines & visualizers
│
├── studies/                          # Optuna SQLite study databases
│   ├── decision_tree.db
│   ├── random_forest.db
│   └── xgboost.db
│
├── main.py                           # Minimal CLI entry point (placeholder)
├── requirements.txt                  # Production dependencies
├── PROJECT_RULES.md                  # Coding standards & conventions
├── TODO.md                           # Progress checklist
├── .env.example                      # Environment variable template
└── .gitignore                        # Git ignore rules
```

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│  Raw Data: application_train.csv, bureau.csv, prev_application.csv │
│                         data/raw/                                  │
└────────────────────┬───────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────┐
│  DataLoader & DataAggregator (scripts/run_data_pipeline.py)       │
│  • Bureau and Previous Application aggregated per SK_ID_CURR       │
│  • Memory-safe left joins with application_train.csv               │
└────────────────────┬───────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────┐
│  FeatureEngineer (src/feature_engineering.py)                     │
│  • Derived features: ratios, demographics, EXT_SOURCE stats        │
│  • Sklearn-compatible transformer (fit/transform)                  │
└────────────────────┬───────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────┐
│  DataPreprocessor (src/preprocessing.py)                          │
│  • ColumnTransformer: numeric (impute+scale) + categorical (OHE)   │
│  • 219 raw cols → 341 preprocessed features                        │
│  • Saves: models/preprocessing_pipeline.joblib                     │
└────────────────────┬───────────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  ML Models       │  │  Deep Learning   │
│  (train_ml.py)   │  │  (train_dl.py)   │
│  • Decision Tree │  │  • MLP (Keras)   │
│  • Random Forest │  │  • Dropout/BN    │
│  • XGBoost       │  │  • Early Stop    │
│  • CatBoost      │  │  • LR Scheduler  │
│  • Logistic Reg  │  └────────┬─────────┘
└────────┬─────────┘           │
         │      ┌──────────────┘
         ▼      ▼
┌────────────────────────────────────────────────────────────────────┐
│  Optuna Tuning (src/tunning/)                                     │
│  • TreeTuner → DecisionTree, RandomForest                          │
│  • BoostingTuner → XGBoost, CatBoost                               │
│  • NeuralTuner → Keras MLP                                         │
│  • Studies persisted: studies/*.db                                  │
└────────────────────┬───────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────┐
│  EvaluationEngine (src/evaluate.py)                               │
│  • 11 classification metrics + business KPIs                       │
│  • ROC/PR curves, confusion matrix, threshold sweep                │
│  • compare_models() → reports/model_comparison.csv                 │
└────────────────────┬───────────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────┐  ┌──────────────────────────────────────────────┐
│  Explainability  │  │  FastAPI (api/)                              │
│  (src/explain/)  │  │  • GET  /              → API info            │
│  • SHAP (3 var.) │  │  • GET  /health        → Model health check  │
│  • LIME          │  │  • GET  /model-info    → Architecture info   │
│  • DiCE          │  │  • POST /predict       → Single prediction   │
│  • Integ. Grads  │  │  • POST /predict/batch → Batch predictions   │
└──────────────────┘  │  • POST /explain       → SHAP attributions   │
                      │  Serves: xgboost.joblib + pipeline.joblib     │
                      │  Queries: data/feature_store.db via sqlite3  │
                      └──────────────────┬───────────────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────────────┐
                      │  Frontend Dashboard (frontend/)              │
                      │  • Static HTML/CSS/JS                        │
                      │  • Submits SK_ID_CURR + form payload         │
                      └──────────────────────────────────────────────┘
```

---

## Core Module Reference

### `src/config.py` — Central Configuration

The single source of truth for all project constants and paths.

| Constant | Value | Purpose |
|----------|-------|---------|
| `RANDOM_STATE` | `42` | Global reproducibility seed |
| `PROJECT_ROOT` | `Path(__file__).resolve().parent.parent` | Base path resolution |
| `DATA_DIR` | `PROJECT_ROOT / "data"` | Data directory |
| `RAW_DATA_DIR` | `DATA_DIR / "raw"` | Raw CSV location |
| `MODEL_DIR` | `PROJECT_ROOT / "models"` | Model artifact storage |
| `REPORT_DIR` | `PROJECT_ROOT / "reports"` | Report output |
| `STUDY_DIR` | `PROJECT_ROOT / "studies"` | Optuna study DBs |
| `TARGET_COLUMN` | `"TARGET"` | Target column name |
| `N_JOBS` | `-1` | Parallel processing (all cores) |
| `CV_FOLDS` | `5` | Stratified K-Fold splits |
| `SCORING` | `"roc_auc"` | Primary optimization metric |

**Hyperparameter search spaces defined**: `DECISION_TREE_SPACE`, `RANDOM_FOREST_SPACE`, `XGBOOST_SPACE`, `CATBOOST_SPACE`, `NEURAL_NETWORK_SPACE`

**Deep learning config**: `DEEP_LEARNING_TRAINING` dict (2 hidden layers, 64 units, 0.20 dropout, Adam, lr=1e-3, binary_crossentropy, 100 epochs, batch 128)

**Early stopping**: `EARLY_STOPPING` dict (monitor `val_auc`, patience 10, restore best weights)

**Filename registries**: `MODEL_NAMES`, `PARAMETER_FILES`, `STUDY_NAMES`, `EVALUATION_REPORTS`

---

### `src/data_loader.py` — Data Ingestion

**Class: `DataLoader`**
- `load_csv(filename)` → `pd.DataFrame` — Load from `RAW_DATA_DIR`, validates existence
- `optimize_memory(df)` → `pd.DataFrame` — Downcast int/float columns to reduce memory
- `dataset_summary(df)` — Print shape, info, describe
- `missing_summary(df)` → `pd.DataFrame` — Null counts/percentages sorted descending
- `class_distribution(df)` — Print target class balance
- `report(df)` — Full audit pipeline

---

### `src/feature_engineering.py` — Domain Features

**Class: `FeatureEngineer(BaseEstimator, TransformerMixin)`** — Sklearn pipeline compatible

18 engineered features including:
- `AGE_YEARS`, `EMPLOYMENT_YEARS` (from DAYS_* columns)
- `CREDIT_INCOME_RATIO`, `ANNUITY_INCOME_RATIO`, `GOODS_CREDIT_RATIO`
- `INCOME_PER_PERSON`, `CREDIT_PER_PERSON`, `CHILDREN_RATIO`
- `EMPLOYMENT_AGE_RATIO`, `CREDIT_TERM`
- `EXT_SOURCE_MEAN`, `EXT_SOURCE_STD` (row-wise across EXT_SOURCE_1/2/3)
- `PHONE_CHANGE_YEARS`, `REGISTRATION_YEARS`, `ID_PUBLISH_YEARS`
- `LARGE_FAMILY`, `HAS_CAR`, `HAS_HOUSE` (binary flags)

---

### `src/preprocessing.py` — Data Transformation

**Class: `DataPreprocessor`**
- `detect_features(df, target_column)` → `(numeric_list, categorical_list)`
- `build_pipeline()` → `ColumnTransformer`
  - Numeric: `SimpleImputer(median)` → `StandardScaler()`
  - Categorical: `SimpleImputer(most_frequent)` → `OneHotEncoder(handle_unknown="ignore")`
- `fit_transform(X)` / `transform(X)` — Standard sklearn interface
- `save_pipeline()` / `load_pipeline()` — Serialize to `models/preprocessor.joblib`
- `get_feature_names()` → 245 output feature names

---

### `src/evaluate.py` — Evaluation Engine

**Protocol: `BinaryClassifier`** — Runtime-checkable: requires `predict()` and `predict_proba()`

**Class: `EvaluationEngine`**
- Constructor: `model`, `threshold=0.5`, `report_dir`
- `classification_metrics(y_true, y_pred, y_proba)` → 11 metrics:
  - Accuracy, Precision, Recall, F1, ROC AUC, Average Precision, Balanced Accuracy, Matthews Corrcoef, Cohen Kappa, Log Loss, Brier Score Loss
- `business_metrics(y_true, y_pred)` → Credit risk KPIs:
  - True Defaults Captured (TP), False Defaults Flagged (FP), Good Customers Cleared (TN), Defaults Missed (FN), Default Capture Rate, Approval Precision
- `evaluate(features, y_true)` → Combined metrics
- `plot_confusion_matrix()`, `plot_roc_curve()`, `plot_precision_recall_curve()` — Visualization
- `compare_models(results, metric)` → Sorted leaderboard DataFrame
- `save_metrics()` → JSON + CSV persistence

**Convenience functions**: `evaluate_model()`, `plot_roc()`, `plot_precision_recall()`, `plot_confusion_matrix()`, `business_metrics()`, `compare_models()`, `save_results()`

---

### `src/utils.py` — Utility Functions

| Function | Purpose |
|----------|---------|
| `setup_logger()` | Configure `"CreditRisk"` logger |
| `set_seed(42)` | Set seeds: random, numpy, tensorflow, PYTHONHASHSEED |
| `create_directory(path)` | Create directory with parents |
| `save_model(model, filepath)` | Joblib serialization |
| `load_model(filepath)` | Joblib deserialization |
| `save_dl_model(model, filepath)` | Keras model.save() |
| `load_dl_model(filepath)` | tf.keras.models.load_model() |
| `save_figure(fig, filepath)` | Matplotlib save at 300 DPI |
| `timer(func)` | Execution timing decorator |
| `memory_usage(df)` | DataFrame memory in MB |
| `dataset_info(df)` | Shape, missing values, dtype counts |
| `model_size(filepath)` | Model file size in MB |

---

## Model Hierarchy

```
BaseModel (ABC)  ← src/models/base_model.py
│
│  Abstract: build_model()
│  Concrete: fit(), predict(), predict_proba(), save(), load(), get_model()
│  Persistence: joblib.dump / joblib.load
│
├── DecisionTreeModel       ← DecisionTreeClassifier(max_depth=10, class_weight="balanced")
├── RandomForestModel       ← RandomForestClassifier(n_estimators=300, class_weight="balanced")
├── LogisticRegressionModel ← LogisticRegression(max_iter=1000, class_weight="balanced")
├── XGBoostModel            ← XGBClassifier(n_estimators=300, lr=0.05) [optional import]
├── CatBoostModel           ← CatBoostClassifier(iterations=300, lr=0.05) [optional import]
│
└── NeuralNetworkModel      ← src/models/neural_network.py
    • TensorFlow/Keras Functional API
    • Configurable: input_dim, hidden_layers, units, dropout, optimizer, lr
    • predict_proba() returns sklearn-compatible [1-p, p] array
    • save/load enforces .keras extension
    • Lazy input_dim inference from first fit() call
```

**Key pattern**: All ML models auto-build on `__init__()`. XGBoost and CatBoost use safe `try/except ImportError` guards.

---

## Hyperparameter Tuning System

```
BaseTuner  ← src/tunning/base_tuner.py
│
│  • _create_study() → SQLite-backed Optuna study (TPESampler + MedianPruner)
│  • _cross_validation() → StratifiedKFold + cross_val_score
│  • _save_model() / _save_parameters()
│  • summary(), get_best_model/params/score()
│
├── TreeTuner              ← tune_decision_tree(n_trials=20), tune_random_forest(n_trials=40)
│   Uses class_weight="balanced" on refit
│
├── BoostingTuner          ← tune_xgboost(n_trials=50), tune_catboost(n_trials=50)
│   Registry-driven via MODEL_REGISTRY
│   Manual StratifiedKFold with roc_auc_score
│
└── NeuralNetworkTuner     ← optimize(X_train, y_train, X_valid, y_valid, n_trials=30)
    Custom OptunaPruningCallback (Keras on_epoch_end → trial.should_prune())
    Tunes: layers, units, dropout, lr, optimizer, batch_size
```

**`MODEL_REGISTRY`** (`src/tunning/registry.py`): Maps model names to `{model_class, search_space, study_name, model_file, parameter_file}`. Supports DT, RF, XGBoost, CatBoost with conditional imports.

**`OptunaVisualizer`** (`src/tunning/visualization.py`): Generates Plotly HTML reports (optimization history, parameter importance, parallel coordinates, contour, slice, EDF). Supports multi-study leaderboards.

**`TuningUtils`** (`src/tunning/utils.py`): Static helpers for seeding, JSON/Joblib/Keras/Study serialization, timing, best trial display.

**`HyperparameterOptimizer`** (`src/training/hyperparameter.py`): Alternative base with Optuna + matplotlib visualization. Model-specific methods are stubs (`pass`).

---

## Explainability Framework

```
BaseExplainer  ← src/explainability/base_explainer.py
│
│  • predict(X), predict_probability(X) — handles sklearn + Keras
│  • save_figure(filename) — 300 DPI matplotlib
│  • create_subfolder(), model_name(), number_of_features()
│
├── BaseSHAPExplainer → TreeSHAPExplainer    (exact, fast — tree models)
│                     → DeepSHAPExplainer    (DL — with GradientExplainer fallback)
│                     → KernelSHAPExplainer  (model-agnostic — any black box)
│   • SHAPExplainerFactory.create(model) — auto-selects correct variant
│   • Plots: summary, beeswarm, waterfall, force, dependence, feature_importance
│
├── LimeExplainer
│   • Uses lime.lime_tabular.LimeTabularExplainer
│   • Handles both sklearn and Keras prediction interfaces
│   • save_html(), save_png(), explain_multiple()
│
├── CounterfactualExplainer
│   • Greedy coordinate search (no external deps)
│   • Iterates features within ranges until prob < threshold
│   • compare(), visualize_changes(), save_report()
│
├── DiceExplainer
│   • Microsoft DiCE library integration
│   • Auto-detects backend (TF2 vs sklearn)
│   • Constraint support: immutable features + permitted ranges
│   • generate_counterfactuals(), visualize(), save_csv/json(), summary()
│
└── IntegratedGradientsExplainer
    • TensorFlow-only (GradientTape-based)
    • Path integral from baseline (zero vector) to input
    • Riemann sum approximation with configurable steps
    • explain(), visualize(), save_csv/json(), summary()
```

**`ReportGenerator`** (`src/explainability/report_generator.py`): Centralized export service — `save_csv()`, `save_json()`, `save_html()`, `save_summary()`.

---

## Training Pipeline

### `MLTrainer` (`src/training/train_ml.py`)
- Instantiates all 5 ML models in `self.models` dict
- `train_all(X_train, y_train, X_test, y_test)` → loops, trains, evaluates, saves artifacts
- `comparison_table()` → sorted by ROC AUC
- `best_model()` → top performer

### `DeepLearningTrainer` (`src/training/train_dl.py`)
- `load_data()` → reads Parquet files, validates matching columns, converts to float32/int32
- `build_model()` → `NeuralNetworkModel` with config from `DEEP_LEARNING_TRAINING`
- `create_callbacks()` → EarlyStopping + ReduceLROnPlateau + ModelCheckpoint
- `train()` → fit with validation, reload best checkpoint
- `evaluate()` → dual: Keras native + `evaluate_model()`
- `run()` → end-to-end orchestration

---

## Inference Pipeline

### `Predictor` (`src/inference/predictor.py`)
- `__init__(model_path, pipeline_path)` → auto-loads both artifacts
- `load_model()` → dispatches by suffix (`.keras`/`.h5` → Keras, else → Joblib)
- `preprocess(data)` → `pipeline.transform(data)`
- `predict(data)` → `{prediction, probability, model_type}`
- `predict_proba(data)` → positive class probability
- `_classify_risk(probability)` → Very Low / Low / Medium / High / Very High
- `health_check()` → readiness probe
- `explain(data, method)` → stubs for SHAP/LIME/DiCE/IG (NotImplementedError)

### `InferenceEngine` (`src/inference/inference.py`)
- Wraps `Predictor` with input validation and risk classification
- `validate_input(data)` → type + emptiness checks
- `classify_risk(probability)` → 5 risk tiers
- `run(data)` → validate → predict → classify → format_response
- `format_response()` → `{prediction, probability, risk_level}`

---

## FastAPI Application (`api/`)

### Architecture
- **Entry point**: `api/main.py` — FastAPI app with lifespan manager
- **Startup**: Loads `xgboost.joblib` + `preprocessing_pipeline.joblib` → smoke test
- **Dependency Injection**: `api/dependencies.py` wires `ModelLoader`, `XGBoostPredictor`, services
- **Singleton**: `ModelLoader` ensures artifacts loaded once in memory

### API Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|---------------|
| `GET` | `/` | API info & navigation | `Dict[str, Any]` |
| `GET` | `/health` | Model health check (model_loaded, pipeline_loaded) | `HealthResponse` |
| `GET` | `/model-info` | Architecture details & benchmark metrics | `ModelInfoResponse` |
| `POST` | `/predict` | Single applicant scoring (+ optional `?explain=true`) | `PredictionResponse` |
| `POST` | `/predict/batch` | Batch scoring (up to 500 applicants) | `BatchPredictionResponse` |
| `POST` | `/explain` | Standalone SHAP local attribution | `ExplanationResponse` |

### Prediction Response Structure
```json
{
  "prediction": 0,
  "default_probability": 0.23,
  "risk_score": 23.0,
  "risk_category": "Low Risk | Moderate Risk | High Risk | Very High Risk",
  "loan_decision": "Likely Approved | Manual Review | Higher Risk / Manual Review | Likely Rejected",
  "model": "XGBoost",
  "explanation": null | { "top_risk_factors": [...], "protective_factors": [...] }
}
```

### Service Layer
- **`ModelService`**: `get_health()`, `get_model_info()`
- **`PredictionService`**: `predict_single()`, `predict_batch()`
- **`ExplanationService`**: `explain_applicant()` — generates SHAP attribution

### Test Suite (`api/tests/`)
- `test_health.py` — Root, health, model-info endpoints
- `test_model_loading.py` — Artifact existence, singleton pattern, smoke test
- `test_prediction.py` — Single, batch, explain, validation (422 on invalid input)

---

## Frontend Dashboard (`frontend/`)

- **Stack**: Vanilla HTML + CSS + JavaScript (no build tools)
- **Size**: `index.html` (22KB), `style.css` (21KB), `app.js` (17KB)
- **Features**: Credit risk assessment form, prediction display, risk visualization
- **API Integration**: Connects to FastAPI backend via `fetch()`

---

## Notebook Pipeline

| # | Notebook | Purpose | Status |
|---|----------|---------|--------|
| 1 | `01_EDA.ipynb` | Exploratory data analysis, missingness audit, class balance | ✅ Complete |
| 2 | `02_Preprocessing.ipynb` | Feature engineering, transformation pipeline, parquet export | ✅ Complete |
| 3 | `03_ML_Models.ipynb` | ML model training, Optuna tuning, baseline comparison | ✅ Complete |
| 4 | `04_DL_Model.ipynb` | Deep learning MLP training with callbacks | ✅ Complete |
| 5 | `05_Explainable_AI.ipynb` | SHAP global/local, LIME explanations | ✅ Complete |
| 6 | `06_Model_Comparison.ipynb` | Final 5-model benchmark, ROC/PR, champion selection | ✅ Complete |

---

## Model Performance Benchmark

Evaluated on **61,503 held-out test applicants** (341 features, ~4,965 actual defaults):

### Classification Metrics (sorted by ROC AUC)

| Model | ROC AUC | PR-AUC | F1 | Recall | Precision | Balanced Acc | MCC |
|-------|---------|--------|-----|--------|-----------|--------------|------|
| **Augmented XGBoost** (API) | **0.7794** | **0.2751** | — | — | — | — | — |
| **CatBoost** | 0.7716 | 0.2784 | 0.3705 | 0.6410 | 0.2604 | 0.7189 | — |
| **XGBoost** (Baseline) | 0.7712 | 0.2796 | 0.3744 | 0.6466 | 0.2636 | 0.7209 | — |
| **Neural Network** | 0.7610 | 0.2603 | 0.3552 | 0.6418 | 0.2458 | 0.7077 | — |
| **Random Forest** | 0.7382 | 0.2139 | 0.2786 | 0.3186 | 0.2475 | 0.6168 | 0.2085 |
| **Decision Tree** | 0.6282 | 0.1211 | 0.1901 | 0.6828 | 0.1104 | 0.5999 | 0.1088 |

### Business Metrics (threshold = 0.50)

| Model | Defaults Captured | False Flagged | Cleared Good | Missed | Capture Rate |
|-------|-------------------|---------------|--------------|--------|-------------|
| **Decision Tree** | 3,390 | 27,309 | 29,229 | 1,575 | 68.28% |
| **XGBoost** | 3,325 | 16,124 | 40,414 | 1,640 | 66.97% |
| **CatBoost** | 3,183 | 9,047 | 47,491 | 1,783 | 64.10% |
| **Neural Network** | 3,187 | 9,789 | 46,749 | 1,779 | 64.18% |
| **Random Forest** | 1,582 | 4,809 | 51,729 | 3,383 | 31.86% |

### Top 10 Most Important Features

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `EXT_SOURCE_3` | 8.34% |
| 2 | `EXT_SOURCE_2` | 8.14% |
| 3 | `EXT_SOURCE_1` | 3.88% |
| 4 | `DAYS_BIRTH` (age) | 3.73% |
| 5 | `DAYS_EMPLOYED` | 3.35% |
| 6 | `DAYS_ID_PUBLISH` | 3.20% |
| 7 | `AMT_ANNUITY` | 3.02% |
| 8 | `DAYS_LAST_PHONE_CHANGE` | 3.02% |
| 9 | `AMT_CREDIT` | 2.95% |
| 10 | `DAYS_REGISTRATION` | 2.84% |

---

## Current Status & TODO

### ✅ Completed
- [x] EDA & data profiling
- [x] Preprocessing & feature engineering (245 features)
- [x] Supplementary dataset integration (bureau.csv, previous_application.csv → 341 features)
- [x] All 6 model implementations (DT, RF, XGBoost, CatBoost, Logistic, Neural Network)
- [x] Model training & hyperparameter tuning (Optuna)
- [x] Model comparison & champion selection
- [x] Evaluation engine with 11 metrics + business KPIs
- [x] SHAP explainability (Tree, Deep, Kernel + Factory)
- [x] LIME explainability
- [x] FastAPI REST API with 6 endpoints
- [x] API test suite (health, model loading, prediction, batch, explanation, validation)
- [x] SQLite Offline-to-Online Feature Store for real-time historical data lookup
- [x] Frontend dashboard (HTML/CSS/JS) with Applicant ID lookup

### ⚠️ In Progress / Partially Done
- [ ] DiCE counterfactual explanations (code exists but not integrated into pipeline)
- [ ] Integrated Gradients (code exists but not integrated into pipeline)
- [ ] Report Generator (class exists but not wired into workflow)
- [ ] `Predictor.explain()` stubs → need to wire to explainability modules

### ❌ Not Started
- [ ] Root `tests/` directory (empty — tests only in `api/tests/`)
- [ ] `src/training/compare_models.py` (empty placeholder)
- [ ] `src/explainability.py` (empty — logic in `src/explainability/` package)
- [ ] `src/visualization.py` (empty — handled in `evaluate.py`)
- [ ] MLflow integration (referenced in `.env.example` but not implemented)
- [ ] Probability calibration (Platt scaling / isotonic regression)
- [ ] Fairness & demographic parity auditing
- [ ] PSI / feature drift monitoring
- [ ] Docker containerization
- [ ] CI/CD pipeline

---

## Design Patterns & Conventions

### Coding Standards (from `PROJECT_RULES.md`)
- **Python**: >= 3.11, PEP8, Black formatter, 88 char line length
- **Classes**: PascalCase (e.g., `RandomForestModel`, `DiceExplainer`)
- **Functions**: snake_case (e.g., `train_model()`, `predict()`)
- **Constants**: UPPER_CASE (e.g., `RANDOM_STATE = 42`)
- **Type hints**: Required on all public functions
- **Docstrings**: Required on all classes and public methods
- **Error handling**: Never bare `except:` — always specific
- **Logging**: Use `logging` module, not `print()`
- **Models saved**: Always in `models/`, never in `src/`
- **Reproducibility**: Always use `RANDOM_STATE = 42`

### Design Patterns Used
| Pattern | Where |
|---------|-------|
| Abstract Base Class (ABC) | `BaseModel` — enforces `build_model()` contract |
| Template Method | `BaseTuner` — common CV/save, specialized objectives in subclasses |
| Factory | `SHAPExplainerFactory.create()` — auto-selects Tree/Deep/Kernel SHAP |
| Strategy | Tree/Deep/Kernel SHAP — same interface, different algorithms |
| Registry | `MODEL_REGISTRY` — decouples model configs from tuning logic |
| Singleton | `ModelLoader` in API — one-time artifact loading |
| Adapter | `NeuralNetworkModel.predict_proba()` → sklearn-compatible `[1-p, p]` |
| Facade | `InferenceEngine` — hides preprocessing + prediction + risk classification |
| Dependency Injection | FastAPI `Depends()` for Loader, Predictor, Services |
| Layer Supertype | `BaseExplainer` — common prediction/IO for all explainers |
| Graceful Degradation | Optional imports for XGBoost, CatBoost, TensorFlow, dice-ml |

### Inheritance Contracts
- **Every ML model** must inherit `BaseModel` and implement `build_model()`
- **Every explainer** must inherit `BaseExplainer`
- **Every tuner** must inherit `BaseTuner`

---

## Dependencies

### Core (`requirements.txt`)
```
numpy>=1.24.0    pandas>=2.0.0      scipy>=1.10.0      pyarrow>=12.0.0
matplotlib>=3.7.0 seaborn>=0.12.0    missingno>=0.5.2   plotly>=5.14.0
scikit-learn>=1.3.0                  imbalanced-learn>=0.11.0
xgboost>=1.7.0   catboost>=1.2.0    tensorflow>=2.13.0
optuna>=3.3.0    shap>=0.42.0       lime>=0.2.0.1      dice-ml>=0.11
joblib>=1.3.0    tqdm>=4.65.0       python-dotenv>=1.0.0
fastapi>=0.100.0 uvicorn>=0.22.0    pydantic>=2.0.0
```

### API-specific (`api/requirements.txt`)
Subset of above focused on serving: FastAPI, Uvicorn, Pydantic, Joblib, XGBoost, SHAP, Pandas, NumPy.

---

## Key Design Decisions

1. **Parquet over CSV for processed data**: Faster I/O, smaller on disk, preserves dtypes
2. **ColumnTransformer over manual preprocessing**: Ensures consistent train/test transformation
3. **Joblib for ML models, .keras for DL**: Native serialization per framework
4. **Optuna over GridSearch**: Bayesian optimization, pruning, persistent SQLite studies
5. **ROC-AUC as primary metric**: Threshold-independent, robust for imbalanced classes
6. **class_weight="balanced" on tree models**: Compensates for 11:1 class imbalance
7. **XGBoost as API champion over CatBoost**: Marginally lower ROC-AUC (0.7610 vs 0.7716) but better PR-AUC (0.2507 vs 0.2784) and simpler deployment
8. **SHAP Factory pattern**: Auto-selects optimal explainer variant without caller needing to know model type
9. **Separate API package**: `api/` is self-contained with its own config, schemas, services — decoupled from `src/`
10. **Optional dependency guards**: Project doesn't crash if XGBoost, CatBoost, TensorFlow, or dice-ml are missing
