"""
On-demand query EXPLAIN.

Runs a query plan for a captured SQL statement, on demand only (never on the
recording path). Vendor-aware (PostgreSQL / MySQL / SQLite) with graceful
fallback.

Plain EXPLAIN does not execute the statement. EXPLAIN ANALYZE does execute SQL,
so Orbit only honors it for plain SELECT statements and wraps it in a rollback
scope. PostgreSQL also gets a transaction-level read-only guard.
"""

from typing import Any, Dict, Optional

from django.db import connections, transaction

from orbit.adapters import has_unbindable_param, rebind_params


def _is_select(sql: str) -> bool:
    return (
        sql.lstrip().lower().startswith(("select", "with", "explain", "show", "pragma"))
    )


def _is_analyzable_select(sql: str) -> bool:
    """ANALYZE executes SQL; only permit plain SELECT statements."""
    stripped = sql.strip().rstrip(";").lower()
    return stripped.startswith("select") and ";" not in stripped


def _is_dml(sql: str) -> bool:
    """True for INSERT/UPDATE/DELETE statements."""
    return sql.lstrip().lower().startswith(("insert", "update", "delete"))


def _build_explain_sql(vendor: str, sql: str, analyze: bool) -> Optional[str]:
    sql = sql.rstrip().rstrip(";")
    if vendor == "postgresql":
        opts = "ANALYZE, COSTS, FORMAT TEXT" if analyze else "COSTS, FORMAT TEXT"
        return "EXPLAIN ({}) {}".format(opts, sql)
    if vendor == "mysql":
        return "EXPLAIN ANALYZE {}".format(sql) if analyze else "EXPLAIN {}".format(sql)
    if vendor == "sqlite":
        return "EXPLAIN QUERY PLAN {}".format(sql)
    return None


def explain_query(
    sql: str,
    params: Any = None,
    analyze: bool = False,
    using: str = "default",
) -> Dict[str, Any]:
    """
    Return a dict with keys: supported, vendor, analyze, and plan or error.

    Never raises: failures are reported in error so callers/UI degrade cleanly.
    """
    result: Dict[str, Any] = {"supported": True, "analyze": False, "vendor": None}

    if not sql or not sql.strip():
        return {"supported": False, "error": "No SQL to explain"}

    conn = connections[using]
    vendor = conn.vendor
    result["vendor"] = vendor

    if analyze and not _is_analyzable_select(sql):
        analyze = False
    result["analyze"] = analyze

    params = rebind_params(params, conn)

    if _is_dml(sql) and not analyze and has_unbindable_param(params):
        return {
            "supported": True,
            "vendor": vendor,
            "analyze": False,
            "error": (
                "Can't EXPLAIN this statement: it has a JSON-typed parameter that was "
                "serialised for storage and can no longer be faithfully rebound. This "
                "is a limitation of replaying captured parameters, not a database or "
                "EXPLAIN support issue. Entries recorded after upgrading Orbit's "
                "recorder should not hit this; only older captured entries can."
            ),
        }

    explain_sql = _build_explain_sql(vendor, sql, analyze)
    if explain_sql is None:
        return {
            "supported": False,
            "vendor": vendor,
            "error": "EXPLAIN not supported for this database",
        }

    def _run(bind_params):
        with conn.cursor() as cursor:
            cursor.execute(explain_sql, bind_params)
            rows = cursor.fetchall()
        return ["  ".join(str(c) for c in row) for row in rows]

    bound = params if isinstance(params, (list, tuple, dict)) else None

    try:
        if analyze:
            with transaction.atomic(using=using):
                sid = transaction.savepoint(using=using)
                try:
                    if vendor == "postgresql":
                        with conn.cursor() as cursor:
                            cursor.execute("SET TRANSACTION READ ONLY")
                    plan = _run(bound)
                finally:
                    transaction.savepoint_rollback(sid, using=using)
        elif _is_dml(sql):
            plan = _run(bound)
        else:
            try:
                plan = _run(bound)
            except Exception:
                plan = _run(None)

        result["plan"] = plan
        return result

    except Exception as e:  # pragma: no cover - defensive
        return {
            "supported": True,
            "vendor": vendor,
            "analyze": analyze,
            "error": str(e),
        }
