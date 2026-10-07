"""
=========================================================
Pytest Configuration & Shared Fixtures
=========================================================
Provides shared test fixtures including FastAPI TestClient
and self-contained SQLite Feature Store test fixtures.

Author: FinTrustX Test Suite
=========================================================
"""

import sqlite3
import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create reusable FastAPI TestClient with lifespan context."""
    with TestClient(app, headers={"X-API-Key": "dev_api_key_123"}) as test_client:
        yield test_client


@pytest.fixture
def sqlite_feature_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """
    Self-contained SQLite feature store fixture.
    Creates an isolated SQLite database with table 'applicant_features'
    containing known test applicant records, and patches FEATURE_STORE_PATH /
    FastAPI dependency injection overrides so tests remain isolated from
    disk state.
    """
    db_file = tmp_path / "test_feature_store.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applicant_features (
            SK_ID_CURR INTEGER PRIMARY KEY,
            EXT_SOURCE_1 REAL,
            EXT_SOURCE_2 REAL,
            EXT_SOURCE_3 REAL,
            BUREAU_DAYS_CREDIT_MEAN REAL,
            BUREAU_AMT_CREDIT_SUM_MAX REAL,
            PREV_AMT_APPLICATION_MEAN REAL
        )
    """)
    cursor.execute("""
        INSERT OR REPLACE INTO applicant_features 
        (SK_ID_CURR, EXT_SOURCE_1, EXT_SOURCE_2, EXT_SOURCE_3, BUREAU_DAYS_CREDIT_MEAN, BUREAU_AMT_CREDIT_SUM_MAX, PREV_AMT_APPLICATION_MEAN)
        VALUES (100002, 0.0830, 0.2629, 0.1393, -874.0, 450000.0, 179055.0)
    """)
    cursor.execute("""
        INSERT OR REPLACE INTO applicant_features 
        (SK_ID_CURR, EXT_SOURCE_1, EXT_SOURCE_2, EXT_SOURCE_3, BUREAU_DAYS_CREDIT_MEAN, BUREAU_AMT_CREDIT_SUM_MAX, PREV_AMT_APPLICATION_MEAN)
        VALUES (100003, 0.7500, 0.8200, 0.8900, -1400.0, 1293500.0, 435436.5)
    """)
    conn.commit()
    conn.close()

    # Monkeypatch configuration paths across modules if already present
    for mod_name in ["api.config", "api.dependencies", "api.feature_store", "api.services.prediction_service"]:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "FEATURE_STORE_PATH"):
                monkeypatch.setattr(mod, "FEATURE_STORE_PATH", db_file)

    # If FastAPI dependency get_feature_store is defined, override it
    try:
        import api.dependencies as deps
        if hasattr(deps, "get_feature_store"):
            from api.feature_store import FeatureStore
            store = FeatureStore(db_path=db_file)
            app.dependency_overrides[deps.get_feature_store] = lambda: store
            yield db_file
            app.dependency_overrides.pop(deps.get_feature_store, None)
            return
    except Exception:
        pass

    yield db_file
