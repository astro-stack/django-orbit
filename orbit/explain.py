"""
On-demand query EXPLAIN (B2).

Runs a query plan for a captured SQL statement, on demand only (never on the recording
path). Vendor-aware (PostgreSQL / MySQL / SQLite) with graceful fallback. Plain ``EXPLAIN``
does not execute the statement; ``EXPLAIN ANALYZE`` does, so it is gated behind config and
only ever allowed for read-only ``SELECT`` statements, wrapped in a rolled-back savepoint.
"""

from typing import Any, Dict, List, Optional

from django.db import connections, transaction


def _is_select(sql: str) -> bool:
    return sql.lstrip().lower().startswith(("select", "with", "explain", "show", "pragma"))


def _build_explain_sql(vendor: str, sql: str, analyze: bool) -> Optional[str]:
    sql = sql.rstrip().rstrip(";")
    if vendor == "postgresql":
        opts = "ANALYZE, COSTS, FORMAT TEXT" if analyze else "COSTS, FORMAT TEXT"
        return "EXPLAIN ({}) {}".format(opts, sql)
    if vendor == "mysql":
        return "EXPLAIN ANALYZE {}".format(sql) if analyze else "EXPLAIN {}".format(sql)
    if vendor == "sqlite":
        # SQLite has no ANALYZE-style timing; the query plan is the useful artifact.
        return "EXPLAIN QUERY PLAN {}".format(sql)
    return None


def explain_query(
    sql: str,
    params: Any = None,
    analyze: bool = False,
    using: str = "default",
) -> Dict[str, Any]:
    """
    Return {'supported', 'vendor', 'analyze', 'plan' (list[str]) | 'error'}.

    Never raises: any failure is reported in 'error' so callers/UI can degrade gracefully.
    """
    result: Dict[str, Any] = {"supported": True, "analyze": False, "vendor": None}

    if not sql or not sql.strip():
        return {"supported": False, "error": "No SQL to explain"}

    connection = connections[using]
    vendor = connection.vendor
    result["vendor"] = vendor

    # ANALYZE executes the statement — only ever for read-only SELECTs.
    if analyze and not _is_select(sql):
        analyze = False
    result["analyze"] = analyze

    explain_sql = _build_explain_sql(vendor, sql, analyze)
    if explain_sql is None:
        return {"supported": False, "vendor": vendor, "error": "EXPLAIN not supported for this database"}

    # Params may have been serialized for storage and not be re-bindable; fall back to
    # running EXPLAIN without params (the plan rarely depends on literal values).
    def _run(bind_params):
        with connection.cursor() as cursor:
            cursor.execute(explain_sql, bind_params)
            rows = cursor.fetchall()
        return ["  ".join(str(c) for c in row) for row in rows]

    try:
        if analyze:
            # Extra safety: execute inside a savepoint we always roll back.
            with transaction.atomic(using=using):
                sid = transaction.savepoint(using=using)
                try:
                    plan = _run(params if isinstance(params, (list, tuple)) else None)
                finally:
                    transaction.savepoint_rollback(sid, using=using)
        else:
            try:
                plan = _run(params if isinstance(params, (list, tuple)) else None)
            except Exception:
                plan = _run(None)
        result["plan"] = plan
        return result
    except Exception as e:  # pragma: no cover - defensive
        return {"supported": True, "vendor": vendor, "analyze": analyze, "error": str(e)}
