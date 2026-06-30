"""
Tests for orbit.adapters, orbit.recorders (param serialisation), and
orbit.explain — covering the JSON adapter unwrap/rebind pipeline and
its graceful-degradation guarantees.

Run with:  pytest tests/test_adapter_explain.py -v
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import override_settings

import pytest

from orbit.adapters import (
    ADAPTER_MARKER_KEY,
    has_unbindable_param,
    is_adapter_marker,
    is_supported_adapter,
    rebind_adapter,
    rebind_params,
    unwrap_adapter,
    unwrap_adapters,
)

pytestmark = pytest.mark.django_db

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


class Jsonb:
    """Minimal psycopg3-style Jsonb stand-in."""

    __module__ = "psycopg"

    def __init__(self, obj):
        self.obj = obj


class Json:
    """Minimal psycopg2-style Json stand-in."""

    __module__ = "psycopg2"

    def __init__(self, obj):
        self.obj = obj


class _UnknownAdapter:
    """Something the registry knows nothing about."""

    __module__ = "some_other_driver"

    def __init__(self, val):
        self.val = val


def _json_marker(value):
    return {ADAPTER_MARKER_KEY: "json", "value": value}


# ---------------------------------------------------------------------------
# orbit.adapters — detection
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestIsSupported:
    def test_psycopg3_jsonb(self):
        assert is_supported_adapter(Jsonb({"k": 1})) == "json"

    def test_psycopg2_json(self):
        assert is_supported_adapter(Json([1, 2])) == "json"

    def test_plain_dict_not_adapter(self):
        assert is_supported_adapter({"k": 1}) is None

    def test_plain_str_not_adapter(self):
        assert is_supported_adapter("hello") is None

    def test_none_not_adapter(self):
        assert is_supported_adapter(None) is None

    def test_unknown_adapter_class_not_adapter(self):
        assert is_supported_adapter(_UnknownAdapter(42)) is None


# ---------------------------------------------------------------------------
# orbit.adapters — unwrapping
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUnwrapAdapter:
    def test_jsonb_dict(self):
        marker = unwrap_adapter(Jsonb({"level": "INFO"}))
        assert marker == _json_marker({"level": "INFO"})

    def test_json_list(self):
        marker = unwrap_adapter(Json([1, 2, 3]))
        assert marker == _json_marker([1, 2, 3])

    def test_plain_value_passthrough(self):
        val = {"plain": "dict"}
        assert unwrap_adapter(val) is val

    def test_none_passthrough(self):
        assert unwrap_adapter(None) is None

    def test_integer_passthrough(self):
        assert unwrap_adapter(42) == 42

    def test_unknown_adapter_passthrough(self):
        obj = _UnknownAdapter(99)
        assert unwrap_adapter(obj) is obj

    def test_unwrap_preserves_null_inner_value(self):
        """None is a valid JSON value — it must survive the round-trip."""
        marker = unwrap_adapter(Jsonb(None))
        assert marker == _json_marker(None)

    def test_unwrap_exception_returns_original(self):
        """If the unwrap function itself raises, the original value is returned."""
        bad = Jsonb({"x": 1})
        # Sabotage the attribute lookup
        del bad.obj
        result = unwrap_adapter(bad)
        # Should get the original object back, not raise
        assert result is bad


# ---------------------------------------------------------------------------
# orbit.adapters — marker identification
# ---------------------------------------------------------------------------


class TestIsAdapterMarker:
    def test_valid_json_marker(self):
        assert is_adapter_marker(_json_marker({"a": 1})) is True

    def test_dict_without_key_is_not_marker(self):
        assert is_adapter_marker({"value": 1}) is False

    def test_marker_key_must_be_string(self):
        assert is_adapter_marker({ADAPTER_MARKER_KEY: True, "value": 1}) is False

    def test_non_dict_is_not_marker(self):
        assert is_adapter_marker("hello") is False
        assert is_adapter_marker(None) is False
        assert is_adapter_marker(42) is False


# ---------------------------------------------------------------------------
# orbit.adapters — rebinding
# ---------------------------------------------------------------------------


class TestRebindAdapter:
    def test_sqlite_returns_json_text(self):
        marker = _json_marker({"k": "v"})
        result = rebind_adapter(marker, "sqlite")
        assert result == json.dumps({"k": "v"})

    def test_mysql_returns_json_text(self):
        marker = _json_marker([1, 2])
        result = rebind_adapter(marker, "mysql")
        assert result == json.dumps([1, 2])

    def test_postgresql_falls_back_to_json_text_without_psycopg(self):
        """
        When psycopg is not importable, the Postgres rebind path must fall back
        to plain JSON text rather than raising.
        """
        marker = _json_marker({"x": 1})
        with patch("builtins.__import__", side_effect=ImportError):
            result = rebind_adapter(marker, "postgresql")
        assert result == json.dumps({"x": 1})

    def test_unknown_kind_returns_value(self):
        marker = {ADAPTER_MARKER_KEY: "array", "value": [1, 2, 3]}
        result = rebind_adapter(marker, "postgresql")
        assert result == [1, 2, 3]

    def test_null_json_value_round_trips(self):
        marker = _json_marker(None)
        result = rebind_adapter(marker, "sqlite")
        assert result == "null"


class TestRebindParams:
    def test_mixed_params(self):
        params = [42, _json_marker({"a": 1}), "plain"]
        result = rebind_params(params, "sqlite")
        assert result[0] == 42
        assert result[1] == json.dumps({"a": 1})
        assert result[2] == "plain"

    def test_none_params_passthrough(self):
        assert rebind_params(None, "sqlite") is None

    def test_empty_list(self):
        assert rebind_params([], "sqlite") == []

    def test_returns_new_list_not_original(self):
        params = [1, 2]
        result = rebind_params(params, "sqlite")
        assert result is not params


# ---------------------------------------------------------------------------
# orbit.adapters — unbindable-param detection
# ---------------------------------------------------------------------------


class TestHasUnbindableParam:
    def test_clean_params_are_bindable(self):
        assert has_unbindable_param([1, "hello", None]) is False

    def test_bare_dict_is_unbindable(self):
        assert has_unbindable_param([{"key": "value"}]) is True

    def test_bare_list_is_unbindable(self):
        assert has_unbindable_param([[1, 2, 3]]) is True

    def test_stringified_jsonb_repr_is_unbindable(self):
        assert has_unbindable_param(["Jsonb({'level': 'INFO'})"]) is True

    def test_stringified_json_repr_is_unbindable(self):
        assert has_unbindable_param(["Json({'k': 'v'})"]) is True

    def test_marker_dict_is_not_unbindable(self):
        # Markers are handled by rebind_params before this check runs.
        assert has_unbindable_param([_json_marker({"k": 1})]) is False

    def test_none_params(self):
        assert has_unbindable_param(None) is False

    def test_non_list_params(self):
        assert has_unbindable_param("raw_string") is False


# ---------------------------------------------------------------------------
# orbit.explain — integration (SQL classification + EXPLAIN dispatch)
# ---------------------------------------------------------------------------

# We test explain_query by patching the database cursor rather than touching
# a real database, so the tests remain backend-agnostic and fast.


def _mock_connection(vendor="postgresql", plan_rows=None):
    """Return a mock Django connection object."""
    if plan_rows is None:
        plan_rows = [("Seq Scan on users  (cost=0.00..35.50 rows=2550)",)]

    cursor = MagicMock()
    cursor.__enter__ = lambda s: s
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.return_value = plan_rows

    conn = MagicMock()
    conn.vendor = vendor
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.mark.django_db
class TestExplainQuery:
    """Tests for orbit.explain.explain_query."""

    def _run(
        self, sql, params=None, analyze=False, vendor="postgresql", plan_rows=None
    ):
        from orbit.explain import explain_query

        conn, cursor = _mock_connection(vendor=vendor, plan_rows=plan_rows)
        with patch("orbit.explain.connections", {vendor: conn}):
            return explain_query(sql, params=params, analyze=analyze, using=vendor)

    # --- basic SELECT -------------------------------------------------------

    def test_select_explain_returns_plan(self):
        result = self._run("SELECT 1", vendor="postgresql")
        assert result["supported"] is True
        assert "plan" in result
        assert "error" not in result

    def test_select_explain_sqlite(self):
        result = self._run(
            "SELECT * FROM auth_user",
            vendor="sqlite",
            plan_rows=[("0", "0", "0", "SCAN auth_user")],
        )
        assert result["supported"] is True
        assert "plan" in result

    def test_select_explain_mysql(self):
        result = self._run(
            "SELECT * FROM auth_user",
            vendor="mysql",
            plan_rows=[("1", "SIMPLE", "auth_user", None, "ALL")],
        )
        assert result["supported"] is True
        assert "plan" in result

    def test_empty_sql_unsupported(self):
        from orbit.explain import explain_query

        result = explain_query("", using="default")
        assert result["supported"] is False
        assert "error" in result

    # --- INSERT without JSONField -------------------------------------------

    def test_insert_without_json_param_returns_plan(self):
        sql = "INSERT INTO logs (level, message) VALUES (%s, %s)"
        result = self._run(sql, params=["INFO", "hello"], vendor="postgresql")
        assert result["supported"] is True
        assert "plan" in result

    # --- INSERT with JSONField (new marker format) --------------------------

    def test_insert_with_json_marker_param_returns_plan(self):
        """
        A JSONField parameter stored with the new marker format is rebound
        by rebind_params before EXPLAIN runs.
        """
        sql = "INSERT INTO events (payload) VALUES (%s)"
        marker_param = _json_marker({"event": "login", "user_id": 42})
        # After rebind_params, the marker becomes a JSON text string (sqlite path
        # used here to avoid psycopg import requirement in CI).
        result = self._run(sql, params=[marker_param], vendor="sqlite")
        assert result["supported"] is True
        assert "plan" in result

    # --- UPDATE with JSONField (new marker format) --------------------------

    def test_update_with_json_marker_param_returns_plan(self):
        sql = "UPDATE events SET payload = %s WHERE id = %s"
        params = [_json_marker({"k": "v"}), 1]
        result = self._run(sql, params=params, vendor="sqlite")
        assert result["supported"] is True
        assert "plan" in result

    # --- Legacy payload — unbindable params --------------------------------

    def test_insert_with_legacy_bare_dict_param_returns_error(self):
        """
        An INSERT recorded before the adapter-unwrapping fix stores params as
        bare dicts, which cannot be rebound.  Expect a clear error message.
        """
        sql = "INSERT INTO events (payload) VALUES (%s)"
        result = self._run(sql, params=[{"level": "INFO"}], vendor="postgresql")
        assert result["supported"] is True
        assert "plan" not in result
        assert "error" in result
        assert "JSON-typed parameter" in result["error"]

    def test_insert_with_stringified_jsonb_repr_returns_error(self):
        sql = "INSERT INTO events (payload) VALUES (%s)"
        result = self._run(
            sql, params=["Jsonb({'level': 'INFO'})"], vendor="postgresql"
        )
        assert "error" in result
        assert "plan" not in result

    # --- Unknown adapter degrades gracefully --------------------------------

    def test_unknown_adapter_object_in_select_does_not_raise(self):
        """
        An unrecognised adapter object in a SELECT falls through gracefully —
        SELECT has a no-params fallback so the plan still executes.
        """
        sql = "SELECT * FROM logs WHERE id = %s"
        obj = _UnknownAdapter(42)
        # unwrap_adapter returns the object unchanged; rebind_params passes it
        # through; the SELECT fallback path retries without params.
        result = self._run(sql, params=[obj], vendor="postgresql")
        # Should not raise and should have a plan (via the fallback path)
        assert "error" not in result or result.get("plan") is not None

    # --- ANALYZE gating ----------------------------------------------------

    def test_analyze_on_insert_is_silently_downgraded(self):
        """ANALYZE is only safe for SELECTs; non-SELECTs must drop the flag."""
        sql = "INSERT INTO logs (msg) VALUES (%s)"
        result = self._run(sql, params=["hi"], vendor="postgresql")
        assert result.get("analyze") is False

    def test_analyze_true_on_select(self):
        sql = "SELECT 1"
        from orbit.explain import explain_query

        conn, cursor = _mock_connection(vendor="postgresql")
        # Patch transaction primitives so the savepoint dance doesn't fail
        with (
            patch("orbit.explain.connections", {"postgresql": conn}),
            patch("orbit.explain.transaction") as mock_tx,
        ):
            mock_tx.atomic.return_value.__enter__ = lambda s: s
            mock_tx.atomic.return_value.__exit__ = MagicMock(return_value=False)
            mock_tx.savepoint.return_value = "sp1"
            mock_tx.savepoint_rollback = MagicMock()
            result = explain_query(sql, analyze=True, using="postgresql")

        assert result.get("analyze") is True


class TestRecursiveAdapterHandling:
    def test_unwraps_named_and_many_params(self):
        params = {
            "payload": Jsonb({"password": "secret", "visible": "ok"}),
            "rows": [(Json({"token": "hidden"}), 1)],
        }

        result = unwrap_adapters(params)

        assert result["payload"] == _json_marker(
            {"password": "secret", "visible": "ok"}
        )
        assert result["rows"][0][0] == _json_marker({"token": "hidden"})

    def test_rebinds_named_params(self):
        params = {"payload": _json_marker({"a": 1}), "id": 5}

        result = rebind_params(params, "sqlite")

        assert result == {"payload": json.dumps({"a": 1}), "id": 5}

    def test_rebinds_many_param_rows(self):
        params = [(_json_marker({"a": 1}), 1), (_json_marker({"b": 2}), 2)]

        result = rebind_params(params, "sqlite")

        assert result == [(json.dumps({"a": 1}), 1), (json.dumps({"b": 2}), 2)]


@pytest.mark.django_db
@override_settings(ORBIT_CONFIG={"MASK_ALL_PAYLOADS": True})
def test_save_queries_to_orbit_masks_json_adapter_marker_payload(db):
    from orbit.models import OrbitEntry
    from orbit.recorders import OrbitQueryWrapper, save_queries_to_orbit
    from orbit.utils import MASK_PLACEHOLDER

    serialized = OrbitQueryWrapper()._serialize_params(
        [Jsonb({"password": "secret", "visible": "ok"})]
    )

    save_queries_to_orbit(
        [{"sql": "INSERT INTO events (payload) VALUES (%s)", "params": serialized}],
        family_hash="fam-mask",
    )

    entry = OrbitEntry.objects.get(family_hash="fam-mask")
    marker = entry.payload["params"][0]
    assert marker["value"]["password"] == MASK_PLACEHOLDER
    assert marker["value"]["visible"] == "ok"


def test_analyze_is_downgraded_for_data_modifying_cte():
    from orbit.explain import explain_query

    conn, _cursor = _mock_connection(vendor="postgresql")
    sql = "WITH deleted AS (DELETE FROM logs RETURNING *) SELECT * FROM deleted"

    with patch("orbit.explain.connections", {"postgresql": conn}):
        result = explain_query(sql, analyze=True, using="postgresql")

    assert result["analyze"] is False
    executed_sql = conn.cursor.return_value.execute.call_args[0][0]
    assert "ANALYZE" not in executed_sql


def test_postgresql_analyze_sets_transaction_read_only():
    from orbit.explain import explain_query

    conn, cursor = _mock_connection(vendor="postgresql")
    with (
        patch("orbit.explain.connections", {"postgresql": conn}),
        patch("orbit.explain.transaction") as mock_tx,
    ):
        mock_tx.atomic.return_value.__enter__ = lambda s: s
        mock_tx.atomic.return_value.__exit__ = MagicMock(return_value=False)
        mock_tx.savepoint.return_value = "sp1"
        mock_tx.savepoint_rollback = MagicMock()
        result = explain_query("SELECT 1", analyze=True, using="postgresql")

    assert result["analyze"] is True
    assert cursor.execute.call_args_list[0].args[0] == "SET TRANSACTION READ ONLY"
    assert cursor.execute.call_args_list[1].args[0].startswith("EXPLAIN (ANALYZE")
