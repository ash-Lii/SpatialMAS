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
