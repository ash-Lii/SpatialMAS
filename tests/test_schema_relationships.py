from spatialmas.schema.loader import get_schema_repository


def test_schema_repository_loads_tables_from_schema_file():
    repo = get_schema_repository()
    tables = repo.load_tables()

    assert tables, "expected at least one table in the LLM schema"
    assert repo.get_table("SAN_FRANCISCO_BIKESHARE", "BIKESHARE_TRIPS") is not None
