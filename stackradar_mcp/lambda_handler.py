"""AWS Lambda entry point used by the SAM template.

The Function URL is configured for buffered responses. Streamable HTTP's
default SSE stream does not fit that mode, so the app is built with
``json_response=True`` and ``stateless_http=True``. Host is ``0.0.0.0`` so the
SDK does not turn on the localhost DNS-rebinding allowlist, which would reject
the function URL's Host header.
"""

from __future__ import annotations

from mangum import Mangum

from stackradar_mcp.server import mcp

app = mcp.streamable_http_app(json_response=True, stateless_http=True, host="0.0.0.0")
handler = Mangum(app, lifespan="auto")
