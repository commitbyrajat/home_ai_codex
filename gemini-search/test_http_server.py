"""Run via: docker compose exec -T gemini-search python - < gemini-search/test_http_server.py."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import http_server as server


class EngineStartupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        server._engine = None
        server._engine_lock = asyncio.Lock()
        self.environment = patch.dict(os.environ, HEADLESS="1", GEMINI_SEARCH_USER_DATA_DIR="")
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(setattr, server, "_engine", None)

    async def test_failed_start_is_not_cached_and_next_call_retries(self):
        failed = AsyncMock()
        failed.start.side_effect = RuntimeError("CDP unavailable")
        healthy = AsyncMock()
        with patch.object(server, "AIModeEngine", side_effect=[failed, healthy]):
            with self.assertRaisesRegex(RuntimeError, "CDP unavailable"):
                await server.get_engine()
            self.assertIsNone(server._engine)
            self.assertIs(await server.get_engine(), healthy)
            healthy.start.assert_awaited_once()

    async def test_concurrent_calls_share_one_successfully_started_engine(self):
        engine = AsyncMock()
        with patch.object(server, "AIModeEngine", return_value=engine) as factory:
            results = await asyncio.gather(server.get_engine(), server.get_engine())
        self.assertTrue(all(result is engine for result in results))
        factory.assert_called_once()
        engine.start.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
