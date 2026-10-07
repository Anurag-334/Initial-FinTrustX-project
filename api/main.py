"""
=========================================================
FinTrustX FastAPI Application Entrypoint
=========================================================
Production REST API for Credit Risk Assessment, Default
Prediction, Decision Intelligence, and Explainable AI.

Author: Anurag Kashyap
=========================================================
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Depends, Query, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from api.config import (
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    CORS_ORIGINS,
    DEFAULT_CLASSIFICATION_THRESHOLD,
)
from api.schemas import (
    CreditRiskRequest,
    BatchCreditRiskRequest,
    PredictionResponse,
    BatchPredictionResponse,
    ExplanationResponse,
    ModelInfoResponse,
    HealthResponse,
)
from api.dependencies import (
    get_loader,
    get_predictor,
    get_model_service,
    get_prediction_service,
    get_explanation_service,
    verify_api_key,
)
from api.model_loader import ModelLoader
from api.predictor import XGBoostPredictor
from api.services.model_service import ModelService
from api.services.prediction_service import PredictionService
from api.services.explanation_service import ExplanationService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fintrustx_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Loads XGBoost model and preprocessor artifacts once on startup.
    """
    logger.info("=" * 60)
    logger.info("Starting FinTrustX Credit Risk API Service...")
    logger.info("=" * 60)
    
    loader = get_loader()
    try:
        loader.load_artifacts()
        smoke_ok = loader.run_smoke_test()
        if smoke_ok:
            logger.info("✅ Startup smoke test passed successfully.")
        else:
            logger.warning("⚠️ Startup smoke test returned unexpected result.")
    except Exception as e:
        logger.error(f"❌ Critical error during artifact initialization: {e}")
        
    yield
    
    logger.info("FinTrustX API Service shutting down.")


# Initialize FastAPI Application
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_REQUEST_BODY_SIZE = 5 * 1024 * 1024  # 5 MB

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    if "content-length" in request.headers:
        if int(request.headers["content-length"]) > MAX_REQUEST_BODY_SIZE:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large"}
            )
    return await call_next(request)


# =========================================================
# Exception Handlers
# =========================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic schema validation failures with clean 422 errors."""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Invalid input data schema or values.",
            "details": exc.errors(),
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle bad input data with 400 Bad Request."""
    logger.error(f"ValueError on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Bad Request", "message": str(exc)}
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle missing artifact files with 404 Not Found."""
    logger.error(f"FileNotFoundError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "Artifact Not Found", "message": str(exc)}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Safely catch unhandled internal exceptions without leaking raw tracebacks."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An internal prediction error occurred. Please check server logs."
        }
    )


# =========================================================
# API Endpoints
# =========================================================

@app.get(
    "/",
    tags=["General"],
    summary="API Root Information",
    response_model=Dict[str, Any]
)
async def root():
    """Returns general service information and navigation links."""
    return {
        "service": API_TITLE,
        "version": API_VERSION,
        "status": "online",
        "documentation": "/docs",
        "health_check": "/health",
        "model_info": "/model-info",
        "description": "FinTrustX Explainable AI platform for credit risk assessment."
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="System and Model Health Status",
    response_model=HealthResponse
)
async def health(
    loader: ModelLoader = Depends(get_loader),
    service: ModelService = Depends(get_model_service)
):
    """
    Check if the API and underlying XGBoost model and preprocessors are operational.
    """
    health_status = service.get_health(loader)
    if health_status.status != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model artifacts are not loaded into memory."
        )
    return health_status


@app.get(
    "/model-info",
    tags=["Model"],
    summary="Deployed Model Characteristics & Metrics",
    response_model=ModelInfoResponse,
    dependencies=[Depends(verify_api_key)]
)
async def model_info(
    loader: ModelLoader = Depends(get_loader),
    service: ModelService = Depends(get_model_service)
):
    """
    Retrieve architecture details and static benchmark performance metrics of the deployed model.
    """
    try:
        return service.get_model_info(loader)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@app.post(
    "/predict",
    tags=["Prediction"],
    summary="Single Applicant Credit Risk Evaluation",
    response_model=PredictionResponse,
    dependencies=[Depends(verify_api_key)]
)
async def predict_credit_risk(
    request: CreditRiskRequest,
    explain: bool = Query(default=False, description="Whether to include SHAP feature attribution in response"),
    threshold: float = Query(
        default=DEFAULT_CLASSIFICATION_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Decision cut-off threshold (default 0.50)"
    ),
    predictor: XGBoostPredictor = Depends(get_predictor),
    service: PredictionService = Depends(get_prediction_service)
):
    """
    Score a single loan applicant and generate default probability, risk tier,
    loan underwriting recommendation, and optional localized SHAP reason codes.
    """
    try:
        return service.predict_single(
            request=request,
            predictor=predictor,
            threshold=threshold,
            explain=explain
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}"
        )


@app.post(
    "/explain",
    tags=["Explainability"],
    summary="Localized SHAP Feature Attribution",
    response_model=ExplanationResponse,
    dependencies=[Depends(verify_api_key)]
)
async def explain_prediction(
    request: CreditRiskRequest,
    predictor: XGBoostPredictor = Depends(get_predictor),
    service: ExplanationService = Depends(get_explanation_service)
):
    """
    Generate localized SHAP attribution factors for an applicant, detailing
    top risk-increasing drivers and protective risk-reducing factors.
    """
    try:
        return service.explain_applicant(request=request, predictor=predictor)
    except Exception as e:
        logger.error(f"Explanation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explainability error: {str(e)}"
        )


@app.post(
    "/predict/batch",
    tags=["Prediction"],
    summary="Batch Applicant Credit Risk Evaluation",
    response_model=BatchPredictionResponse,
    dependencies=[Depends(verify_api_key)]
)
async def predict_batch(
    batch_request: BatchCreditRiskRequest,
    threshold: float = Query(
        default=DEFAULT_CLASSIFICATION_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Decision cut-off threshold (default 0.50)"
    ),
    predictor: XGBoostPredictor = Depends(get_predictor),
    service: PredictionService = Depends(get_prediction_service)
):
    """
    Perform high-throughput vectorized prediction for a batch of loan applicants (up to 500 records).
    """
    try:
        return service.predict_batch(
            batch_request=batch_request,
            predictor=predictor,
            threshold=threshold
        )
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch inference error: {str(e)}"
        )
