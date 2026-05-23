from __future__ import annotations

from spatialmas.schema.loader import get_schema_repository


def main() -> None:
    repo = get_schema_repository()
    tables = repo.load_tables()
    if not tables:
        raise SystemExit("schema/schema.txt did not contain any tables")

    print(f"schema validation passed: {len(tables)} tables")


if __name__ == "__main__":
    main()
