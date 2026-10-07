"""
===========================================================
Unit & Integration Tests: SQLite Feature Store
===========================================================

Verifies:
1. Database initialization and WAL mode.
2. applicant_features table schema (98 columns, SK_ID_CURR primary key).
3. Correct feature types and non-null key constraints.
4. Point query retrieval latency (< 5 ms).
5. Seeding logic with limited sample and full database verification.
===========================================================
"""

import sqlite3
import tempfile
import time
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

from scripts.seed_feature_store import (
    ALL_TABLE_COLUMNS,
    HISTORICAL_FEATURE_COLUMNS,
    initialize_sqlite_db,
    insert_features_chunked,
    seed_feature_store,
    verify_database,
)
from src.config import DATA_DIR, RAW_DATA_DIR


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database file path."""
    return tmp_path / "test_feature_store.db"


def test_table_schema_and_primary_key(temp_db_path):
    """Verify that initialize_sqlite_db creates the exact expected schema with PK."""
    conn = initialize_sqlite_db(temp_db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(applicant_features);")
        columns = cursor.fetchall()
        col_dict = {col[1]: {"type": col[2], "pk": col[5]} for col in columns}

        assert len(col_dict) == 98, f"Expected 98 columns, found {len(col_dict)}"
        assert "SK_ID_CURR" in col_dict
        assert col_dict["SK_ID_CURR"]["pk"] == 1
        assert "INTEGER" in col_dict["SK_ID_CURR"]["type"].upper()

        for col in HISTORICAL_FEATURE_COLUMNS:
            assert col in col_dict, f"Missing historical column: {col}"

        # Verify WAL mode
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.upper() == "WAL"
    finally:
        conn.close()


def test_chunked_insert_and_point_query_latency(temp_db_path):
    """Verify that insert_features_chunked correctly populates rows and query is < 5ms."""
    conn = initialize_sqlite_db(temp_db_path)
    try:
        # Create dummy DataFrame with 100 rows matching schema
        n_rows = 100
        data = {"SK_ID_CURR": np.arange(100001, 100001 + n_rows, dtype=np.int64)}
        for col in HISTORICAL_FEATURE_COLUMNS:
            if "FLAG" in col or "COUNT" in col:
                data[col] = np.random.randint(0, 5, size=n_rows)
            else:
                data[col] = np.random.randn(n_rows).astype(np.float32)

        df = pd.DataFrame(data)
        inserted = insert_features_chunked(conn, df, batch_size=25)
        assert inserted == n_rows

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM applicant_features;")
        count = cursor.fetchone()[0]
        assert count == n_rows

        # Measure point query latency
        latencies = []
        for sid in [100001, 100050, 100100]:
            t0 = time.perf_counter()
            cursor.execute(
                "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?", (sid,)
            )
            row = cursor.fetchone()
            dt_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(dt_ms)
            assert row is not None
            assert row[0] == sid

        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 5.0, f"Query latency too high: {avg_latency:.3f} ms"
    finally:
        conn.close()


def test_seed_feature_store_with_limit(temp_db_path):
    """Verify end-to-end seed_feature_store execution with a small row limit."""
    limit = 10
    inserted = seed_feature_store(
        db_path=temp_db_path,
        raw_data_dir=RAW_DATA_DIR,
        batch_size=5,
        limit=limit,
    )
    assert inserted == limit

    # Run verification logic
    verify_database(temp_db_path)

    # Inspect contents
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applicant_features LIMIT 1;")
        row = dict(cursor.fetchone())
        assert "SK_ID_CURR" in row
        assert "BUREAU_SK_ID_BUREAU_COUNT" in row
        assert "PREV_SK_ID_PREV_COUNT" in row
        assert "FLAG_NO_BUREAU_DATA" in row
        assert "TOTAL_DEBT_TO_INCOME" in row
    finally:
        conn.close()


def test_production_feature_store_if_exists():
    """If production database exists at data/feature_store.db, verify its integrity."""
    prod_db = DATA_DIR / "feature_store.db"
    if not prod_db.exists():
        pytest.skip("Production database data/feature_store.db not seeded yet.")

    verify_database(prod_db)
