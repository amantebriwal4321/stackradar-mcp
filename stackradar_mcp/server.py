"""Streamable HTTP MCP server. This module is the runtime entry point.

``MCPServer`` comes from the official MCP Python SDK. ``serve`` calls
``run(transport="streamable-http")``, which is the hackathon's required
transport. Tool handlers return a short spoken line as text and the score
breakdown as structured content.
"""

from __future__ import annotations

import json
import os
from typing import Annotated

from pydantic import Field
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent
from mcp.types.version import HANDSHAKE_PROTOCOL_VERSIONS, LATEST_PROTOCOL_VERSION

from stackradar_mcp import __version__
from stackradar_mcp.catalog import TOOLS
from stackradar_mcp.service import compare_tools, tool_score, trending_tools, weekly_digest
from stackradar_mcp.signals import mode, seed_as_of

INSTRUCTIONS = (
    "StackRadar scores developer tools from 0 to 100 with the same absolute "
    "momentum formula as the StackRadar web app: GitHub stars 60 percent, "
    "forks 15 percent, and community mentions 25 percent. Mentions come from "
    "Hacker News, Dev.to, Reddit, and tech RSS. "
    "When you answer by voice, speak the tool result text. It is already a short "
    "spoken line. Do not read JSON, field names, or the numeric breakdown unless "
    "the person asks for the breakdown. "
    "trending_tools ranks a category. compare_tools compares two names. "
    "tool_score explains one tool. weekly_digest gives the leaders and who got "
    "louder in conversation this week. "
    "Categories: all, web, ai, data, cloud, devops, systems, security, web3. "
    "Windows: 24h, 7d, 30d. "
    "If a live source fails, the server uses a saved snapshot and says so."
)

mcp = MCPServer(
    "StackRadar",
    title="StackRadar MCP",
    description="Momentum scores for developer tools, written so a voice assistant can say them.",
    instructions=INSTRUCTIONS,
    website_url="https://github.com/amantebriwal4321/StackRadar",
    version=__version__,
)


def _result(payload: dict) -> CallToolResult:
    spoken = str(payload.get("spoken") or "I could not build a StackRadar answer.")
    return CallToolResult(
        content=[TextContent(type="text", text=spoken)],
        structured_content=payload,
        is_error=not payload.get("ok", True),
    )


@mcp.tool(name="trending_tools", title="Trending tools")
async def trending_tools_tool(
    category: Annotated[str, Field(description="all, web, ai, data, cloud, devops, systems, security, or web3")] = "all",
    window: Annotated[str, Field(description="24h, 7d, or 30d")] = "7d",
    limit: Annotated[int, Field(description="How many tools to return, from 1 to 10", ge=1, le=10)] = 5,
) -> CallToolResult:
    """Rank developer tools by StackRadar momentum for a category and time window.

    The text you get back is a short line meant to be spoken. The structured
    result has the scores.
    """
    return _result(await trending_tools(category=category, window=window, limit=limit))


@mcp.tool(name="compare_tools", title="Compare tools")
async def compare_tools_tool(
    a: Annotated[str, Field(description="First tool name or slug, for example FastAPI")],
    b: Annotated[str, Field(description="Second tool name or slug, for example Next.js")],
    window: Annotated[str, Field(description="24h, 7d, or 30d")] = "7d",
) -> CallToolResult:
    """Compare two developer tools and say which one leads, and why.

    The reason is the largest gap in the StackRadar breakdown: stars, forks,
    or community mentions.
    """
    return _result(await compare_tools(a=a, b=b, window=window))


@mcp.tool(name="tool_score", title="Tool score")
async def tool_score_tool(
    name: Annotated[str, Field(description="Tool name or slug, for example Ollama or fastapi")],
    window: Annotated[str, Field(description="24h, 7d, or 30d")] = "7d",
) -> CallToolResult:
    """Score one developer tool from 0 to 100 and return the StackRadar breakdown.

    Breakdown points are stars (60 percent), forks (15 percent), and community
    mentions (25 percent, saturating at 25 mentions).
    """
    return _result(await tool_score(name=name, window=window))


