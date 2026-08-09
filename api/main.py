"""
=========================================================
Credit Risk AI API

Main FastAPI Application

Author : Anurag Kashyap
=========================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    compare,
    explain,
    health,
    predict,
    upload,
)

app = FastAPI(
    title="Credit Risk AI",
    description=(
        "Explainable AI Platform for Credit Risk Assessment "
        "and Loan Decision Intelligence."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------
# Middleware
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Change later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

app.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

app.include_router(
    predict.router,
    prefix="/predict",
    tags=["Prediction"],
)

app.include_router(
    explain.router,
    prefix="/explain",
    tags=["Explainability"],
)

app.include_router(
    compare.router,
    prefix="/compare",
    tags=["Model Comparison"],
)

app.include_router(
    upload.router,
    prefix="/upload",
    tags=["Batch Prediction"],
)

# ---------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Credit Risk AI API",
        "version": "1.0.0",
        "status": "running",
    }

