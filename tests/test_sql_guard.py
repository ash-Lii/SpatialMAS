from spatialmas.services.query_service import QueryService
from spatialmas.services.sql_service import SQLValidationService


def test_rejects_non_read_only_sql():
    try:
        SQLValidationService.validate_and_fix_sql("DELETE FROM t")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "read-only" in str(exc).lower() or "forbidden" in str(exc).lower()


def test_adds_limit_if_missing():
    sql = "SELECT * FROM SPATIAL_CORE.TRIPS"
    out = SQLValidationService.ensure_limit(sql, 1000)
    assert "LIMIT 1000" in out.upper()


def test_rewrites_year_between_to_microseconds():
    sql = 'SELECT * FROM t WHERE "start_date" BETWEEN 2014 AND 2017'
    result = SQLValidationService.validate_and_fix_sql(sql)
    assert "1388534400000000" in result.fixed_sql
    assert "1514764799999999" in result.fixed_sql


def test_retries_invalid_identifier_by_quoting_column():
    sql = 'SELECT start_date FROM SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS LIMIT 10'
    retry_sql, warning = QueryService._retry_invalid_identifier(
        sql,
        "000904 (42000): SQL compilation error: error line 1 at position 8 invalid identifier 'START_DATE'",
    )
    assert retry_sql == 'SELECT "start_date" FROM SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS LIMIT 10'
    assert warning == 'Retried query after quoting invalid identifier "start_date"'


def test_does_not_retry_when_identifier_is_already_quoted():
    sql = 'SELECT "start_date" FROM SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS LIMIT 10'
    retry_sql, warning = QueryService._retry_invalid_identifier(
        sql,
        "000904 (42000): SQL compilation error: error line 1 at position 8 invalid identifier 'START_DATE'",
    )
    assert retry_sql is None
    assert warning is None


def test_keeps_year_between_when_year_is_already_extracted():
    sql = (
        'SELECT EXTRACT(YEAR FROM TO_TIMESTAMP("start_date" / 1000000)) AS "year" '
        'FROM SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS '
        'WHERE EXTRACT(YEAR FROM TO_TIMESTAMP("start_date" / 1000000)) BETWEEN 2014 AND 2017'
    )
    result = SQLValidationService.validate_and_fix_sql(sql)
    assert "BETWEEN 2014 AND 2017" in result.fixed_sql
    assert "Converted year-based BETWEEN filter" not in " ".join(result.warnings)
