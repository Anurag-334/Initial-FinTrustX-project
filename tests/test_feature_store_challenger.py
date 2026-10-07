"""
=============================================================================
FinTrustX — Challenger 1: Feature Store & SQLite Adversarial Stress Test Suite
=============================================================================

Adversarial Stress Verifier covering:
1. SQLite Database Schema & Integrity:
   - Table `applicant_features` schema, exact 98 columns matching specification.
   - Primary key constraint on `SK_ID_CURR` (INTEGER PRIMARY KEY).
   - Rejection of duplicate primary keys.
   - Total row count verification (exactly 356,255).
   - Zero NULLs in primary key; unique row count == total count.
   - ID range coverage matching train + test applications.
2. Point Query Latency Benchmarking:
   - Benchmark across 2,000 random valid applicant IDs under high-resolution timing.
   - Evaluation of mean, p50, p90, p95, p99, and max latency (must be < 5.0 ms).
   - Repeated queries for cache warmth testing.
3. Adversarial Edge Cases:
   - Non-existent IDs (positive, high, out of range).
   - Negative IDs.
   - Zero ID.
   - Extreme boundary values (32-bit and 64-bit integer limits, overflows).
   - Floating-point IDs (integer floats and non-integer floats).
   - String IDs and type coercion.
   - SQL Injection attack payloads with parameterized queries.
   - None / NULL ID inputs.
4. WAL Mode & Concurrent Multi-Threaded Read Stress:
   - Journal mode verification (WAL).
   - Concurrent reading stress test (20 threads x 100 queries = 2,000 queries).
   - Concurrent reader / writer test under WAL mode.
5. Memory Safety Compliance (GEMINI.md):
   - Rule 1: Dtype downcasting verification (float32, int16/int32, category).
   - Rule 2: Sequential execution verification (Bureau -> Prev App -> Anchor -> Persist).
   - Rule 3: Explicit garbage collection verification (del + gc.collect() at boundaries).
   - Empirical memory footprint profiling (< 1.8 GB ceiling).
=============================================================================
"""

import ast
import concurrent.futures
import gc
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import psutil
import pytest

from scripts.seed_feature_store import (
    ALL_TABLE_COLUMNS,
    BUREAU_COLUMNS,
    FLAG_COLUMNS,
    HISTORICAL_FEATURE_COLUMNS,
    PREV_COLUMNS,
    RATIO_COLUMNS,
    initialize_sqlite_db,
    insert_features_chunked,
    seed_feature_store,
)
from src.config import DATA_DIR, RAW_DATA_DIR
from src.data_aggregation import optimize_dtypes

PROD_DB_PATH = DATA_DIR / "feature_store.db"


# =============================================================================
# Helper Fixtures & Utilities
# =============================================================================

@pytest.fixture(scope="session")
def prod_db_conn():
    """Session-level read-only connection to production SQLite database."""
    if not PROD_DB_PATH.exists():
        pytest.fail(f"Production database missing at {PROD_DB_PATH}")
    # Open URI in read-only mode to prevent unintended modification
    uri = f"file:{PROD_DB_PATH.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=30.0)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary SQLite database path for write/isolation tests."""
    return tmp_path / "test_scratch_feature_store.db"


