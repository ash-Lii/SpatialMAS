from __future__ import annotations

import json

from langchain.tools import tool

from spatialmas.services.analysis_service import AnalysisService
from spatialmas.services.query_service import QueryService
from spatialmas.services.schema_service import SchemaSelectionService
from spatialmas.services.sql_service import SQLGenerationService


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@tool
def select_relevant_schema(question: str) -> str:
    """Select relevant tables and columns for a natural-language question."""
    service = SchemaSelectionService()
    result = service.select_relevant_schema(question)
    return _json(result.to_dict())


@tool
def generate_sql_query(question: str, schema_string: str) -> str:
    """Generate Snowflake SQL from question + simplified schema string."""
    service = SQLGenerationService()
    sql = service.generate_sql(question=question, schema_string=schema_string)
    return sql


@tool
def execute_db_query(sql_query: str, limit: int = 1000) -> str:
    """Execute read-only SQL against Snowflake and return structured JSON result."""
    service = QueryService()
    result = service.execute_query(sql_query=sql_query, limit=limit)
    return _json(result.to_dict())


@tool
def analyze_query_result(data: str, analysis_type: str = "comprehensive") -> str:
    """Analyze query result rows encoded as JSON array."""
    service = AnalysisService()
    result = service.analyze_query_result(data=data, analysis_type=analysis_type)
    return _json(result)
