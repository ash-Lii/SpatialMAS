from __future__ import annotations

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute a read-only SQL query against Snowflake and print JSON output")
    parser.add_argument("sql_query", help='SQL text to run, for example: "SELECT * FROM ... LIMIT 10"')
    args = parser.parse_args()

    sql_query = args.sql_query.strip()
    if not sql_query:
        parser.error("sql_query cannot be empty")

    from spatialmas.services.query_service import QueryService

    result = QueryService().execute_query(sql_query=sql_query)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
