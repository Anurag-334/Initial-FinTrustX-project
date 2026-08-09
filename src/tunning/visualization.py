"""
=========================================================
Optuna Visualization Utilities
=========================================================

Author : Anurag Kashyap
=========================================================
"""

from __future__ import annotations

from os import name
from pathlib import Path

import optuna
from optuna import study
import plotly.io as pio

import logging
import pandas as pd


from optuna.visualization import (
    plot_optimization_history,
    plot_param_importances,
    plot_parallel_coordinate,
    plot_contour,
    plot_slice,
    plot_edf,
)

from plotly.graph_objs import Figure

logger = logging.getLogger(__name__)


class OptunaVisualizer:
    """
    Generates and persists interactive Optuna diagnostic plots for a
    completed (or in-progress) study.

    Every plot method returns a plotly Figure so it can be shown inline
    in a notebook (`fig.show()`) or saved to disk via `save_figure`.
    """

    def __init__(self, output_dir="reports/optuna"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Individual plots
    # ------------------------------------------------------------------
    def optimization_history(self, study:optuna.Study,):
        return plot_optimization_history(study)

    def parameter_importance(self, study):
        return plot_param_importances(study)

    def parallel_coordinate(self, study):
        return plot_parallel_coordinate(study)

    def contour_plot(self, study):
        return plot_contour(study)

    def slice_plot(self, study):
        return plot_slice(study)

    def edf_plot(self, study: optuna.Study)-> Figure:
        return plot_edf(study)

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------
    def save_figure(self, fig, filename, also_png=True):
        """
        Saves an interactive HTML file, and — when possible — a static
        PNG alongside it (same basename), so plots can be dropped
        straight into a report, slide deck, or README.

        PNG export requires the optional `kaleido` package. If it isn't
        installed, the PNG is skipped with a warning instead of raising,
        so `save_all_plots` never fails just because a static image
        couldn't be produced.
        """
        html_path = self.output_dir / filename
        pio.write_html(fig, html_path)

        if also_png:
            png_path = html_path.with_suffix(".png")
            try:
                pio.write_image(fig, png_path)
            except Exception as exc:  # e.g. kaleido not installed
                logger.warning(
                    f"[OptunaVisualizer] Skipped PNG export for "
                    f"{filename} ({exc}). Install `kaleido` to enable it."
                )

        return html_path

    def save_all_plots(self, study):
        """
        Generates and saves the full diagnostic suite for a single study:

            reports/optuna/
                optimization_history.html / .png
                parameter_importance.html / .png
                parallel_coordinate.html  / .png
                contour.html              / .png
                slice.html                / .png
                edf.html                  / .png
        """
        plots = {
            "optimization_history.html": self.optimization_history(study),
            "parameter_importance.html": self.parameter_importance(study),
            "parallel_coordinate.html": self.parallel_coordinate(study),
            "contour.html": self.contour_plot(study),
            "slice.html": self.slice_plot(study),
            "edf.html": self.edf_plot(study),
        }

        saved_paths = {}
        for filename, fig in plots.items():
            saved_paths[filename] = self.save_figure(fig, filename)

        return saved_paths

    # ------------------------------------------------------------------
    # Cross-model comparison
    # ------------------------------------------------------------------
    def compare_studies(self, studies: dict[str, optuna.Study]):
        """
        Prints a quick leaderboard-style summary across multiple studies,
        e.g. one per model family (Random Forest, XGBoost, CatBoost,
        Neural Network, ...).
        """
        leaderboard = self.leaderboard(studies)
        for _, row in leaderboard.iterrows():
            logger.info("=" * 50)
            logger.info(f"Model : {row['model']}")
            logger.info(f"Best Score : {row['best_score']:.5f}")
            logger.info(f"Best Trial : {row['best_trial']}")

    def best_parameters(self,study: optuna.Study,):
        return study.best_params

    def leaderboard(self, studies: dict[str, optuna.Study]):
        """
        Returns a leaderboard-style summary across multiple studies,
        e.g. one per model family (Random Forest, XGBoost, CatBoost,
        Neural Network, ...).
        """
        leaderboard = []
        for name, study in studies.items():
            leaderboard.append(
                {
                    "model": name,
                    "best_score": study.best_value,
                    "best_trial": study.best_trial.number,
                    "best_params": study.best_params,
                }
            )
        return pd.DataFrame(leaderboard).sort_values(by="best_score", ascending=False)
    