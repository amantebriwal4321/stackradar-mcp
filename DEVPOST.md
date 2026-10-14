# StackRadar MCP

Draft Devpost answers for Build, Ship, Shape. Alexa+ track. Solo entry, Aman Tebriwal, GitHub `amantebriwal4321`. Deadline on the rules page: 23 Oct 2026, 12:00pm Pacific (12:30am IST on 24 Oct).

Paste the sections below into the form. The video script is at the bottom. Record it under three minutes, upload to YouTube or Vimeo, public.

## Project name

StackRadar MCP

## Tagline

Ask which developer tools are actually heating up.

## Elevator

I run StackRadar, a small desk that scores about 30 developer tools from GitHub, Hacker News, Dev.to, Reddit, and RSS. The number is absolute, 0 to 100: stars 60 percent, forks 15 percent, community mentions 25 percent. It works on a screen. It is clumsy out loud.

StackRadar MCP puts that formula on a self hosted MCP server. A host can ask what is trending in AI this week, compare FastAPI with Next.js, or hear a weekly digest. Every tool returns a short spoken line plus the breakdown. If an API is down, a saved snapshot still answers, and the line says so.

## Description

StackRadar MCP is a Python server on the official MCP SDK. It speaks spec revisions 2025-11-25 and 2026-07-28 over Streamable HTTP. Four tools: `trending_tools`, `compare_tools`, `tool_score`, `weekly_digest`.

The score is `calculate_all_tool_scores` from my StackRadar repo, including the log floors, the 25 mention cap, and the word boundary matcher. The catalog slugs match that repo too.

The new part is the voice layer. Leaders follow the momentum score. The "who got louder" line is the change in community mentions against a saved baseline. A week of stars barely moves a log scale that tops out near 300,000, so the digest reports the thing that can actually move.

Live reads use the public GitHub, Hacker News, and Dev.to APIs, plus RSS. Reddit's public search returned 403 Blocked from this environment, so that slice falls back to the snapshot. Successful fetches cache for six hours. A failed source is remembered for 15 minutes. A live refresh gives up after about eight seconds and answers with whatever it has, so a spoken question does not hang.

There is a demo client that opens a real Streamable HTTP session and calls all four tools, a sample host config, tests, a Dockerfile, and a SAM template for a Lambda Function URL. Lambda's buffered URL cannot carry the default SSE stream, so each POST returns one JSON body and the server keeps no session.

The Alexa+ add-on CLI and web simulator are select partner only. I cannot attach this server to a device today. The FAQ says a self hosted server plus your own client is the submission. That client is in the repo.

## How to try it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
STACKRADAR_MODE=seed STACKRADAR_PORT=8741 stackradar-mcp
python clients/demo_client.py
```

Health: `http://127.0.0.1:8741/health`

The demo prints a protocol version and one spoken line per tool. Snapshot mode is deterministic. Set `STACKRADAR_MODE=auto` when you want live GitHub, Hacker News, and Dev.to numbers. Optional `GITHUB_TOKEN` if you have one.

## Built with

* Official MCP Python SDK 2.3, Streamable HTTP
* StackRadar scoring formula and tool catalog
* GitHub REST, Hacker News Algolia, Dev.to, RSS
* AWS SAM and Lambda Function URL (template in the repo)
* Docker

## Track

Alexa+

## Mini challenges

Open source. This repository is a new MIT project, written for the hackathon window. GitHub username `amantebriwal4321`. The work is the MCP server: four tools, the ported scorer, live fetches with a snapshot fallback, tests, and deploy config. It matters because the score I already publish can be asked out loud, by any MCP host, without scraping the website.

AWS Builder. `template.yaml` deploys the same app to a Lambda Function URL. The handler is `stackradar_mcp/lambda_handler.py` (Mangum in front of the Streamable HTTP app, JSON responses, no session). I have not deployed it from this environment. It needs my AWS account. Product feedback below covers SAM and Lambda as the AWS surface I actually wired.

## Product feedback

Which tools, and for what

* MCP Python SDK, to expose the four tools over Streamable HTTP and to drive the demo client.
* Public GitHub, Hacker News, Dev.to, Reddit, and RSS, for the signals behind the score.
* AWS SAM and Lambda Function URLs, as the deploy path.
* I did not get the Alexa+ add-on CLI, MCP Toolkit, or web simulator. The hackathon FAQ says they are select partner preview.

What worked

* `MCPServer` plus `run(transport="streamable-http")` got a real client talking quickly. The same four tools pass in process and over HTTP.
* `json_response` and `stateless_http` are real switches, and they are what a Lambda URL needs.
* The v2 migration guide tells the truth about the rename and about moving host and port onto `run()`.
* GitHub, Hacker News, Dev.to, and the Hacker News RSS feed answered with normal 200s. I refreshed all 31 star counts from the public GitHub API while building the snapshot.