@mcp.tool(name="weekly_digest", title="Weekly digest")
async def weekly_digest_tool(
    category: Annotated[str, Field(description="all, web, ai, data, cloud, devops, systems, security, or web3")] = "all",
) -> CallToolResult:
    """Give a weekly voice briefing: score leaders, and who got louder in conversation.

    Leaders follow the momentum score. The riser is the tool with the biggest
    increase in community mentions versus the saved baseline, which is the part
    that actually moves inside a week.
    """
    return _result(await weekly_digest(category=category))


@mcp.resource("stackradar://catalog", mime_type="application/json", title="Tool catalog")
def catalog_resource() -> str:
    """Names, categories, and GitHub repos this server can score."""
    slim = [
        {
            "name": tool["name"],
            "slug": tool["slug"],
            "category": tool["category"],
            "github_repo": tool["github_repo"],
            "description": tool["description"],
        }
        for tool in TOOLS
    ]
    return json.dumps({"as_of": seed_as_of(), "tools": slim}, indent=2)


@mcp.prompt(title="Alexa briefing")
def alexa_briefing(question: str) -> str:
    """Instructions for answering one spoken StackRadar question on Alexa+."""
    return (
        "You are answering on Alexa+. Call the StackRadar tool that fits the question, "
        "then speak only the tool result text. It is already short enough to say aloud. "
        f"Question: {question}"
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "name": "StackRadar MCP",
            "version": __version__,
            "transport": "streamable-http",
            "path": "/mcp",
            "json_response": True,
            "stateless_http": True,
            "protocol_versions": list(HANDSHAKE_PROTOCOL_VERSIONS) + [LATEST_PROTOCOL_VERSION],
            "minimum_hackathon_protocol": "2025-11-25",
            "mode": mode(),
            "snapshot_as_of": seed_as_of(),
        }
    )


@mcp.custom_route("/", methods=["GET"])
async def index(_: Request) -> HTMLResponse:
    page = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>StackRadar MCP</title>
  <style>
    :root { color-scheme: light dark; }
    body { font-family: Georgia, "Iowan Old Style", serif; margin: 0; background: #f4f0e6; color: #1c1915; }
    main { max-width: 42rem; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }
    h1 { font-size: 2.2rem; line-height: 1.1; margin-bottom: 0.4rem; }
    p { line-height: 1.5; }
    code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.92rem; }
    ul { padding-left: 1.2rem; }
    .card { background: white; border: 1px solid #d9d1c3; border-radius: 12px; padding: 1rem 1.1rem; margin: 1rem 0; }
    a { color: #0b4f6c; }
    @media (prefers-color-scheme: dark) {
      body { background: #161410; color: #f3ecdf; }
      .card { background: #221f1a; border-color: #3a342c; }
      a { color: #8ecae6; }
    }
  </style>
</head>
<body>
  <main>
    <h1>StackRadar MCP</h1>
    <p>A voice-ready momentum desk for developer tools. Ask what is hot in AI this week, compare two libraries, or get a short weekly digest. Answers are scored with the same 0 to 100 formula as StackRadar, then shortened so Alexa+ can say them.</p>
    <div class="card">
      <p class="mono">Streamable HTTP endpoint</p>
      <p><a href="/mcp">/mcp</a></p>
      <p>Health: <a href="/health">/health</a></p>
    </div>
    <h2>Tools</h2>
    <ul>
      <li><strong>trending_tools</strong> for a category and a window</li>
      <li><strong>compare_tools</strong> for two names</li>
      <li><strong>tool_score</strong> for one name and the score breakdown</li>
      <li><strong>weekly_digest</strong> for leaders and who got louder</li>
    </ul>
    <p>Point any MCP host at this server, or run <span class="mono">python clients/demo_client.py</span> from the repo.</p>
  </main>
</body>
</html>"""
    return HTMLResponse(page)


def serve(host: str | None = None, port: int | None = None) -> None:
    """Bind Streamable HTTP. JSON responses and no session, so Lambda can host it."""
    bind_host = host or os.environ.get("STACKRADAR_HOST", "127.0.0.1")
    bind_port = port if port is not None else int(os.environ.get("STACKRADAR_PORT", "8741"))
    mcp.run(
        transport="streamable-http",
        host=bind_host,
        port=bind_port,
        json_response=True,
        stateless_http=True,
    )
