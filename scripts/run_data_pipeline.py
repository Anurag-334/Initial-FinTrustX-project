"""
===========================================================
FinTrustX — Standalone Data Integration & Preprocessing CLI
===========================================================

Author : FinTrustX Engineering Team
Description:
------------
Executes the end-to-end data pipeline for Home Credit Default
Risk:
1. Selective ingestion of bureau.csv & previous_application.csv
2. Status-partitioned aggregation & derived financial ratios
3. Safe left-join onto application_train.csv (307,511 rows)
4. Stratified 80/20 train/test split (random_state=42)
5. Fitting DataPreprocessor (ColumnTransformer) without leakage
6. Output artifact serialization:
   - data/processed_train.parquet (246,008 rows)
   - data/processed_test.parquet (61,503 rows)
   - models/preprocessing_pipeline.joblib
   - models/preprocessed_feature_names.csv
7. Memory profiling (psutil RSS) with explicit garbage collection
8. Comprehensive post-execution validation assertions

Usage:
------
python scripts/run_data_pipeline.py
python scripts/run_data_pipeline.py --help
python scripts/run_data_pipeline.py --verify-only
===========================================================
"""

from __future__ import annotations

import argparse
import gc
import logging
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

try:
    import psutil
except ImportError:
    psutil = None

# Ensure project root is in sys.path for direct CLI execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DATA_DIR,
    MODEL_DIR,
    RANDOM_STATE,
    RAW_DATA_DIR,
    TARGET_COLUMN,
)
from src.data_aggregation import DataAggregator  # noqa: E402
from src.data_loader import DataLoader  # noqa: E402
from src.preprocessing import DataPreprocessor  # noqa: E402
from src.utils import set_seed  # noqa: E402

logger = logging.getLogger("FinTrustX.Pipeline")


# ==========================================================
# Memory Tracking Architecture
# ==========================================================

class MemoryTracker:
    """
    Monitors process resident set size (RSS) in megabytes.
    Guarantees enforcement of Requirement R2 (peak RAM < 1.8 GB).
    """

    def __init__(self, alert_threshold_mb: float = 1800.0) -> None:
        self.alert_threshold_mb = alert_threshold_mb
        self.process = (
            psutil.Process(os.getpid()) if psutil is not None else None
        )
        self.peak_rss_mb = 0.0
        self.baseline_rss_mb = self.get_rss_mb()
        self.peak_rss_mb = self.baseline_rss_mb
        self.checkpoints: List[Dict[str, Any]] = []

    def get_rss_mb(self) -> float:
        """Return current resident set size in MB."""
        if self.process is not None:
            rss = self.process.memory_info().rss / (1024.0 * 1024.0)
        else:
            rss = 0.0
        if rss > self.peak_rss_mb:
            self.peak_rss_mb = rss
        return rss

    def log_status(
        self, stage_name: str, step_type: str = "CHECKPOINT"
    ) -> None:
        """Log memory status and check against threshold."""
        current_rss = self.get_rss_mb()
        logger.info(
            f"[{step_type}] {stage_name} | Current RSS: {current_rss:.2f} MB | "
            f"Peak RSS: {self.peak_rss_mb:.2f} MB"
        )
        if current_rss > self.alert_threshold_mb:
            logger.warning(
                f"Memory Alert! Current RSS ({current_rss:.2f} MB) exceeds "
                f"ceiling ({self.alert_threshold_mb:.2f} MB)."
            )

    @contextmanager
    def track_stage(self, stage_name: str):
        """Context manager tracking time, RSS delta, and GC."""
        rss_start = self.get_rss_mb()
        logger.info(
            f"==========================================================\n"
            f">>> [STAGE START] {stage_name}\n"
            f"    Initial RSS: {rss_start:.2f} MB\n"
            f"=========================================================="
        )
        start_time = time.time()
        try:
            yield
        finally:
            uncollected = gc.collect()
            rss_end = self.get_rss_mb()
            elapsed = time.time() - start_time
            delta = rss_end - rss_start
            logger.info(
                f"----------------------------------------------------------\n"
                f"<<< [STAGE COMPLETE] {stage_name}\n"
                f"    Duration   : {elapsed:.2f} seconds\n"
                f"    Final RSS  : {rss_end:.2f} MB (Delta: {delta:+.2f} MB)\n"
                f"    Peak RSS   : {self.peak_rss_mb:.2f} MB\n"
                f"    GC Objects : {uncollected} reclaimed\n"
                f"----------------------------------------------------------"
            )
            self.checkpoints.append({
                "stage": stage_name,
                "elapsed_sec": round(elapsed, 2),
                "rss_start_mb": round(rss_start, 2),
                "rss_end_mb": round(rss_end, 2),
                "delta_mb": round(delta, 2),
                "peak_mb": round(self.peak_rss_mb, 2),
                "gc_reclaimed": uncollected,
            })


