"""
Comprehensive Forensic Audit Script for Milestone 2:
Inspects models/xgboost.joblib, models/xgboost.json, data/processed_test.parquet,
and evaluation metrics.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

PROJECT_ROOT = Path("d:/Projects/Credit-risk-ai")


def hash_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def audit():
    results = {}

    # 1. File Artifact Verification
    model_path = PROJECT_ROOT / "models" / "xgboost.joblib"
    json_path = PROJECT_ROOT / "models" / "xgboost.json"
    test_path = PROJECT_ROOT / "data" / "processed_test.parquet"
    train_path = PROJECT_ROOT / "data" / "processed_train.parquet"
    feat_names_path = PROJECT_ROOT / "models" / "preprocessed_feature_names.csv"

    print("=== 1. FILE METADATA AND INTEGRITY ===")
    assert model_path.exists(), f"Missing model: {model_path}"
    assert json_path.exists(), f"Missing json: {json_path}"
    assert test_path.exists(), f"Missing test data: {test_path}"

    model_stat = model_path.stat()
    json_stat = json_path.stat()
    test_stat = test_path.stat()

    results["model_size_bytes"] = model_stat.st_size
    results["model_sha256"] = hash_file(model_path)
    results["json_size_bytes"] = json_stat.st_size
    results["json_sha256"] = hash_file(json_path)

    print(f"Model path: {model_path}")
    print(f"Model size: {model_stat.st_size} bytes ({model_stat.st_size / 1024:.2f} KB)")
    print(f"Model SHA256: {results['model_sha256']}")
    print(f"JSON size: {json_stat.st_size} bytes")
    print(f"JSON SHA256: {results['json_sha256']}")

    # 2. Deserialization & Class Inspection
    print("\n=== 2. DESERIALIZATION AND BOOSTER ARCHITECTURE ===")
    loaded_obj = joblib.load(model_path)
    results["loaded_class"] = type(loaded_obj).__name__
    results["loaded_module"] = type(loaded_obj).__module__
    print(f"Loaded object type: {type(loaded_obj)} (module: {type(loaded_obj).__module__})")

    # Resolve underlying booster
    if hasattr(loaded_obj, "get_booster"):
        booster = loaded_obj.get_booster()
    elif hasattr(loaded_obj, "booster"):
        booster = loaded_obj.booster
    elif hasattr(loaded_obj, "model") and hasattr(loaded_obj.model, "get_booster"):
        booster = loaded_obj.model.get_booster()
    else:
        booster = loaded_obj

    results["booster_class"] = type(booster).__name__
    print(f"Booster object type: {type(booster)}")

    # Check tree dump and count
    dump = booster.get_dump(dump_format="text")
    tree_count = len(dump)
    results["tree_count_dump"] = tree_count
    print(f"Tree count from booster.get_dump(): {tree_count}")

    # Inspect booster attributes / config
    config_str = booster.save_config()
    config_dict = json.loads(config_str)
    results["booster_config_summary"] = {
        "tree_method": config_dict.get("learner", {}).get("gradient_booster", {}).get("gbtree_train_param", {}).get("tree_method"),
        "objective": config_dict.get("learner", {}).get("learner_train_param", {}).get("objective"),
    }
    print("Booster config tree_method:", results["booster_config_summary"]["tree_method"])
    print("Booster config objective:", results["booster_config_summary"]["objective"])

    # Inspect first 3 trees and last tree in dump to verify non-trivial tree structure
    print("\nSample tree structure from dump[0] (first 5 lines):")
    for line in dump[0].split("\n")[:5]:
        print("  ", line)

    print("\nSample tree structure from dump[-1] (first 5 lines):")
    for line in dump[-1].split("\n")[:5]:
        print("  ", line)

    # 3. Features & Importances
    print("\n=== 3. FEATURE SPECIFICATION & IMPORTANCE FORENSICS ===")
    # Load preprocessed feature names
    expected_feats_df = pd.read_csv(feat_names_path)
    expected_feat_names = expected_feats_df.iloc[:, 0].tolist() if "feature_name" not in expected_feats_df.columns else expected_feats_df["feature_name"].tolist()
    results["expected_feature_count"] = len(expected_feat_names)
    print(f"Feature names file count: {len(expected_feat_names)}")

    # Booster feature names
    booster_feat_names = booster.feature_names
    results["booster_feature_count"] = len(booster_feat_names) if booster_feat_names else None
    print(f"Booster feature names count: {len(booster_feat_names) if booster_feat_names else 'None'}")

    # Importance scores
    score_weight = booster.get_score(importance_type="weight")
    score_gain = booster.get_score(importance_type="gain")
    score_cover = booster.get_score(importance_type="cover")

    results["features_with_weight"] = len(score_weight)
    results["features_with_gain"] = len(score_gain)
    results["features_with_cover"] = len(score_cover)

    print(f"Features with non-zero weight (splits): {len(score_weight)} / {len(expected_feat_names)}")
    print(f"Features with non-zero gain: {len(score_gain)} / {len(expected_feat_names)}")
    print(f"Features with non-zero cover: {len(score_cover)} / {len(expected_feat_names)}")

    # Top 10 features by gain
    top_gain = sorted(score_gain.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nTop 10 features by gain:")
    for f, g in top_gain:
        print(f"  {f:40s}: gain={g:.4f}, weight={score_weight.get(f, 0)}")

    # Check presence of Milestone 1 features (BUREAU and PREV) in top splits
    bureau_features_used = [f for f in score_gain if f.startswith("BUREAU_")]
    prev_features_used = [f for f in score_gain if f.startswith("PREV_")]
    results["bureau_features_used"] = len(bureau_features_used)
    results["prev_features_used"] = len(prev_features_used)
    print(f"BUREAU features actively used in splits: {len(bureau_features_used)}")
    print(f"PREV features actively used in splits: {len(prev_features_used)}")

    # 4. Empirical Test Inference & ROC-AUC Recalculation
    print("\n=== 4. TEST DATA INFERENCE & ROC-AUC RE-EVALUATION ===")
    test_df = pd.read_parquet(test_path)
    print(f"Loaded test dataframe: {test_df.shape}")
    assert "TARGET" in test_df.columns, "TARGET column not in test_df"

    X_test = test_df.drop(columns=["TARGET"])
    y_test = test_df["TARGET"].astype(int)

    print(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")
    print(f"Class 0 count: {(y_test == 0).sum()}, Class 1 count: {(y_test == 1).sum()}")
    print(f"Default rate: {y_test.mean():.6f}")

    # Predict probabilities directly via loaded_obj
    t0 = time.time()
    if hasattr(loaded_obj, "predict_proba"):
        probs = loaded_obj.predict_proba(X_test)
        if probs.ndim == 2:
            p1 = probs[:, 1]
        else:
            p1 = probs
    else:
        # If raw Booster
        import xgboost as xgb
        dtest = xgb.DMatrix(X_test)
        p1 = booster.predict(dtest)
    pred_time = time.time() - t0
    print(f"Inference completed on 61,503 rows in {pred_time:.4f} seconds ({pred_time / len(X_test) * 1000:.4f} ms/row)")

    # Distribution of probabilities
    results["prob_min"] = float(p1.min())
    results["prob_max"] = float(p1.max())
    results["prob_mean"] = float(p1.mean())
    results["prob_std"] = float(p1.std())
    results["prob_distinct_count"] = int(len(np.unique(p1)))

    print(f"Predicted probabilities: min={p1.min():.6f}, max={p1.max():.6f}, mean={p1.mean():.6f}, std={p1.std():.6f}")
    print(f"Distinct probability values out of 61,503: {results['prob_distinct_count']}")

    # Calculate ROC-AUC independently
    calculated_auc = roc_auc_score(y_test, p1)
    results["calculated_roc_auc"] = float(calculated_auc)
    print(f"Calculated ROC-AUC: {calculated_auc:.16f}")
    print(f"Worker M2 reported: 0.7793832838928354")
    diff = abs(calculated_auc - 0.7793832838928354)
    print(f"Absolute discrepancy: {diff:.2e}")

    # Threshold 0.50 evaluation
    preds_binary = (p1 >= 0.50).astype(int)
    cm = confusion_matrix(y_test, preds_binary)
    tn, fp, fn, tp = cm.ravel()
    results["confusion_matrix"] = {"TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp)}
    print(f"Confusion Matrix (threshold=0.50): TN={tn}, FP={fp}, FN={fn}, TP={tp}")

    results["accuracy"] = float(accuracy_score(y_test, preds_binary))
    results["precision"] = float(precision_score(y_test, preds_binary, zero_division=0))
    results["recall"] = float(recall_score(y_test, preds_binary))
    results["f1"] = float(f1_score(y_test, preds_binary))
    results["average_precision"] = float(average_precision_score(y_test, p1))
    results["balanced_accuracy"] = float(balanced_accuracy_score(y_test, preds_binary))
    results["mcc"] = float(matthews_corrcoef(y_test, preds_binary))
    results["cohen_kappa"] = float(cohen_kappa_score(y_test, preds_binary))
    results["logloss"] = float(log_loss(y_test, p1))
    results["brier_score"] = float(brier_score_loss(y_test, p1))

    print(f"Accuracy: {results['accuracy']:.16f}")
    print(f"Precision: {results['precision']:.16f}")
    print(f"Recall: {results['recall']:.16f}")
    print(f"F1: {results['f1']:.16f}")
    print(f"Average Precision (PR-AUC): {results['average_precision']:.16f}")
    print(f"Log Loss: {results['logloss']:.16f}")
    print(f"Brier Score: {results['brier_score']:.16f}")

    # 5. Adversarial Input Perturbation & Sensitivity Testing
    print("\n=== 5. ADVERSARIAL SENSITIVITY & INTEGRITY STRESS TEST ===")
    # Test A: Zero vector inference
    zeros_df = pd.DataFrame(np.zeros((5, X_test.shape[1])), columns=X_test.columns)
    zero_probs = loaded_obj.predict_proba(zeros_df)[:, 1] if hasattr(loaded_obj, "predict_proba") else booster.predict(xgb.DMatrix(zeros_df))
    print(f"Zero vector probabilities (5 identical rows): {zero_probs}")
    assert np.allclose(zero_probs, zero_probs[0]), "Zero vector predictions inconsistent"

    # Test B: Inversion / Extreme values
    extreme_pos_df = pd.DataFrame(np.ones((1, X_test.shape[1])) * 10.0, columns=X_test.columns)
    extreme_neg_df = pd.DataFrame(np.ones((1, X_test.shape[1])) * -10.0, columns=X_test.columns)
    pos_prob = (loaded_obj.predict_proba(extreme_pos_df)[:, 1] if hasattr(loaded_obj, "predict_proba") else booster.predict(xgb.DMatrix(extreme_pos_df)))[0]
    neg_prob = (loaded_obj.predict_proba(extreme_neg_df)[:, 1] if hasattr(loaded_obj, "predict_proba") else booster.predict(xgb.DMatrix(extreme_neg_df)))[0]
    print(f"Extreme +10 vector probability: {pos_prob:.6f}")
    print(f"Extreme -10 vector probability: {neg_prob:.6f}")
    assert pos_prob != neg_prob, "Model fails to distinguish extreme positive and negative inputs!"

    # Test C: Single-feature gradient / sensitivity test
    # Find top feature by gain
    top_feat = top_gain[0][0]
    sample_row = X_test.iloc[[0]].copy()
    base_val = sample_row[top_feat].values[0]
    variations = []
    for delta in [-2.0, -1.0, 0.0, +1.0, +2.0]:
        test_var = sample_row.copy()
        test_var[top_feat] = base_val + delta
        p_var = (loaded_obj.predict_proba(test_var)[:, 1] if hasattr(loaded_obj, "predict_proba") else booster.predict(xgb.DMatrix(test_var)))[0]
        variations.append((delta, p_var))
    print(f"Top feature '{top_feat}' perturbation response:")
    for delta, p_var in variations:
        print(f"  delta={delta:+4.1f}: predicted_prob={p_var:.6f}")

    unique_pert_probs = len(set(p for _, p in variations))
    assert unique_pert_probs > 1, "Model predictions did not respond to perturbations of top feature!"
    print("Sensitivity verification passed: predictions dynamically respond to feature changes.")

    # 6. Save audit findings
    out_file = PROJECT_ROOT / ".agents" / "teamwork" / "teamwork_preview_auditor_m2" / "audit_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nAudit results successfully written to {out_file}")


if __name__ == "__main__":
    audit()
