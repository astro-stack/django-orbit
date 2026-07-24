import asyncio

import pytest

pytestmark = pytest.mark.django_db


def test_family_hash_context_isolated_between_async_tasks():
    from orbit.handlers import get_current_family_hash, set_current_family_hash

    async def worker(family_hash):
        set_current_family_hash(family_hash)
        await asyncio.sleep(0)
        return get_current_family_hash()

    async def run_workers():
        return await asyncio.gather(worker("family-a"), worker("family-b"))

    result = asyncio.run(run_workers())

    assert result == ["family-a", "family-b"]
    assert get_current_family_hash() is None


def test_log_context_restores_parent_family_hash():
    from orbit.handlers import (
        OrbitLogContext,
        get_current_family_hash,
        set_current_family_hash,
    )

    set_current_family_hash("request-family")

    with OrbitLogContext("nested-operation"):
        assert get_current_family_hash() == "nested-operation"

    assert get_current_family_hash() == "request-family"
    set_current_family_hash(None)
