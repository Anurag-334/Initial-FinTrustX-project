"""
===========================================================
FinTrustX — Feature Store Seeder
===========================================================

Offline-to-online SQLite Feature Store seeder.
Aggregates historical credit records from bureau.csv and
previous_application.csv, computes baseline cross-table
macroeconomic ratios, and persists pre-aggregated features
into SQLite table `applicant_features` indexed by `SK_ID_CURR`.

Strict Memory Management Compliance (GEMINI.md):
- Dtype downcasting on all loaded and intermediate DataFrames.
- Sequential execution: Bureau -> Previous App -> Merge -> Persist.
- Explicit garbage collection (del + gc.collect()) at every boundary.
- Chunked SQLite transactions (10k-25k rows/chunk) with WAL mode.
===========================================================
"""

import argparse
import gc
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DATA_DIR, RAW_DATA_DIR
from src.data_aggregation import DataAggregator, optimize_dtypes

# Setup module logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("seed_feature_store")

# Define the exact 97 historical and cross-table feature columns
BUREAU_COLUMNS: List[str] = [
    "BUREAU_SK_ID_BUREAU_COUNT",
    "BUREAU_IS_ACTIVE_SUM",
    "BUREAU_IS_ACTIVE_MEAN",
    "BUREAU_IS_CLOSED_SUM",
    "BUREAU_IS_CLOSED_MEAN",
    "BUREAU_IS_MICROLOAN_SUM",
    "BUREAU_IS_MICROLOAN_MEAN",
    "BUREAU_DAYS_CREDIT_MIN",
    "BUREAU_DAYS_CREDIT_MAX",
    "BUREAU_DAYS_CREDIT_MEAN",
    "BUREAU_CREDIT_DAY_OVERDUE_MAX",
    "BUREAU_CREDIT_DAY_OVERDUE_MEAN",
    "BUREAU_DAYS_CREDIT_ENDDATE_MIN",
    "BUREAU_DAYS_CREDIT_ENDDATE_MAX",
    "BUREAU_DAYS_CREDIT_ENDDATE_MEAN",
    "BUREAU_AMT_CREDIT_MAX_OVERDUE_MAX",
    "BUREAU_AMT_CREDIT_MAX_OVERDUE_MEAN",
    "BUREAU_CNT_CREDIT_PROLONG_SUM",
    "BUREAU_CNT_CREDIT_PROLONG_MAX",
    "BUREAU_AMT_CREDIT_SUM_SUM",
    "BUREAU_AMT_CREDIT_SUM_MEAN",
    "BUREAU_AMT_CREDIT_SUM_MAX",
    "BUREAU_AMT_CREDIT_SUM_DEBT_SUM",
    "BUREAU_AMT_CREDIT_SUM_DEBT_MEAN",
    "BUREAU_AMT_CREDIT_SUM_DEBT_MAX",
    "BUREAU_AMT_CREDIT_SUM_LIMIT_SUM",
    "BUREAU_AMT_CREDIT_SUM_LIMIT_MEAN",
    "BUREAU_AMT_CREDIT_SUM_OVERDUE_SUM",
    "BUREAU_AMT_CREDIT_SUM_OVERDUE_MAX",
    "BUREAU_DAYS_CREDIT_UPDATE_MAX",
    "BUREAU_DAYS_CREDIT_UPDATE_MEAN",
    "BUREAU_AMT_ANNUITY_SUM",
    "BUREAU_AMT_ANNUITY_MEAN",
    "BUREAU_AMT_ANNUITY_MAX",
    "BUREAU_ACTIVE_AMT_CREDIT_SUM_DEBT_SUM",
    "BUREAU_ACTIVE_AMT_CREDIT_SUM_DEBT_MEAN",
    "BUREAU_ACTIVE_AMT_CREDIT_SUM_SUM",
    "BUREAU_ACTIVE_AMT_CREDIT_SUM_MEAN",
    "BUREAU_ACTIVE_DAYS_CREDIT_MAX",
    "BUREAU_DEBT_CREDIT_RATIO",
    "BUREAU_ACTIVE_DEBT_RATIO",
    "BUREAU_OVERDUE_DEBT_RATIO",
    "BUREAU_ACTIVE_LOAN_SHARE",
    "BUREAU_PROLONG_RATE",
]

