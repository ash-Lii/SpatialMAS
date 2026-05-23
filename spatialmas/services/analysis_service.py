from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd


class AnalysisService:
    def analyze_query_result(self, data: str, analysis_type: str = "comprehensive") -> dict[str, Any]:
        rows = json.loads(data)
        if not isinstance(rows, list):
            raise ValueError("data must be a JSON array of row objects")

        if not rows:
            return {
                "row_count": 0,
                "columns": [],
                "insights": ["No rows returned"],
                "recommendations": [],
            }

        df = pd.DataFrame(rows)
        result: dict[str, Any] = {
            "row_count": len(df),
            "columns": list(df.columns),
            "insights": [],
            "recommendations": [],
        }

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

        if analysis_type in {"basic", "comprehensive"} and numeric_cols:
            stats = {}
            for col in numeric_cols:
                desc = df[col].describe()
                stats[col] = {
                    "count": int(desc["count"]),
                    "mean": float(desc["mean"]),
                    "min": float(desc["min"]),
                    "p50": float(desc["50%"]),
                    "max": float(desc["max"]),
                }
            result["descriptive_stats"] = stats

        if analysis_type in {"statistical", "comprehensive"} and len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr().round(4).fillna(0)
            result["correlation_matrix"] = corr.to_dict()

        if analysis_type in {"trend", "comprehensive"} and numeric_cols and len(df) >= 3:
            trend = {}
            for col in numeric_cols:
                y = df[col].to_numpy(dtype=float)
                x = np.arange(len(y))
                coeff = np.polyfit(x, y, 1)
                trend[col] = {"slope": float(coeff[0]), "intercept": float(coeff[1])}
            result["trend"] = trend

        if categorical_cols:
            focus = categorical_cols[:3]
            result["categorical_summary"] = {
                col: {"unique": int(df[col].nunique(dropna=True))} for col in focus
            }

        if not result["insights"]:
            result["insights"].append("Analysis completed")

        if len(df) < 30:
            result["recommendations"].append("Sample size is small; consider broader query scope")

        return result
