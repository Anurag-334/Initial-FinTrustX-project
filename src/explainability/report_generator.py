"""
==========================================
Report Generator

Saves explainability reports.

Author: Anurag Kashyap
==========================================
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Save explainability reports.
    """
    def __init__(self,output_dir: str = "reports/explainability",):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_csv(self,dataframe: pd.DataFrame,filename: str,) -> Path:
        output_path = self.output_dir / filename

        dataframe.to_csv(output_path,index=False,)

        logger.info(f"CSV saved to {output_path}")

        return output_path
    def save_json(self,dataframe: pd.DataFrame,filename: str,) -> Path:
        output_path = self.output_dir / filename

        with open(output_path,"w",encoding="utf-8",) as file:

            json.dump(dataframe.to_dict(orient="records"),file,indent=4,)

        logger.info(f"JSON saved to {output_path}")

        return output_path
    def save_html(self,dataframe: pd.DataFrame,filename: str,) -> Path:
        output_path = self.output_dir / filename

        dataframe.to_html(output_path,index=False,)

        logger.info(f"HTML saved to {output_path}")

        return output_path
    def save_summary(self,summary: dict,filename: str = "summary.json",) -> Path:
        output_path = self.output_dir / filename

        with open(output_path,"w",encoding="utf-8",) as file:

            json.dump(summary,file,indent=4,)

        logger.info(f"Summary saved to {output_path}")

        return output_path