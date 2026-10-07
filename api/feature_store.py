"""
=========================================================
FinTrustX SQLite Feature Store Client
=========================================================
Provides real-time online feature retrieval from the
offline SQLite feature store database.

Author: Anurag Kashyap
=========================================================
"""

import logging
import sqlite3
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from api.config import (
    FEATURE_STORE_DB_PATH,
    FEATURE_STORE_PATH,
    FEATURE_STORE_TABLE_NAME,
)

logger = logging.getLogger(__name__)


class FeatureStore:
    """
    Thread-safe SQLite feature store accessor for applicant historical data.
    Provides fast single and batch queries by SK_ID_CURR with defensive fallbacks.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        table_name: str = FEATURE_STORE_TABLE_NAME,
    ) -> None:
        self.db_path = Path(db_path) if db_path else FEATURE_STORE_DB_PATH
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise ValueError(f"Invalid table name: {table_name}")
        self.table_name = table_name

    def is_available(self) -> bool:
        """Check if the SQLite feature store database file exists and contains the expected table."""
        if not self.db_path.exists():
            return False
        try:
            with sqlite3.connect(str(self.db_path), timeout=2.0) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (self.table_name,),
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.warning(f"Feature store availability check failed: {e}")
            return False

    def get_record_count(self) -> int:
        """Return total applicant records in the feature store table."""
        if not self.db_path.exists():
            return 0
        try:
            with sqlite3.connect(str(self.db_path), timeout=2.0) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            logger.warning(f"Feature store count query failed: {e}")
            return 0

    def get_applicant_features(self, sk_id_curr: Optional[int]) -> Optional[Dict[str, Any]]:
        """
        Fetch historical features for a single applicant by SK_ID_CURR.

        Parameters
        ----------
        sk_id_curr : int or None
            Unique applicant loan ID.

        Returns
        -------
        Optional[Dict[str, Any]]
            Dictionary of feature column names to values, or None if not found or DB missing.
        """
        if sk_id_curr is None:
            return None

        if not self.db_path.exists():
            logger.warning(f"Feature store database file not found at {self.db_path}")
            return None

        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = f"SELECT * FROM {self.table_name} WHERE SK_ID_CURR = ? LIMIT 1"
                cursor.execute(query, (int(sk_id_curr),))
                row = cursor.fetchone()
                if row is None:
                    return None
                return dict(row)
        except sqlite3.OperationalError as e:
            logger.warning(f"Feature store operational error for applicant {sk_id_curr}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error querying feature store for applicant {sk_id_curr}: {e}")
            return None

    def get_batch_applicant_features(
        self, sk_id_currs: List[Optional[int]]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Batch-query historical features for multiple applicants using WHERE SK_ID_CURR IN (...).

        Parameters
        ----------
        sk_id_currs : List[Optional[int]]
            List of applicant IDs to query.

        Returns
        -------
        Dict[int, Dict[str, Any]]
            Mapping of SK_ID_CURR to historical feature dictionary.
        """
        if not sk_id_currs or not self.db_path.exists():
            return {}

        valid_ids = [int(i) for i in sk_id_currs if i is not None]
        if not valid_ids:
            return {}

        unique_ids = list(dict.fromkeys(valid_ids))
        results: Dict[int, Dict[str, Any]] = {}

        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in unique_ids)
                query = f"SELECT * FROM {self.table_name} WHERE SK_ID_CURR IN ({placeholders})"
                cursor.execute(query, unique_ids)
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    applicant_id = int(row_dict.get("SK_ID_CURR", 0))
                    results[applicant_id] = row_dict
            return results
        except sqlite3.OperationalError as e:
            logger.warning(f"Feature store operational error in batch query: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error batch-querying feature store: {e}")
            return {}


# Module-level singleton
_feature_store_instance: Optional[FeatureStore] = None


def get_feature_store(db_path: Optional[Union[str, Path]] = None) -> FeatureStore:
    """Return singleton FeatureStore instance."""
    global _feature_store_instance
    if _feature_store_instance is None or db_path is not None:
        _feature_store_instance = FeatureStore(db_path=db_path)
    return _feature_store_instance
