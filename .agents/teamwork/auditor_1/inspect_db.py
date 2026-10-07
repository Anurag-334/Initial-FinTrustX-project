import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('data/feature_store.db')
cursor = conn.cursor()

# 1. Check table info
cursor.execute("PRAGMA table_info(applicant_features);")
cols = cursor.fetchall()
col_names = [c[1] for c in cols]
pk_col = [c[1] for c in cols if c[5] == 1]

print(f"Total columns: {len(col_names)}")
print(f"PK column: {pk_col}")
print(f"First 10 columns: {col_names[:10]}")
print(f"Last 10 columns: {col_names[-10:]}")

# 2. Check row count
cursor.execute("SELECT COUNT(*) FROM applicant_features;")
total_rows = cursor.fetchone()[0]
print(f"Total rows: {total_rows}")

# 3. Check sample rows
cursor.execute("SELECT SK_ID_CURR, BUREAU_LOAN_COUNT, PREV_APP_COUNT, BUREAU_AMT_CREDIT_SUM_SUM, PREV_AMT_CREDIT_SUM, TOTAL_DEBT_TO_INCOME FROM applicant_features LIMIT 5;")
sample_rows = cursor.fetchall()
print("Sample rows:")
for r in sample_rows:
    print(r)

# 4. Check specific known applicants from Home Credit (e.g. 100002, 100003, 100045)
for sid in [100002, 100003, 100045]:
    cursor.execute("SELECT SK_ID_CURR, BUREAU_LOAN_COUNT, PREV_APP_COUNT, BUREAU_AMT_CREDIT_SUM_SUM, PREV_AMT_CREDIT_SUM, TOTAL_DEBT_TO_INCOME FROM applicant_features WHERE SK_ID_CURR = ?;", (sid,))
    print(f"Known applicant {sid}: {cursor.fetchone()}")

# 5. Check statistical summary of columns to ensure genuine data distribution
df = pd.read_sql_query("SELECT BUREAU_LOAN_COUNT, PREV_APP_COUNT, BUREAU_AMT_CREDIT_SUM_SUM, PREV_AMT_APPLICATION_MEAN FROM applicant_features LIMIT 10000;", conn)
print("\nDistribution stats for first 10,000 rows:")
print(df.describe())

# 6. Verify non-triviality and absence of constant values across columns
cursor.execute("SELECT COUNT(DISTINCT BUREAU_LOAN_COUNT), COUNT(DISTINCT PREV_APP_COUNT), COUNT(DISTINCT TOTAL_DEBT_TO_INCOME) FROM applicant_features;")
distinct_counts = cursor.fetchone()
print(f"Distinct counts (BUREAU_LOAN_COUNT, PREV_APP_COUNT, TOTAL_DEBT_TO_INCOME): {distinct_counts}")

conn.close()