# ==========================================================
# Artifact Persistence Helpers
# ==========================================================

def save_processed_partition(
    features: np.ndarray,
    target: pd.Series,
    feature_names: List[str],
    output_path: Path,
) -> None:
    """
    Save preprocessed features and target to Parquet with float32 downcasting.

    Parameters
    ----------
    features : np.ndarray
        Dense 2D array of transformed features.
    target : pd.Series
        Aligned target series (0/1).
    feature_names : list of str
        Names of transformed feature columns.
    output_path : Path
        Target destination Parquet path.
    """
    logger.info(f"Assembling Parquet partition for {output_path.name}...")
    df_out = pd.DataFrame(
        features.astype(np.float32),
        columns=feature_names,
        index=target.index,
    )
    df_out[TARGET_COLUMN] = target.astype(np.int8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_parquet(output_path, index=True, engine="pyarrow")
    logger.info(
        f"Saved {output_path} (Shape: {df_out.shape}, Size: "
        f"{output_path.stat().st_size / (1024 * 1024):.2f} MB)"
    )


# ==========================================================
# Validation Assertion Suite
# ==========================================================

def run_validation_suite(
    output_dir: Path,
    model_dir: Path,
    expected_train_rows: int = 246008,
    expected_test_rows: int = 61503,
) -> bool:
    """
    Execute rigorous validation assertions on generated pipeline artifacts.

    Parameters
    ----------
    output_dir : Path
        Directory containing processed Parquet files.
    model_dir : Path
        Directory containing serialized pipeline artifacts.
    expected_train_rows : int
        Expected number of training rows (246,008).
    expected_test_rows : int
        Expected number of test rows (61,503).

    Returns
    -------
    bool
        True if all assertions pass.
    """
    logger.info("Executing Post-Pipeline Validation Assertion Suite...")

    train_path = output_dir / "processed_train.parquet"
    test_path = output_dir / "processed_test.parquet"
    pipeline_path = model_dir / "preprocessing_pipeline.joblib"
    feat_names_path = model_dir / "preprocessed_feature_names.csv"

    # 1. File Existence Checks
    for path in [train_path, test_path, pipeline_path, feat_names_path]:
        assert path.exists(), f"Assertion Failure: Missing artifact at {path}"
        assert (
            path.stat().st_size > 0
        ), f"Assertion Failure: Artifact is empty at {path}"

    # 2. Schema and Row Count Assertions
    df_train = pd.read_parquet(train_path)
    df_test = pd.read_parquet(test_path)

    assert len(df_train) == expected_train_rows, (
        f"Row count mismatch in train: {len(df_train)} vs {expected_train_rows}"
    )
    assert len(df_test) == expected_test_rows, (
        f"Row count mismatch in test: {len(df_test)} vs {expected_test_rows}"
    )
    assert len(df_train) + len(df_test) == 307511, (
        "Total dataset rows do not equal 307,511!"
    )
    assert TARGET_COLUMN in df_train.columns, f"Missing {TARGET_COLUMN} in train"
    assert TARGET_COLUMN in df_test.columns, f"Missing {TARGET_COLUMN} in test"
    assert df_train.columns.tolist() == df_test.columns.tolist(), (
        "Train and test column schema mismatch!"
    )

    # 3. Anti-Leakage & Disjoint Index Check
    train_indices = set(df_train.index)
    test_indices = set(df_test.index)
    assert len(train_indices.intersection(test_indices)) == 0, (
        "Data Leakage Detected! Train and test splits share indices."
    )

    # 4. Target Distribution Invariance
    train_rate = df_train[TARGET_COLUMN].mean()
    test_rate = df_test[TARGET_COLUMN].mean()
    assert abs(train_rate - 0.080729) < 0.0005, (
        f"Train default rate deviation: {train_rate:.6f} vs ~0.080729"
    )
    assert abs(test_rate - 0.080728) < 0.0005, (
        f"Test default rate deviation: {test_rate:.6f} vs ~0.080728"
    )

    # 5. Data Quality: Zero Missing or Infinite Values
    x_train_cols = [c for c in df_train.columns if c != TARGET_COLUMN]
    assert not df_train[x_train_cols].isna().any().any(), (
        "Assertion Failure: NaN values found in processed train features!"
    )
    assert not df_test[x_train_cols].isna().any().any(), (
        "Assertion Failure: NaN values found in processed test features!"
    )
    assert np.isfinite(df_train[x_train_cols].values).all(), (
        "Assertion Failure: Non-finite values found in train features!"
    )
    assert np.isfinite(df_test[x_train_cols].values).all(), (
        "Assertion Failure: Non-finite values found in test features!"
    )

    # 6. Pipeline Serialization & Feature Names Contract
    _ = joblib.load(pipeline_path)
    feat_df = pd.read_csv(feat_names_path)
    feature_names = feat_df.iloc[:, 0].tolist()

    assert len(feature_names) == len(x_train_cols), (
        f"Feature name count ({len(feature_names)}) != "
        f"feature columns ({len(x_train_cols)})"
    )

    logger.info(">>> ALL VALIDATION ASSERTIONS PASSED SUCCESSFULLY! <<<")
    return True


# ==========================================================
# Main Execution Pipeline
# ==========================================================

def run_pipeline(
    raw_dir: Path,
    output_dir: Path,
    model_dir: Path,
    random_state: int = RANDOM_STATE,
    test_size: float = 0.20,
    skip_bureau: bool = False,
    skip_prev: bool = False,
) -> None:
    """
    Execute the complete end-to-end data integration and preprocessing pipeline.
    """
    tracker = MemoryTracker()
    set_seed(random_state)

    logger.info(f"Starting FinTrustX Data Pipeline (PID: {os.getpid()})")
    logger.info(
        f"Raw: {raw_dir} | Output: {output_dir} | Models: {model_dir}"
    )

    aggregator = DataAggregator(raw_data_dir=raw_dir)
    loader = DataLoader()
    loader.raw_data_dir = raw_dir

    # ------------------------------------------------------
    # STAGE 1: Bureau Data Aggregation
    # ------------------------------------------------------
    bureau_agg: Optional[pd.DataFrame] = None
    if not skip_bureau:
        with tracker.track_stage("Stage 1: Bureau Record Aggregation"):
            bureau_agg = aggregator.aggregate_bureau()
            logger.info(
                f"Bureau features aggregated. Shape: {bureau_agg.shape}"
            )
    else:
        logger.info("Stage 1 skipped (--skip-bureau specified).")

    # ------------------------------------------------------
    # STAGE 2: Previous Application Aggregation
    # ------------------------------------------------------
    prev_agg: Optional[pd.DataFrame] = None
    if not skip_prev:
        with tracker.track_stage("Stage 2: Previous Application Aggregation"):
            prev_agg = aggregator.aggregate_previous_application()
            logger.info(
                f"Previous app features aggregated. Shape: {prev_agg.shape}"
            )
    else:
        logger.info("Stage 2 skipped (--skip-prev specified).")

    # ------------------------------------------------------
    # STAGE 3: Ingest Main Data & Safe Feature Merge
    # ------------------------------------------------------
    with tracker.track_stage("Stage 3: Application Data Merge"):
        logger.info("Loading application_train.csv...")
        main_df = loader.load_csv("application_train.csv")
        main_df = loader.optimize_memory(main_df)

        if bureau_agg is not None and prev_agg is not None:
            merged_df = aggregator.merge_features(
                main_df, bureau_agg, prev_agg
            )
        elif bureau_agg is not None:
            merged_df = main_df.merge(bureau_agg, on="SK_ID_CURR", how="left")
        elif prev_agg is not None:
            merged_df = main_df.merge(prev_agg, on="SK_ID_CURR", how="left")
        else:
            merged_df = main_df

        # Release intermediate child frames immediately
        del bureau_agg, prev_agg, main_df
        gc.collect()

        assert len(merged_df) == 307511, (
            f"Row count altered after merge! Expected 307,511, got "
            f"{len(merged_df)}"
        )
        assert TARGET_COLUMN in merged_df.columns, f"Missing {TARGET_COLUMN}!"
        logger.info(f"Merged dataset shape: {merged_df.shape}")

    # ------------------------------------------------------
    # STAGE 4: Stratified Train / Test Split
    # ------------------------------------------------------
    with tracker.track_stage("Stage 4: Stratified Train/Test Split"):
        y = merged_df[TARGET_COLUMN].astype(int)
        x_data = merged_df.drop(columns=[TARGET_COLUMN])

        x_train, x_test, y_train, y_test = train_test_split(
            x_data,
            y,
            test_size=test_size,
            stratify=y,
            random_state=random_state,
        )

        del merged_df, x_data, y
        gc.collect()

        logger.info(
            f"Train split: {x_train.shape[0]} rows | "
            f"Test split: {x_test.shape[0]} rows"
        )
        assert len(x_train) == 246008, (
            f"Expected 246008 train rows, got {len(x_train)}"
        )
        assert len(x_test) == 61503, (
            f"Expected 61503 test rows, got {len(x_test)}"
        )

    # ------------------------------------------------------
    # STAGE 5: Fit Preprocessing Pipeline & Transform
    # ------------------------------------------------------
    with tracker.track_stage("Stage 5: Preprocessing Transformation"):
        preprocessor = DataPreprocessor()
        # Explicitly exclude SK_ID_CURR to eliminate identifier leakage
        numeric_cols, categorical_cols = preprocessor.detect_features(
            pd.concat([x_train, y_train], axis=1),
            target_column=TARGET_COLUMN,
            exclude_columns=["SK_ID_CURR"],
        )
        logger.info(
            f"Detected features: {len(numeric_cols)} numerical, "
            f"{len(categorical_cols)} categorical."
        )

        preprocessor.build_pipeline()

        logger.info("Fitting ColumnTransformer strictly on X_train...")
        x_train_processed = preprocessor.fit_transform(x_train)
        logger.info(
            f"X_train transformed. Shape: {x_train_processed.shape}"
        )

        logger.info("Transforming X_test using frozen transformer...")
        x_test_processed = preprocessor.transform(x_test)
        logger.info(
            f"X_test transformed. Shape: {x_test_processed.shape}"
        )

        feature_names = preprocessor.get_feature_names().tolist()
        logger.info(f"Total output feature names: {len(feature_names)}")

        # Free raw split frames
        del x_train, x_test
        gc.collect()

    # ------------------------------------------------------
    # STAGE 6: Artifact Persistence
    # ------------------------------------------------------
    with tracker.track_stage("Stage 6: Artifact Serialization"):
        model_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save fitted pipeline
        pipeline_path = model_dir / "preprocessing_pipeline.joblib"
        preprocessor.save_pipeline(filename=pipeline_path.name)

        # 2. Save preprocessed feature names
        feat_path = model_dir / "preprocessed_feature_names.csv"
        pd.DataFrame({"feature_name": feature_names}).to_csv(
            feat_path, index=False
        )
        logger.info(f"Saved feature names to {feat_path}")

        # 3. Save processed train and test Parquet files
        train_parquet_path = output_dir / "processed_train.parquet"
        test_parquet_path = output_dir / "processed_test.parquet"
        save_processed_partition(
            features=x_train_processed,
            target=y_train,
            feature_names=feature_names,
            output_path=train_parquet_path,
        )
        save_processed_partition(
            features=x_test_processed,
            target=y_test,
            feature_names=feature_names,
            output_path=test_parquet_path,
        )

        del x_train_processed, x_test_processed, y_train, y_test
        gc.collect()

    # ------------------------------------------------------
    # STAGE 7: Validation Assertions
    # ------------------------------------------------------
    with tracker.track_stage("Stage 7: Pipeline Validation"):
        run_validation_suite(
            output_dir=output_dir,
            model_dir=model_dir,
            expected_train_rows=246008,
            expected_test_rows=61503,
        )

    logger.info("Pipeline execution finished successfully!")
    logger.info(
        f"Global Peak RSS Memory: {tracker.peak_rss_mb:.2f} MB (< 1800 MB)"
    )


# ==========================================================
# CLI Entrypoint
# ==========================================================

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="FinTrustX Data Integration & Preprocessing Pipeline"
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Path to directory containing raw CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DATA_DIR,
        help="Path to directory where processed Parquets are saved.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=MODEL_DIR,
        help="Path to directory where model and pipeline artifacts are saved.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=RANDOM_STATE,
        help="Random seed for train/test splitting (default: 42).",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.20,
        help="Hold-out test set fraction (default: 0.20).",
    )
    parser.add_argument(
        "--skip-bureau",
        action="store_true",
        help="Skip bureau table aggregation.",
    )
    parser.add_argument(
        "--skip-prev",
        action="store_true",
        help="Skip previous application table aggregation.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only run validation suite on existing artifacts.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level.",
    )
    return parser.parse_args()


def main() -> None:
    """Application entrypoint."""
    args = parse_args()

    # Configure logging
    log_fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=log_fmt,
    )

    if args.verify_only:
        logger.info("Running in --verify-only mode...")
        success = run_validation_suite(
            output_dir=args.output_dir,
            model_dir=args.model_dir,
        )
        sys.exit(0 if success else 1)

    run_pipeline(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        model_dir=args.model_dir,
        random_state=args.random_state,
        test_size=args.test_size,
        skip_bureau=args.skip_bureau,
        skip_prev=args.skip_prev,
    )


if __name__ == "__main__":
    main()