What needs work

* Alexa+ onboarding is closed to participants. The quickstart still says to run the Alexa AI CLI. The FAQ says you cannot. I built a server I cannot register.
* Streamable HTTP defaults to an SSE stream and, on the 2025-11-25 path, to an in memory session. Both fight a buffered Function URL and a load balancer that is not sticky. The flags exist. A first reading does not tell you to set them.
* Building the app with host `127.0.0.1` turns on a localhost Host allowlist. A function URL host would get HTTP 421 until you pass `0.0.0.0` or your own allowlist.
* `https://www.reddit.com/search.json` returned 403 Blocked to a client with a normal user agent. The practical read is RSS, which StackRadar already uses.
* Hacker News `nbHits` is the size of the index. I first used it as a mention count and the digest claimed Bun had 618 new mentions. Counting the returned `hits` fixed it.

Onboarding, from zero to a working call

SDK install was `pip install mcp`. The surprise was the v2 API, not the idea of the protocol. The first successful call was an in memory client hitting `tool_score`. The slow part was keeping a reply useful when Reddit is blocked and when a live refresh has to stop. Alexa onboarding stopped at the partner gate. I never got a device hello world, because there is no door.

Would I build with these again

Yes for MCP, and yes for Lambda as a host for a stateless JSON MCP server. The protocol is the right seam for a voice assistant. I would add an Alexa+ add-on again once a normal developer can register a URL. I would not start a weekend project that depends on the partner CLI as it stands.

## Feature requests

1. A public way to register a self hosted MCP URL on Alexa+, with a simulator that can call it. Priority: Critical. The track tells every entrant to build this server, then the console path is closed.
2. A one page Lambda note: JSON responses, no session, which headers, which Host checks. Priority: Important. I had to read the SDK source to learn that the default host enables a localhost allowlist.
3. An unauthenticated Reddit read that does not 403 a script, or a docs line that says search.json is blocked. Priority: Nice-to-have. RSS already works.

## Friction log

Full writeup with steps, expected, actual, workaround, and suggestion: `FRICTION_LOG.md`. Six entries. The critical one is the closed Alexa+ onboarding. The others are the SDK v2 move, Lambda versus SSE and the localhost host check, Reddit's 403, Hacker News `nbHits`, and a slim Python image with no venv.

## Video script

About two and a half minutes if you talk at a normal pace. No music bed unless you have rights to it. No third party logos that you do not need. Screen is a terminal the whole time, plus two seconds on the architecture diagram in the README if you want a cutaway.

0:00
"This is StackRadar. I score developer tools from 0 to 100 using GitHub, Hacker News, Dev.to, Reddit, and RSS. Same formula as my web app. This project puts it on an MCP server, so a voice assistant can ask."

Show the README mermaid for a couple of seconds, then the terminal.

0:18
"Starting the server. Streamable HTTP, port 8741. The health check lists protocol 2025-11-25 and the later 2026 revision."

Run `STACKRADAR_MODE=seed STACKRADAR_PORT=8741 stackradar-mcp`. In the other pane, open `http://127.0.0.1:8741/health` or curl it. Point at `streamable-http` and `2025-11-25`.

0:35
"This demo client is a real MCP client. It connects, lists the tools, and calls each one. Snapshot mode, so the video does not depend on a rate limit."

Run `python clients/demo_client.py`. Leave each spoken block on screen long enough to read it out loud.

0:50
Read the AI trending line as it prints. It will be close to: "Top AI and ML tools over the last 7 days: Ollama at 84, TensorFlow at 79, and Hugging Face Transformers at 78."

1:10
Read the FastAPI score. "FastAPI scores 71 out of 100. It sits in the mature band. The score is steady against the saved baseline."

1:25
Read the compare line. "FastAPI scores 71 and Next.js scores 79. Next.js leads by 8 points, and GitHub stars are the biggest gap."

1:40
Read the digest. "The board is led by React at 91, Ollama at 84, and TensorFlow at 79. Ollama is also the loudest new conversation, with 13 more community mentions than the saved baseline."

1:55
"That split is on purpose. The score is mostly stars, on a log scale, so a week does not reshuffle the board. The louder line is the mention change. Stars, forks, and mentions are in the structured result if you ask for the breakdown. The weights are 60, 15, and 25, same function as the StackRadar backend."

2:15
"If GitHub or Reddit fails, the snapshot still answers, and the sentence says the reading is mixed or from the snapshot. Deploy is a SAM template to a Lambda Function URL, same JSON body, no session. That part needs my AWS account, so it is not live in this video."

2:35
"Alexa+ onboarding is still partner only, so this client is the stand in. Four tools, one formula I already use, short enough to say out loud. That is StackRadar MCP."

Stop by 2:50.