PREV_COLUMNS: List[str] = [
    "PREV_SK_ID_PREV_COUNT",
    "PREV_IS_APPROVED_SUM",
    "PREV_IS_APPROVED_MEAN",
    "PREV_IS_REFUSED_SUM",
    "PREV_IS_REFUSED_MEAN",
    "PREV_IS_CANCELED_SUM",
    "PREV_IS_CANCELED_MEAN",
    "PREV_AMT_ANNUITY_MIN",
    "PREV_AMT_ANNUITY_MAX",
    "PREV_AMT_ANNUITY_MEAN",
    "PREV_AMT_ANNUITY_SUM",
    "PREV_AMT_APPLICATION_MIN",
    "PREV_AMT_APPLICATION_MAX",
    "PREV_AMT_APPLICATION_MEAN",
    "PREV_AMT_APPLICATION_SUM",
    "PREV_AMT_CREDIT_MIN",
    "PREV_AMT_CREDIT_MAX",
    "PREV_AMT_CREDIT_MEAN",
    "PREV_AMT_CREDIT_SUM",
    "PREV_AMT_DOWN_PAYMENT_MAX",
    "PREV_AMT_DOWN_PAYMENT_MEAN",
    "PREV_AMT_DOWN_PAYMENT_SUM",
    "PREV_RATE_DOWN_PAYMENT_MAX",
    "PREV_RATE_DOWN_PAYMENT_MEAN",
    "PREV_DAYS_DECISION_MIN",
    "PREV_DAYS_DECISION_MAX",
    "PREV_DAYS_DECISION_MEAN",
    "PREV_CNT_PAYMENT_MAX",
    "PREV_CNT_PAYMENT_MEAN",
    "PREV_CNT_PAYMENT_SUM",
    "PREV_DAYS_TERMINATION_MAX",
    "PREV_DAYS_TERMINATION_MEAN",
    "PREV_APP_CREDIT_RATIO_MEAN",
    "PREV_APP_CREDIT_RATIO_MAX",
    "PREV_APPROVED_AMT_CREDIT_SUM",
    "PREV_APPROVED_AMT_CREDIT_MEAN",
    "PREV_REFUSED_AMT_APPLICATION_SUM",
    "PREV_REFUSED_AMT_APPLICATION_MEAN",
    "PREV_REFUSED_DAYS_DECISION_MAX",
    "PREV_APPROVED_DAYS_DECISION_MAX",
    "PREV_APPROVAL_RATE",
    "PREV_REFUSAL_RATE",
    "PREV_CREDIT_TO_APPLICATION_RATIO",
    "PREV_DOWN_PAYMENT_RATIO",
]

FLAG_COLUMNS: List[str] = [
    "FLAG_NO_BUREAU_DATA",
    "FLAG_NO_PREV_DATA",
    "BUREAU_LOAN_COUNT",
    "PREV_APP_COUNT",
]

RATIO_COLUMNS: List[str] = [
    "BUREAU_TOTAL_DEBT_TO_INCOME",
    "BUREAU_ANNUITY_TO_INCOME",
    "PREV_ANNUITY_TO_INCOME",
    "PREV_CURRENT_TO_PRIOR_CREDIT_RATIO",
    "TOTAL_DEBT_TO_INCOME",
]

HISTORICAL_FEATURE_COLUMNS: List[str] = (
    BUREAU_COLUMNS + PREV_COLUMNS + FLAG_COLUMNS + RATIO_COLUMNS
)
ALL_TABLE_COLUMNS: List[str] = ["SK_ID_CURR"] + HISTORICAL_FEATURE_COLUMNS


