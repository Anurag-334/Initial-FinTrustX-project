import joblib
import numpy as np
import pandas as pd
import psutil
import os

print("--- Checking Artifacts ---")
train_path = "data/processed_train.parquet"
test_path = "data/processed_test.parquet"
pipeline_path = "models/preprocessing_pipeline.joblib"
feat_path = "models/preprocessed_feature_names.csv"

df_train = pd.read_parquet(train_path)
df_test = pd.read_parquet(test_path)
feat_df = pd.read_csv(feat_path)
pipeline = joblib.load(pipeline_path)

print(f"df_train shape: {df_train.shape}")
print(f"df_test shape: {df_test.shape}")
print(f"Total rows: {len(df_train) + len(df_test)}")
print(f"feat_df shape: {feat_df.shape}")

# Dtypes
dtypes_set = set(df_train.dtypes.unique())
print(f"Train dtypes: {dtypes_set}")
target_train_dtype = df_train["TARGET"].dtype
target_test_dtype = df_test["TARGET"].dtype
print(f"Target dtypes: train={target_train_dtype}, test={target_test_dtype}")

# Target distributions
train_target = df_train["TARGET"].value_counts().to_dict()
test_target = df_test["TARGET"].value_counts().to_dict()
print(f"Train targets: {train_target}")
print(f"Test targets: {test_target}")
print(f"Train default rate: {df_train['TARGET'].mean():.6f}")
print(f"Test default rate: {df_test['TARGET'].mean():.6f}")

# Overlap & Nulls
overlap = len(set(df_train.index).intersection(set(df_test.index)))
print(f"Train/Test index overlap: {overlap}")
print(f"Train nulls: {df_train.isna().sum().sum()}")
print(f"Test nulls: {df_test.isna().sum().sum()}")
print(f"Train infs: {np.isinf(df_train.values).sum()}")
print(f"Test infs: {np.isinf(df_test.values).sum()}")

# Leakage check: SK_ID_CURR
id_cols_train = [c for c in df_train.columns if "SK_ID" in c]
id_cols_test = [c for c in df_test.columns if "SK_ID" in c]
id_cols_feat = [c for c in feat_df["feature_name"] if "SK_ID" in c]
print(f"SK_ID cols in train: {id_cols_train}")
print(f"SK_ID cols in test: {id_cols_test}")
print(f"SK_ID cols in feat: {id_cols_feat}")

# Column alignment
feature_cols = [c for c in df_train.columns if c != "TARGET"]
print(f"Number of feature cols: {len(feature_cols)}")
cols_match = (feature_cols == feat_df["feature_name"].tolist())
print(f"Columns match feature_names.csv exactly: {cols_match}")

# Check pipeline object
print(f"Pipeline object type: {type(pipeline)}")
print(f"Pipeline transformers: {[t[0] for t in pipeline.transformers_]}")
num_transformer = [t for t in pipeline.transformers_ if t[0] == "num"][0]
cat_transformer = [t for t in pipeline.transformers_ if t[0] == "cat"][0]
print(f"Num input features: {len(num_transformer[2])}")
print(f"Cat input features: {len(cat_transformer[2])}")

# Check variance / standard deviations (ensure not all zeros or dummy constants)
stds = df_train[feature_cols].std()
zero_std_cols = stds[stds == 0].index.tolist()
print(f"Zero standard deviation columns count: {len(zero_std_cols)}")
if zero_std_cols:
    print(f"Zero std cols: {zero_std_cols}")
print(f"Mean of feature standard deviations: {stds.mean():.4f}")
print(f"Min standard deviation: {stds.min():.4f}, Max: {stds.max():.4f}")
