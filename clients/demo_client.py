"""Call every StackRadar tool over Streamable HTTP and print the spoken line.

Start the server first:

    STACKRADAR_MODE=seed STACKRADAR_PORT=8741 stackradar-mcp

Then:

    python clients/demo_client.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp import Client

URL = os.environ.get("STACKRADAR_MCP_URL", "http://127.0.0.1:8741/mcp")

CALLS: list[tuple[str, dict]] = [
    ("trending_tools", {"category": "ai", "window": "7d", "limit": 3}),
    ("tool_score", {"name": "fastapi", "window": "7d"}),
    ("compare_tools", {"a": "fastapi", "b": "nextjs", "window": "7d"}),
    ("weekly_digest", {}),
]


def _spoken(result) -> str:
    chunks = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


async def main() -> int:
    print(f"connecting to {URL}")
    async with Client(URL) as client:
        print(f"protocol {client.protocol_version}")
        print(f"server {client.server_info.name} {client.server_info.version}")
        listed = await client.list_tools()
        names = [tool.name for tool in listed.tools]
        print("tools:", ", ".join(names))
        missing = [name for name, _ in CALLS if name not in names]
        if missing:
            print("missing tools:", ", ".join(missing))
            return 1
        failed = False
        for name, arguments in CALLS:
            result = await client.call_tool(name, arguments)
            spoken = _spoken(result)
            source = ""
            if isinstance(result.structured_content, dict):
                source = result.structured_content.get("data_source") or ""
            print(f"\n== {name} ==")
            if source:
                print(f"data: {source}")
            print(spoken or "(empty)")
            if result.is_error or not spoken:
                failed = True
        return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:  # noqa: BLE001 - the demo should say what failed
        print(f"demo client failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