def get_current_ram_mb() -> float:
    """Get current resident set size (RSS) memory in MB."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def initialize_sqlite_db(db_path: Path, table_name: str = "applicant_features") -> sqlite3.Connection:
    """
    Initialize SQLite database with WAL mode and target table schema.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=60.0)

    # Enable WAL mode and performance pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY;")

    # Build DDL column definitions
    col_defs: List[str] = ["SK_ID_CURR INTEGER PRIMARY KEY"]
    for col in BUREAU_COLUMNS:
        col_defs.append(f"{col} REAL")
    for col in PREV_COLUMNS:
        col_defs.append(f"{col} REAL")
    for col in FLAG_COLUMNS:
        col_defs.append(f"{col} INTEGER")
    for col in RATIO_COLUMNS:
        col_defs.append(f"{col} REAL")

    ddl = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {', '.join(col_defs)}
    );
    """
    conn.execute(f"DROP TABLE IF EXISTS {table_name};")
    conn.execute(ddl)
    conn.commit()
    return conn


def insert_features_chunked(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    batch_size: int = 25000,
    table_name: str = "applicant_features",
) -> int:
    """
    Stream DataFrame rows into SQLite in chunked transactions.
    """
    cols = ALL_TABLE_COLUMNS
    placeholders = ", ".join(["?"] * len(cols))
    sql = (
        f"INSERT OR REPLACE INTO {table_name} ({', '.join(cols)}) "
        f"VALUES ({placeholders})"
    )

    total_rows = len(df)
    cursor = conn.cursor()
    inserted = 0

    for start_idx in range(0, total_rows, batch_size):
        end_idx = min(start_idx + batch_size, total_rows)
        chunk = df.iloc[start_idx:end_idx][cols]

        # Convert to records with None for NaNs so SQLite stores NULL
        chunk_vals = chunk.where(pd.notna(chunk), None).values.tolist()

        cursor.executemany(sql, chunk_vals)
        conn.commit()
        inserted += len(chunk_vals)

        logger.info(
            f"Inserted {inserted:,} / {total_rows:,} rows "
            f"({(inserted / total_rows) * 100:.1f}%)"
        )

    return inserted


def seed_feature_store(
    db_path: Path,
    raw_data_dir: Path,
    batch_size: int = 25000,
    limit: Optional[int] = None,
) -> int:
    """
    Run end-to-end memory-safe feature store seeding pipeline.
    """
    t0 = time.time()
    logger.info("===========================================================")
    logger.info("FinTrustX Feature Store Seeding Pipeline Starting")
    logger.info(f"Target DB: {db_path}")
    logger.info(f"Raw Data Dir: {raw_data_dir}")
    logger.info(f"Batch Size: {batch_size}")
    logger.info(f"Row Limit: {limit}")
    logger.info(f"Initial RAM: {get_current_ram_mb():.1f} MB")
    logger.info("===========================================================")

    aggregator = DataAggregator(raw_data_dir=raw_data_dir)

    # -------------------------------------------------------------
    # Stage 1: Sequential Execution - Aggregate Bureau
    # -------------------------------------------------------------
    logger.info(">>> Stage 1/4: Aggregating bureau.csv...")
    t_stage = time.time()
    bureau_agg = aggregator.aggregate_bureau()
    logger.info(
        f"Stage 1 Complete: Bureau agg shape={bureau_agg.shape} in "
        f"{time.time() - t_stage:.2f}s (RAM: {get_current_ram_mb():.1f} MB)"
    )

    # -------------------------------------------------------------
    # Stage 2: Sequential Execution - Aggregate Previous Application
    # -------------------------------------------------------------
    logger.info(">>> Stage 2/4: Aggregating previous_application.csv...")
    t_stage = time.time()
    prev_agg = aggregator.aggregate_previous_application()
    logger.info(
        f"Stage 2 Complete: Prev app agg shape={prev_agg.shape} in "
        f"{time.time() - t_stage:.2f}s (RAM: {get_current_ram_mb():.1f} MB)"
    )

    # -------------------------------------------------------------
    # Stage 3: Load Minimal Anchor & Merge Features
    # -------------------------------------------------------------
    logger.info(">>> Stage 3/4: Loading application anchors & merging...")
    t_stage = time.time()
    anchor_cols = ["SK_ID_CURR", "AMT_INCOME_TOTAL", "AMT_CREDIT"]

    train_path = raw_data_dir / "application_train.csv"
    if not train_path.exists():
        raise FileNotFoundError(f"application_train.csv not found at {train_path}")

    logger.info(f"Loading anchor cols from {train_path.name}...")
    train_anchor = pd.read_csv(train_path, usecols=anchor_cols)
    train_anchor = optimize_dtypes(train_anchor)

    test_path = raw_data_dir / "application_test.csv"
    if test_path.exists():
        logger.info(f"Loading anchor cols from {test_path.name}...")
        test_anchor = pd.read_csv(test_path, usecols=anchor_cols)
        test_anchor = optimize_dtypes(test_anchor)
        main_df = pd.concat([train_anchor, test_anchor], ignore_index=True)
        del test_anchor
    else:
        main_df = train_anchor

    del train_anchor
    gc.collect()

    main_df = main_df.drop_duplicates(subset=["SK_ID_CURR"]).reset_index(drop=True)

    if limit is not None and limit > 0:
        logger.info(f"Applying limit: truncating main_df to {limit} rows.")
        main_df = main_df.iloc[:limit].copy()

    logger.info(
        f"Performing feature merge for {len(main_df):,} applicants..."
    )
    merged = aggregator.merge_features(
        main_df=main_df,
        bureau_agg=bureau_agg,
        prev_agg=prev_agg,
    )

    # Explicit Garbage Collection of intermediate frames
    del bureau_agg, prev_agg, main_df
    gc.collect()

    # Select only table columns
    feature_df = merged[ALL_TABLE_COLUMNS].copy()
    del merged
    gc.collect()

    # Ensure SK_ID_CURR is int32/int64
    feature_df["SK_ID_CURR"] = feature_df["SK_ID_CURR"].astype(int)
    feature_df = optimize_dtypes(feature_df)

    logger.info(
        f"Stage 3 Complete: Merged feature shape={feature_df.shape} in "
        f"{time.time() - t_stage:.2f}s (RAM: {get_current_ram_mb():.1f} MB)"
    )

    # -------------------------------------------------------------
    # Stage 4: Persist to SQLite
    # -------------------------------------------------------------
    logger.info(">>> Stage 4/4: Initializing SQLite and persisting features...")
    t_stage = time.time()
    conn = initialize_sqlite_db(db_path, table_name="applicant_features_new")

    try:
        inserted = insert_features_chunked(
            conn=conn,
            df=feature_df,
            batch_size=batch_size,
            table_name="applicant_features_new",
        )
        # Create index after insertion
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_applicant_features_new_sk_id "
            "ON applicant_features_new (SK_ID_CURR);"
        )

        # Atomic swap
        try:
            conn.execute("ALTER TABLE applicant_features RENAME TO applicant_features_old;")
        except sqlite3.OperationalError:
            pass  # applicant_features does not exist yet

        conn.execute("ALTER TABLE applicant_features_new RENAME TO applicant_features;")
        conn.execute("DROP TABLE IF EXISTS applicant_features_old;")
        
        # Checkpoint WAL
        conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
    finally:
        conn.close()

    del feature_df
    gc.collect()

    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    logger.info(
        f"Stage 4 Complete: Persisted {inserted:,} rows in "
        f"{time.time() - t_stage:.2f}s. DB Size: {db_size_mb:.2f} MB"
    )

    total_time = time.time() - t0
    logger.info("===========================================================")
    logger.info(f"Seeding Complete! Total time: {total_time:.2f}s")
    logger.info(f"Total applicants persisted: {inserted:,}")
    logger.info(f"Total columns per applicant: {len(ALL_TABLE_COLUMNS)}")
    logger.info(f"Final DB Path: {db_path} ({db_size_mb:.2f} MB)")
    logger.info(f"Final RAM: {get_current_ram_mb():.1f} MB")
    logger.info("===========================================================")

    return inserted


def verify_database(db_path: Path) -> None:
    """
    Perform sanity checks and measure sample query latency.

    Parameters
    ----------
    db_path : Path
        Path to SQLite database to verify.
    """
    logger.info(f"Verifying SQLite database at {db_path}...")
    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # Check table existence and columns
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(applicant_features);")
        columns = cursor.fetchall()
        col_names = [c["name"] for c in columns]
        pk_col = next((c["name"] for c in columns if c["pk"] == 1), None)

        logger.info(f"Table columns: {len(col_names)}")
        logger.info(f"Primary key column: {pk_col}")
        assert pk_col == "SK_ID_CURR", f"Expected primary key SK_ID_CURR, got {pk_col}"
        assert len(col_names) == len(ALL_TABLE_COLUMNS), (
            f"Expected {len(ALL_TABLE_COLUMNS)} columns, got {len(col_names)}"
        )

        # Check total rows
        cursor.execute("SELECT COUNT(*) AS total FROM applicant_features;")
        total_rows = cursor.fetchone()["total"]
        logger.info(f"Total rows in applicant_features: {total_rows:,}")
        assert total_rows > 0, "applicant_features table is empty!"

        # Test sample queries and measure latency
        sample_ids = [100002, 100003, 100045]
        for sid in sample_ids:
            t_start = time.perf_counter()
            cursor.execute(
                "SELECT * FROM applicant_features WHERE SK_ID_CURR = ?",
                (sid,),
            )
            row = cursor.fetchone()
            latency_ms = (time.perf_counter() - t_start) * 1000.0

            if row:
                row_dict = dict(row)
                bureau_count = row_dict.get("BUREAU_LOAN_COUNT")
                prev_count = row_dict.get("PREV_APP_COUNT")
                logger.info(
                    f"Sample Query ID {sid}: Found in {latency_ms:.3f} ms | "
                    f"BUREAU_LOAN_COUNT={bureau_count}, PREV_APP_COUNT={prev_count}"
                )
            else:
                logger.warning(
                    f"Sample Query ID {sid}: Not found (queried in {latency_ms:.3f} ms)"
                )

        logger.info("Database verification passed successfully!")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Seed SQLite Feature Store with aggregated historical features."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DATA_DIR / "feature_store.db",
        help="Target SQLite database file path (default: data/feature_store.db)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Path to raw data directory (default: data/raw)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25000,
        help="Insert chunk size (default: 25000)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row limit for quick testing (e.g. 50000)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Skip seeding and only run verification queries on existing DB",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.verify_only:
        verify_database(args.db_path)
        return

    seed_feature_store(
        db_path=args.db_path,
        raw_data_dir=args.data_dir,
        batch_size=args.batch_size,
        limit=args.limit,
    )

    verify_database(args.db_path)


if __name__ == "__main__":
    main()
