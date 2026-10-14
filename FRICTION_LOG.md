# Friction log

Built while wiring StackRadar MCP for the Alexa+ track of Build, Ship, Shape. Each entry is something that actually happened in this repo, with the workaround that shipped.

Hackathon form fields, if you paste these in: task, steps, expected, actual, severity, workaround, suggestion.

## 1. Alexa+ has no door for a self hosted MCP server

Severity: Critical

Task: Attach this MCP server to Alexa+ the way the quickstart describes, so the demo video could show a real device or the Amazon web simulator.

Steps: Read the Alexa+ MCP quickstart (JSON-RPC over Streamable HTTP, then `alexa-ai` to scaffold and deploy an add-on). Read the hackathon FAQ and the rules page for the Alexa+ track.

Expected: A developer account could register a public MCP URL and try it in a simulator.

Actual: The FAQ says the Alexa AI CLI, MCP Toolkit, Category SDK, and web simulator are select partner preview, and participants cannot apply. The quickstart still tells you to run `alexa-ai new mcp`. Those two pages disagree. There is no console step I can complete.

Workaround: Ship a self hosted Streamable HTTP server and a real MCP client (`clients/demo_client.py`) that calls `initialize`, lists tools, and calls each tool. That is the path the FAQ says counts.

Suggestion: Publish one page that says "partner preview is closed, here is the request shape we will accept, here is a hosted simulator that can point at your URL." Keep the quickstart from sending people into a CLI they cannot install.

## 2. Official MCP Python SDK v2 does not match the v1 snippets

Severity: Important

Task: Stand up a Streamable HTTP server with the official `mcp` package and bind it to a port.

Steps: `pip install mcp` (resolved to 2.3.0). Followed older FastMCP examples that pass `host`, `port`, `stateless_http`, and `json_response` into the constructor, then call `run(transport="streamable-http")`.

Expected: The constructor would accept the transport settings, as the v1 docs and most blog posts still show.

Actual: `MCPServer` (the v2 name; `FastMCP` is the old one) rejects those keywords. Host, port, JSON responses, and stateless mode belong on `run()` or on `streamable_http_app()`. `LATEST_PROTOCOL_VERSION` is now `2026-07-28`, and the initialize handshake tops out at `2025-11-25`. Using the old constant in a hand-built initialize request would negotiate a version the handshake cannot offer.

Workaround: `from mcp.server import MCPServer`, then `mcp.run(transport="streamable-http", host=..., port=..., json_response=True, stateless_http=True)`. Tests assert the negotiated version is `2025-11-25` or later.

Suggestion: Keep a short "if your snippet says FastMCP, read this" box at the top of the getting started page. The migration guide is good. The old snippets are what search returns first.

## 3. Lambda buffered URLs and the SDK's localhost host check

Severity: Important

Task: Put the same server behind an AWS Lambda Function URL with SAM, which is the deploy path in `template.yaml`.

Steps: Read the SDK deploy notes and `streamable_http_app` in the installed 2.3.0 package. Compared that with a buffered Function URL, which returns one response body and does not stream SSE.

Expected: The default Streamable HTTP app could sit behind the function URL.

Actual: Two separate mismatches.

* Default responses are an SSE stream. A buffered Function URL will not carry that. `json_response=True` returns one JSON body instead.
* On the 2025-11-25 path the server keeps a session id in memory unless `stateless_http=True`. A second warm container would 404 the session.
* If the app is built with the default host `127.0.0.1`, DNS rebinding protection turns on and allows only localhost Host headers. A function URL host would get HTTP 421.

Workaround: `lambda_handler.py` builds the app with `json_response=True`, `stateless_http=True`, and `host="0.0.0.0"`, which leaves the allowlist off. The SAM template sets `InvokeMode: BUFFERED`.

Suggestion: Add a Lambda Function URL example next to the deploy page that sets those three flags and lists the headers the function URL must forward (`content-type`, `accept`, `mcp-protocol-version`, `mcp-session-id`).

## 4. Reddit search.json returns 403 Blocked

Severity: Important

Task: Count recent Reddit mentions for a tool, the same source StackRadar already uses.

Steps: `GET https://www.reddit.com/search.json?q=fastapi&sort=new&t=week&limit=5` with user agent `stackradar-mcp/0.1 (hackathon demo)`.

Expected: A JSON listing, the way the public API has worked from a laptop in the past.

Actual: `HTTP Error 403: Blocked`. No body worth parsing. This happened from the build environment on 14 Oct 2026, not just from a unit test double.

Workaround: Treat any Reddit failure as "use the snapshot count", say so in the spoken line when the row is mixed, and remember the failure for 15 minutes so the next question does not wait on another 403. StackRadar's own scraper already moved Reddit reads to RSS for this reason. A follow up could do the same here.

Suggestion: Document one unauthenticated read that a script with a normal user agent can rely on, or state outright that search.json is blocked off the web UI.

## 5. Hacker News `nbHits` is not a mention count

Severity: Important

Task: Turn an Algolia search into the Hacker News mention count the formula expects.

Steps: Called `https://hn.algolia.com/api/v1/search` and first used `nbHits` as the count. Ran a live digest across the catalog.

Expected: A number in the same range as "stories we read this week", which is what StackRadar's scraper counts.

Actual: `nbHits` is the size of the match set. Common keywords produced huge totals. The first live digest said Bun had 618 more community mentions than the baseline, which saturated the score and made the spoken line absurd. The API itself returned 200 and was otherwise fine.

Workaround: Request `hitsPerPage=20` and count the `hits` array. That matches "stories we actually received" and stays inside the formula's 25 mention cap.

Suggestion: The Algolia docs are clear if you read them. A note in MCP or hackathon sample servers would have saved the bad first wiring: use `hits`, not `nbHits`, when you mean "how many posts did I look at".

## 6. Slim Python images have no venv

Severity: Nice-to-have

Task: Install the MCP SDK into a virtualenv on the build machine before running tests.

Steps: `python3 -m venv .venv` on the image that came with the workspace (Python 3.12.3).

Expected: ensurepip would create the environment.

Actual: `The virtual environment was not created successfully because ensurepip is not available.` The fix was `apt install python3.12-venv`.

Workaround: Installed the distro package, then `pip install -e ".[dev]"`.

Suggestion: The SDK's install line assumes a normal CPython. One sentence in the install docs for Debian and slim images ("you need the venv package, ensurepip is often split out") would match what people hit in containers.
