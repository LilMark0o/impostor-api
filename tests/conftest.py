from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.pick_word.return_value = "perro"
    llm.pick_hint.return_value = "fiel"
    llm.pick_mirror_word.return_value = "gato"
    return llm


@pytest.fixture
def mock_messaging():
    msg = AsyncMock()
    msg.send.return_value = True
    return msg