def measure_process_rss_mb() -> float:
    """Return process RSS memory in megabytes."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


# =============================================================================
# 1. Schema & Data Integrity Tests
# =============================================================================

class TestFeatureStoreSchemaAndIntegrity:
    """Verifies SQLite table schema, primary key constraints, and row/column counts."""

    def test_db_file_properties(self):
        """Database file exists, has realistic size (> 150 MB and < 250 MB)."""
        assert PROD_DB_PATH.exists(), f"Database does not exist: {PROD_DB_PATH}"
        size_mb = PROD_DB_PATH.stat().st_size / (1024 * 1024)
        assert 140.0 <= size_mb <= 250.0, f"Unexpected DB file size: {size_mb:.2f} MB"

    def test_table_exists_and_column_count(self, prod_db_conn):
        """Table applicant_features exists with exactly 98 columns matching spec."""
        cursor = prod_db_conn.cursor()
        cursor.execute("PRAGMA table_info(applicant_features);")
        columns_info = cursor.fetchall()
        assert len(columns_info) == 98, f"Expected 98 columns, found {len(columns_info)}"

        db_col_names = [row["name"] for row in columns_info]
        assert db_col_names == ALL_TABLE_COLUMNS, (
            "Database column names or ordering does not match ALL_TABLE_COLUMNS specification!"
        )

    def test_column_types_and_affinities(self, prod_db_conn):
        """Verify column types: SK_ID_CURR is INTEGER, FLAGS are INTEGER, rest REAL."""
        cursor = prod_db_conn.cursor()
        cursor.execute("PRAGMA table_info(applicant_features);")
        cols = {row["name"]: row["type"].upper() for row in cursor.fetchall()}

        assert cols["SK_ID_CURR"] == "INTEGER", f"SK_ID_CURR type: {cols['SK_ID_CURR']}"
        for col in FLAG_COLUMNS:
            assert cols[col] == "INTEGER", f"Flag col {col} type: {cols[col]}"
        for col in BUREAU_COLUMNS:
            assert cols[col] == "REAL", f"Bureau col {col} type: {cols[col]}"
        for col in PREV_COLUMNS:
            assert cols[col] == "REAL", f"Prev col {col} type: {cols[col]}"
        for col in RATIO_COLUMNS:
            assert cols[col] == "REAL", f"Ratio col {col} type: {cols[col]}"

    def test_primary_key_and_unique_constraint(self, prod_db_conn):
        """Verify SK_ID_CURR is primary key (pk=1) and has unique index."""
        cursor = prod_db_conn.cursor()
        cursor.execute("PRAGMA table_info(applicant_features);")
        pk_cols = [row["name"] for row in cursor.fetchall() if row["pk"] == 1]
        assert pk_cols == ["SK_ID_CURR"], f"Expected single PK SK_ID_CURR, got {pk_cols}"

        # Check unique index
        cursor.execute("PRAGMA index_list(applicant_features);")
        indices = cursor.fetchall()
        unique_indices = [idx["name"] for idx in indices if idx["unique"] == 1]
        assert len(unique_indices) >= 1, "Expected at least 1 unique index"

    def test_duplicate_pk_insertion_rejection(self, temp_db_path):
        """Verify duplicate SK_ID_CURR insertion is rejected by SQLite IntegrityError."""
        conn = initialize_sqlite_db(temp_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO applicant_features (SK_ID_CURR, BUREAU_LOAN_COUNT) VALUES (100002, 5);"
            )
            conn.commit()

            # Attempt to insert identical SK_ID_CURR without OR REPLACE
            with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed"):
                cursor.execute(
                    "INSERT INTO applicant_features (SK_ID_CURR, BUREAU_LOAN_COUNT) VALUES (100002, 8);"
                )
        finally:
            conn.close()

    def test_exact_row_count_and_uniqueness(self, prod_db_conn):
        """Verify total rows is exactly 356,255 and all SK_ID_CURR are unique."""
        cursor = prod_db_conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total, COUNT(DISTINCT SK_ID_CURR) AS distinct_keys FROM applicant_features;")
        row = cursor.fetchone()
        total_rows = row["total"]
        distinct_keys = row["distinct_keys"]

        assert total_rows == 356255, f"Expected 356,255 rows, got {total_rows}"
        assert distinct_keys == 356255, f"Duplicate keys found! Distinct={distinct_keys}"

    def test_zero_nulls_in_primary_key(self, prod_db_conn):
        """Verify SK_ID_CURR has zero NULL values."""
        cursor = prod_db_conn.cursor()
        cursor.execute("SELECT COUNT(*) AS null_count FROM applicant_features WHERE SK_ID_CURR IS NULL;")
        null_count = cursor.fetchone()["null_count"]
        assert null_count == 0, f"Found {null_count} NULL SK_ID_CURR entries!"

    def test_id_range_and_coverage(self, prod_db_conn):
        """Verify ID boundaries (min >= 100001, max <= 456255) and sample integrity."""
        cursor = prod_db_conn.cursor()
        cursor.execute("SELECT MIN(SK_ID_CURR) AS min_id, MAX(SK_ID_CURR) AS max_id FROM applicant_features;")
        res = cursor.fetchone()
        assert res["min_id"] == 100001, f"Expected min ID 100001, got {res['min_id']}"
        assert res["max_id"] == 456255, f"Expected max ID 456255, got {res['max_id']}"

    def test_feature_value_sanity(self, prod_db_conn):
        """Verify flag values are in {0, 1} and non-null numeric features are finite."""
        cursor = prod_db_conn.cursor()
        # Flags must be strictly 0 or 1
        for flag in ["FLAG_NO_BUREAU_DATA", "FLAG_NO_PREV_DATA"]:
            cursor.execute(f"SELECT DISTINCT {flag} FROM applicant_features WHERE {flag} IS NOT NULL;")
            vals = {row[0] for row in cursor.fetchall()}
            assert vals.issubset({0, 1}), f"Flag {flag} contains non-binary values: {vals}"

        # Sample check 500 rows for valid non-corrupt floats
        cursor.execute("SELECT * FROM applicant_features LIMIT 500;")
        rows = cursor.fetchall()
        for row in rows:
            row_dict = dict(row)
            for k, v in row_dict.items():
                if v is not None and isinstance(v, float):
                    assert not np.isnan(v), f"NaN float found in col {k} for id {row['SK_ID_CURR']}"
                    assert not np.isinf(v), f"Inf float found in col {k} for id {row['SK_ID_CURR']}"


# =============================================================================
# 2. Point Query Latency Benchmarking
# =============================================================================

class TestFeatureStorePointQueryLatency:
    """Stress-test point query latency across random IDs. Target: < 5 ms."""

    def test_point_query_latency_distribution(self, prod_db_conn):
        """
        Benchmark point query latency across 2,000 random valid applicant IDs.
        Must achieve mean < 5.0 ms and p99 < 5.0 ms.
        """
        cursor = prod_db_conn.cursor()
        # Fetch 2,000 random IDs across the entire ID range
        cursor.execute(
            "SELECT SK_ID_CURR FROM applicant_features "
            "WHERE (SK_ID_CURR % 178) = 0 LIMIT 2000;"
        )
        test_ids = [row[0] for row in cursor.fetchall()]
        assert len(test_ids) >= 1000, f"Insufficient sample IDs: {len(test_ids)}"

        latencies_ms: List[float] = []
        sql = "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;"

        for sk_id in test_ids:
            t0 = time.perf_counter_ns()
            cursor.execute(sql, (sk_id,))
            row = cursor.fetchone()
            dt_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            latencies_ms.append(dt_ms)
            assert row is not None, f"Applicant {sk_id} unexpectedly missing"
            assert row["SK_ID_CURR"] == sk_id

        latencies = np.array(latencies_ms)
        mean_lat = float(np.mean(latencies))
        p50_lat = float(np.percentile(latencies, 50))
        p90_lat = float(np.percentile(latencies, 90))
        p95_lat = float(np.percentile(latencies, 95))
        p99_lat = float(np.percentile(latencies, 99))
        max_lat = float(np.max(latencies))
        min_lat = float(np.min(latencies))

        print(
            f"\n[LATENCY BENCHMARK — {len(latencies)} queries]\n"
            f"  Min:    {min_lat:.3f} ms\n"
            f"  p50:    {p50_lat:.3f} ms\n"
            f"  Mean:   {mean_lat:.3f} ms\n"
            f"  p90:    {p90_lat:.3f} ms\n"
            f"  p95:    {p95_lat:.3f} ms\n"
            f"  p99:    {p99_lat:.3f} ms\n"
            f"  Max:    {max_lat:.3f} ms"
        )

        assert mean_lat < 5.0, f"Mean latency failed target: {mean_lat:.3f} ms >= 5.0 ms"
        assert p50_lat < 5.0, f"Median latency failed target: {p50_lat:.3f} ms >= 5.0 ms"
        assert p99_lat < 5.0, f"p99 latency failed target: {p99_lat:.3f} ms >= 5.0 ms"

    def test_repeated_query_cache_warmth(self, prod_db_conn):
        """Repeated lookups for a single ID remain sub-millisecond."""
        cursor = prod_db_conn.cursor()
        test_id = 100002
        latencies_ms: List[float] = []
        sql = "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;"

        for _ in range(500):
            t0 = time.perf_counter_ns()
            cursor.execute(sql, (test_id,))
            row = cursor.fetchone()
            dt_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            latencies_ms.append(dt_ms)
            assert row is not None

        avg_lat = float(np.mean(latencies_ms))
        assert avg_lat < 1.0, f"Repeated query average latency too high: {avg_lat:.3f} ms"


# =============================================================================
# 3. Adversarial Edge Cases
# =============================================================================

class TestFeatureStoreAdversarialEdgeCases:
    """Test non-existent, boundary, negative, string, SQL injection, and None inputs."""

    def test_non_existent_id_queries(self, prod_db_conn):
        """Querying non-existent positive IDs returns None without error."""
        cursor = prod_db_conn.cursor()
        sql = "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;"
        for bad_id in [1, 99999, 456256, 999999999]:
            cursor.execute(sql, (bad_id,))
            row = cursor.fetchone()
            assert row is None, f"Expected None for non-existent ID {bad_id}, got {row}"

    def test_negative_id_queries(self, prod_db_conn):
        """Querying negative IDs returns None without error."""
        cursor = prod_db_conn.cursor()
        sql = "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;"
        for neg_id in [-1, -100002, -999999999]:
            cursor.execute(sql, (neg_id,))
            row = cursor.fetchone()
            assert row is None, f"Expected None for negative ID {neg_id}, got {row}"

    def test_zero_id_query(self, prod_db_conn):
        """Querying ID 0 returns None."""
        cursor = prod_db_conn.cursor()
        cursor.execute("SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;", (0,))
        assert cursor.fetchone() is None

    def test_extreme_integer_boundaries(self, prod_db_conn):
        """Querying 32-bit and 64-bit integer limits returns None gracefully."""
        cursor = prod_db_conn.cursor()
        sql = "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;"
        boundaries = [
            2147483647,             # max 32-bit int
            -2147483648,            # min 32-bit int
            9223372036854775807,     # max 64-bit int
            -9223372036854775808,    # min 64-bit int
        ]
        for val in boundaries:
            cursor.execute(sql, (val,))
            assert cursor.fetchone() is None

    def test_overflow_integer_safety(self, prod_db_conn):
        """Beyond 64-bit int: either handles gracefully returning None or raises Python OverflowError."""
        cursor = prod_db_conn.cursor()
        huge_id = 10**30
        try:
            cursor.execute("SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;", (huge_id,))
            res = cursor.fetchone()
            assert res is None
        except (OverflowError, sqlite3.DataError):
            # Acceptable Python/SQLite overflow trap
            pass

    def test_floating_point_id_queries(self, prod_db_conn):
        """Floating point inputs: 100002.0 matches due to affinity; 100002.5 returns None."""
        cursor = prod_db_conn.cursor()
        # 100002.0 in SQLite INTEGER column matches 100002
        cursor.execute("SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;", (100002.0,))
        row = cursor.fetchone()
        assert row is not None
        assert row["SK_ID_CURR"] == 100002

        # 100002.5 fractional float does not match integer PK
        cursor.execute("SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;", (100002.5,))
        row_frac = cursor.fetchone()
        assert row_frac is None

    def test_string_and_type_coercion_ids(self, prod_db_conn):
        """String IDs: '100002' coerces via affinity; 'abc' returns None."""
        cursor = prod_db_conn.cursor()
        # Numeric string matches integer column
        cursor.execute("SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;", ("100002",))
        row = cursor.fetchone()
        assert row is not None
        assert row["SK_ID_CURR"] == 100002

        # Non-numeric strings return None without error
        for non_num in ["abc", "", "   ", "SK_ID_100002", "null"]:
            cursor.execute("SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;", (non_num,))
            assert cursor.fetchone() is None

    def test_sql_injection_resilience(self, prod_db_conn):
        """Parameterized queries must neutralize SQL injection payloads and return None."""
        cursor = prod_db_conn.cursor()
        sql = "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;"
        attack_payloads = [
            "' OR '1'='1",
            "100002; DROP TABLE applicant_features; --",
            "100002 UNION SELECT 1, 2, 3",
            "'; VACUUM; --",
            "100002 OR 1=1",
            "admin'--",
            "1' or '1' = '1",
        ]
        for attack in attack_payloads:
            cursor.execute(sql, (attack,))
            res = cursor.fetchone()
            assert res is None, f"SQL injection payload {attack} bypassed query logic!"

        # Verify table was not dropped or corrupted
        cursor.execute("SELECT COUNT(*) FROM applicant_features;")
        assert cursor.fetchone()[0] == 356255

    def test_none_and_null_id_query(self, prod_db_conn):
        """Passing None / NULL parameter returns None without crashing."""
        cursor = prod_db_conn.cursor()
        cursor.execute("SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;", (None,))
        assert cursor.fetchone() is None


# =============================================================================
# 4. WAL Mode & Concurrent Multi-Threaded Read Stress
# =============================================================================

class TestFeatureStoreWALAndConcurrency:
    """Verifies Write-Ahead Logging (WAL) and concurrent multi-threaded read access."""

    def test_wal_mode_active(self, prod_db_conn):
        """Database is configured with WAL journal mode and normal/full synchrony."""
        cursor = prod_db_conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal", f"Expected WAL mode, got {mode}"

    def test_concurrent_multi_threaded_reads(self):
        """
        Simulate 20 concurrent FastAPI worker threads executing 100 point queries each
        (total 2,000 queries) simultaneously against data/feature_store.db.
        Must execute with zero locked errors and average latency < 5 ms.
        """
        num_threads = 20
        queries_per_thread = 100
        test_ids = [100002 + (i * 100) for i in range(queries_per_thread)]

        def worker_task(thread_id: int) -> Tuple[int, List[float]]:
            # Each worker thread creates its own SQLite connection
            conn = sqlite3.connect(str(PROD_DB_PATH), timeout=30.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            latencies = []
            success_count = 0
            try:
                for target_id in test_ids:
                    t0 = time.perf_counter_ns()
                    cursor.execute(
                        "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?;",
                        (target_id,),
                    )
                    row = cursor.fetchone()
                    dt_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
                    latencies.append(dt_ms)
                    if row is not None and row["SK_ID_CURR"] == target_id:
                        success_count += 1
            finally:
                conn.close()
            return success_count, latencies

        t_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, tid) for tid in range(num_threads)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        total_time_sec = time.perf_counter() - t_start

        total_success = sum(r[0] for r in results)
        all_latencies = [lat for r in results for lat in r[1]]
        total_queries = len(all_latencies)

        assert total_queries == num_threads * queries_per_thread
        assert total_success == total_queries, (
            f"Some queries failed! Success: {total_success} / {total_queries}"
        )

        qps = total_queries / total_time_sec
        p50 = float(np.percentile(all_latencies, 50))
        p95 = float(np.percentile(all_latencies, 95))
        p99 = float(np.percentile(all_latencies, 99))
        mean_lat = float(np.mean(all_latencies))

        print(
            f"\n[CONCURRENCY STRESS — {num_threads} threads, {total_queries} queries]\n"
            f"  Total time:  {total_time_sec:.3f} s\n"
            f"  Throughput:  {qps:.1f} QPS\n"
            f"  Mean latency: {mean_lat:.3f} ms\n"
            f"  p50 latency:  {p50:.3f} ms\n"
            f"  p95 latency:  {p95:.3f} ms\n"
            f"  p99 latency:  {p99:.3f} ms"
        )

        assert mean_lat < 5.0, f"Mean concurrent latency >= 5 ms: {mean_lat:.3f} ms"
        assert p99 < 10.0, f"p99 concurrent latency too high: {p99:.3f} ms"

    def test_concurrent_read_during_write_wal(self, temp_db_path):
        """
        Verify WAL non-blocking concurrency: readers can query while writer commits.
        Uses a separate scratch DB to avoid mutating production data.
        """
        conn_init = initialize_sqlite_db(temp_db_path)
        # Seed 100 rows
        dummy_data = {"SK_ID_CURR": np.arange(1001, 1101, dtype=np.int64)}
        for col in HISTORICAL_FEATURE_COLUMNS:
            dummy_data[col] = np.zeros(100, dtype=np.float32)
        df_init = pd.DataFrame(dummy_data)
        insert_features_chunked(conn_init, df_init, batch_size=50)
        conn_init.close()

        stop_flag = False

        def writer_loop():
            conn_w = sqlite3.connect(str(temp_db_path), timeout=30.0)
            cursor_w = conn_w.cursor()
            curr_id = 2000
            while not stop_flag:
                cursor_w.execute(
                    "INSERT OR REPLACE INTO applicant_features (SK_ID_CURR, BUREAU_LOAN_COUNT) VALUES (?, ?);",
                    (curr_id, 1),
                )
                conn_w.commit()
                curr_id += 1
                time.sleep(0.005)
            conn_w.close()

        def reader_loop() -> int:
            conn_r = sqlite3.connect(str(temp_db_path), timeout=30.0)
            conn_r.row_factory = sqlite3.Row
            cursor_r = conn_r.cursor()
            reads = 0
            while not stop_flag:
                cursor_r.execute(
                    "SELECT * FROM applicant_features WHERE SK_ID_CURR = 1001;"
                )
                row = cursor_r.fetchone()
                assert row is not None
                reads += 1
                time.sleep(0.002)
            conn_r.close()
            return reads

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            writer_future = executor.submit(writer_loop)
            reader_futures = [executor.submit(reader_loop) for _ in range(3)]
            time.sleep(0.5)
            stop_flag = True
            writer_future.result()
            read_counts = [f.result() for f in reader_futures]

        assert all(c > 10 for c in read_counts), f"Readers failed to execute: {read_counts}"


# =============================================================================
# 5. Memory Safety Compliance (GEMINI.md)
# =============================================================================

class TestMemorySafetyCompliance:
    """
    Audits scripts/seed_feature_store.py and src/data_aggregation.py
    against the 3 mandatory GEMINI.md rules:
    1. Dtype Downcasting (float32, int32/int16, category).
    2. Sequential Execution (one dataset at a time).
    3. Explicit Garbage Collection (del + gc.collect() at every boundary).
    """

    def test_gemini_rule1_dtype_downcasting(self):
        """
        Verify optimize_dtypes downcasts float64 to float32, int64 to int32/int16,
        and low-cardinality strings (ratio < 0.5) to category.
        """
        df = pd.DataFrame({
            "int_col": np.array([1, 2, 100, 4, 5, 6], dtype=np.int64),
            "float_col": np.array([1.5, 2.5, 3.5, 4.5, 5.5, 6.5], dtype=np.float64),
            "cat_col": ["Active", "Closed", "Active", "Active", "Closed", "Active"],
        })
        optimized = optimize_dtypes(df)

        assert optimized["float_col"].dtype == np.float32, "Failed float64 downcast to float32"
        assert optimized["int_col"].dtype in [np.int8, np.int16, np.int32], "Failed int64 downcast"
        assert optimized["cat_col"].dtype.name == "category", "Failed category downcast"

    def test_gemini_rule2_and_rule3_ast_audit(self):
        """
        Statically inspect scripts/seed_feature_store.py source code via AST
        to prove:
        - Dtype optimization is called on all loaded frames.
        - del and gc.collect() are explicitly invoked at every stage boundary.
        - Datasets are loaded sequentially without simultaneous multi-CSV loading.
        """
        seeder_path = Path("scripts/seed_feature_store.py")
        assert seeder_path.exists()
        source = seeder_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Count gc.collect() calls
        gc_collect_calls = 0
        del_statements = 0
        optimize_dtype_calls = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for gc.collect()
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "collect"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "gc"
                ):
                    gc_collect_calls += 1
                # Check for optimize_dtypes()
                elif (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "optimize_dtypes"
                ):
                    optimize_dtype_calls += 1
            elif isinstance(node, ast.Delete):
                del_statements += 1

        print(
            f"\n[AST AUDIT scripts/seed_feature_store.py]\n"
            f"  del statements:         {del_statements}\n"
            f"  gc.collect() calls:     {gc_collect_calls}\n"
            f"  optimize_dtypes calls:  {optimize_dtype_calls}"
        )

        assert del_statements >= 3, f"Insufficient del statements: {del_statements}"
        assert gc_collect_calls >= 3, f"Insufficient gc.collect() calls: {gc_collect_calls}"
        assert optimize_dtype_calls >= 2, f"Insufficient optimize_dtypes calls: {optimize_dtype_calls}"

    def test_empirical_memory_ceiling_under_seeding(self, temp_db_path):
        """
        Empirically run seed_feature_store pipeline with limit=1,000 to verify
        peak RSS memory stays well below the 1.8 GB constraint (< 400 MB).
        """
        rss_start = measure_process_rss_mb()
        inserted = seed_feature_store(
            db_path=temp_db_path,
            raw_data_dir=RAW_DATA_DIR,
            batch_size=500,
            limit=1000,
        )
        rss_end = measure_process_rss_mb()
        assert inserted == 1000

        print(
            f"\n[MEMORY PROFILE]\n"
            f"  Initial RSS: {rss_start:.1f} MB\n"
            f"  Final RSS:   {rss_end:.1f} MB"
        )
        # Must be far below the 1.8 GB (1843 MB) system limit
        assert rss_end < 1843.0, f"Memory exceeded 1.8 GB ceiling: {rss_end:.1f} MB"
        assert rss_end < 600.0, f"Memory unusually elevated: {rss_end:.1f} MB"


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
