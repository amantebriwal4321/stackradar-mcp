import socket
import threading
import time

import httpx
import pytest
from mcp import Client
from mcp.types.version import LATEST_PROTOCOL_VERSION

from stackradar_mcp.server import health, mcp, serve


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.anyio
async def test_in_memory_client_calls_every_tool():
    async with Client(mcp) as client:
        version = client.protocol_version
        assert version >= "2025-11-25" or version == LATEST_PROTOCOL_VERSION
        listed = await client.list_tools()
        names = {tool.name for tool in listed.tools}
        assert names == {"trending_tools", "compare_tools", "tool_score", "weekly_digest"}
        for name, arguments in (
            ("trending_tools", {"category": "web", "window": "7d", "limit": 2}),
            ("tool_score", {"name": "ollama"}),
            ("compare_tools", {"a": "react", "b": "svelte"}),
            ("weekly_digest", {"category": "ai"}),
        ):
            result = await client.call_tool(name, arguments)
            assert result.is_error is False
            assert result.content[0].text
            assert result.structured_content["ok"] is True
            assert result.structured_content["spoken"] == result.content[0].text


@pytest.mark.anyio
async def test_prompt_and_catalog_resource():
    async with Client(mcp) as client:
        prompts = await client.list_prompts()
        assert any(prompt.name == "alexa_briefing" for prompt in prompts.prompts)
        rendered = await client.get_prompt("alexa_briefing", {"question": "What is hot in AI?"})
        text = rendered.messages[0].content
        if not isinstance(text, str):
            text = text.text
        assert "Alexa" in text
        resource = await client.read_resource("stackradar://catalog")
        body = resource.contents[0].text
        assert "fastapi" in body


def test_lambda_app_exposes_mcp_and_health():
    from stackradar_mcp.lambda_handler import app, handler

    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/mcp" in paths
    assert "/health" in paths
    assert handler is not None


def test_health_lists_the_hackathon_protocol():
    class Dummy:
        pass

    import asyncio

    response = asyncio.run(health(Dummy()))  # type: ignore[arg-type]
    payload = response.body.decode()
    assert "2025-11-25" in payload
    assert "streamable-http" in payload


def test_streamable_http_client_round_trip():
    port = _free_port()
    thread = threading.Thread(target=lambda: serve(host="127.0.0.1", port=port), daemon=True)
    thread.start()
    deadline = time.time() + 15
    health_url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        try:
            response = httpx.get(health_url, timeout=1)
            if response.status_code == 200 and "2025-11-25" in response.text:
                break
        except httpx.HTTPError:
            time.sleep(0.15)
    else:
        pytest.fail("server did not open /health")

    async def exercise() -> None:
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            assert "2025-11-25" <= client.protocol_version or client.protocol_version == LATEST_PROTOCOL_VERSION
            result = await client.call_tool("tool_score", {"name": "FastAPI", "window": "7d"})
            assert "FastAPI" in result.content[0].text
            digest = await client.call_tool("weekly_digest", {})
            assert "Ollama" in digest.content[0].text

    import anyio

    anyio.run(exercise)
