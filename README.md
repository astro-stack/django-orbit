# Django Orbit

**AI agent-native runtime evidence and debugging for Django.**

Django Orbit records what your application is doing and gives that evidence to
you and your coding agent. Requests, SQL, logs, exceptions, jobs, cache
operations and other runtime events are linked into bounded, safe context for
investigation.

Orbit has its own dashboard at <code>/orbit/</code> and a read-only MCP server. It does not
inject HTML into your application or require you to leave your coding-agent
workflow to start debugging.

<img width="1312" height="612" alt="Django Orbit dashboard" src="https://github.com/user-attachments/assets/87528512-b458-4217-8dde-699a23c507ce" />

[![PyPI version](https://img.shields.io/pypi/v/django-orbit?style=flat-square)](https://pypi.org/project/django-orbit/)
[![CI](https://github.com/astro-stack/django-orbit/actions/workflows/ci.yml/badge.svg)](https://github.com/astro-stack/django-orbit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.0%2B-green?style=flat-square&logo=django)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)

[Install](#install) | [Try the demo](#try-the-demo) | [Connect an agent](#connect-a-coding-agent) | [Documentation](https://astro-stack.github.io/django-orbit)

## Why Orbit

When a Django issue reaches a coding agent, the hard part is usually not
writing a patch. It is reconstructing what happened:

- Which request or job failed?
- Which SQL queries, logs and exceptions belong to it?
- Is the signal a real regression, a slow query or only duplicate evidence?
- What should be reproduced with a test before changing code?

Orbit captures that runtime evidence locally and keeps it connected by request
family. Humans can inspect it in the dashboard. Agents can query a bounded,
masked and read-only context through MCP.

The intended workflow is:

~~~text
runtime event -> Orbit evidence -> agent investigation -> test plan -> fix -> verification
~~~

Orbit is inspired by Django Debug Toolbar, Laravel Telescope and Spatie Ray,
but lives outside the host application's UI and is designed for APIs, SPAs,
background work and AI-assisted debugging.

## Install

~~~bash
pip install django-orbit
~~~

For MCP access from Claude, Codex, Cursor or another compatible client:

~~~bash
pip install django-orbit[mcp]
~~~

## Quick Start

Add Orbit to your Django project:

~~~python
# settings.py
INSTALLED_APPS = [
    # ...
    "orbit",
]

MIDDLEWARE = [
    "orbit.middleware.OrbitMiddleware",
    # ...
]
~~~

Mount the dashboard URLs:

~~~python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("orbit/", include("orbit.urls")),
    # ...
]
~~~

Run migrations and start Django:

~~~bash
python manage.py migrate
python manage.py runserver
~~~

Open <code>http://localhost:8000/orbit/</code> and exercise an endpoint in your app.
Orbit will show the captured request and its related runtime evidence.

For the full setup, configuration reference and production guidance, see the
[Quick Start documentation](https://astro-stack.github.io/django-orbit/quickstart/).

## Connect a Coding Agent

Orbit's MCP server runs locally over stdio. It reads Orbit evidence and does
not modify your application.

Add a server entry to an MCP-compatible client:

~~~json
{
  "mcpServers": {
    "django-orbit": {
      "command": "python",
      "args": ["manage.py", "orbit_mcp"],
      "cwd": "/path/to/your/django/project"
    }
  }
}
~~~

The exact location of this entry depends on the client. See the [MCP setup
guide](https://astro-stack.github.io/django-orbit/mcp/) for Claude Desktop,
Claude Code, Codex, Cursor and other clients.

### Ticket to Fix

Once MCP is connected, a practical investigation looks like this:

~~~text
1. Describe the ticket or failing behavior.
2. Match it to recent Orbit evidence.
3. Inspect the request family, exception group or endpoint window.
4. Generate a masked incident bundle.
5. Ask the agent for ranked hypotheses and a regression-test plan.
6. Inspect the code, write the test and apply the smallest justified fix.
7. Re-run the test and verify the runtime signal again.
~~~

Useful tools for this flow include:

| Tool | Use |
| --- | --- |
| <code>build_debug_brief</code> | Match a ticket description to recent evidence |
| <code>investigate_request</code> | Inspect one request family and related signals |
| <code>investigate_exception_group</code> | Group an exception fingerprint and affected paths |
| <code>create_incident_bundle</code> | Create JSON, Markdown or prompt handoff context |
| <code>propose_fix_hypotheses</code> | Rank possible fix directions from evidence |
| <code>propose_test_plan</code> | Suggest focused regression or performance tests |
| <code>generate_pr_context</code> | Prepare evidence and release-risk context for a PR |

The agent is not expected to edit code automatically. Orbit supplies context so
the agent can investigate, propose and verify with the developer in control.

## Agent Safety

MCP output is designed to be safe to inspect before sharing with an agent:

- common sensitive keys are masked;
- result sizes and payloads are bounded;
- <code>MCP_INCLUDE_PAYLOADS: False</code> enables metadata-only output;
- prompts, completions and tool-call arguments are not captured by default;
- <code>audit_mcp_exposure</code>, <code>preview_masked_entry</code> and
  <code>list_agent_safe_fields</code> expose the effective safety boundary;
- MCP is read-only and can be disabled with <code>MCP_ENABLED: False</code>.

Recommended local or shared-environment settings:

~~~python
ORBIT_CONFIG = {
    "AUTH_CHECK": lambda request: request.user.is_staff,
    "MCP_ENABLED": True,
    "MCP_INCLUDE_PAYLOADS": False,
    "MCP_MAX_LIMIT": 100,
    "LLM_CAPTURE_CONTENT": False,
    "LLM_CAPTURE_TOOL_CALL_ARGUMENTS": False,
    "WATCHER_FAIL_SILENTLY": True,
}
~~~

Orbit records operational context, so <code>/orbit/</code> and the local MCP process must
still be treated as developer or operator access. Read the [security
guide](https://astro-stack.github.io/django-orbit/security/) before enabling it
in staging or production.

## What Orbit Captures

Orbit supports watchers for the parts of a Django application that usually
matter during debugging:

- HTTP requests and responses;
- SQL, slow queries, duplicate evidence and classified N+1 candidates;
- Python logs and exceptions with request context;
- cache, model, transaction and permission activity;
- management commands and background jobs;
- outgoing HTTP, mail, Redis and storage operations;
- AI/LLM metadata such as provider, model, tokens, latency, errors and tool
  names.

Related events are connected by a <code>family_hash</code>. The full watcher matrix,
configuration keys and extension points are documented in the [API and
configuration reference](https://astro-stack.github.io/django-orbit/api/).

## Try the Demo

The repository includes a small Django project with curated scenarios:

~~~bash
git clone https://github.com/astro-stack/django-orbit.git
cd django-orbit
pip install -e .
python demo.py setup
python manage.py runserver
~~~

Then open:

| URL | Purpose |
| --- | --- |
| <code>http://localhost:8000/</code> | Generate demo runtime events |
| <code>http://localhost:8000/orbit/</code> | Inspect captured evidence |
| <code>http://localhost:8000/orbit/stats/</code> | Review runtime metrics |
| <code>http://localhost:8000/orbit/health/</code> | Check watcher health |

Run <code>python demo.py reset</code> to restore the curated demo corpus.

See [Running the Demo](https://astro-stack.github.io/django-orbit/running-demo/)
for the complete walkthrough and the [Codex/Claude debugging demo](https://astro-stack.github.io/django-orbit/codex-debug-demo/).

## Current Release: v0.13.0

The 0.13 line strengthens the agent-native base:

- versioned, privacy-safe Evidence API contracts;
- async-safe request correlation;
- capture health and metadata-only request detail through MCP;
- evidence-backed investigation guidance;
- safe fix handoffs with hypotheses and regression-test targets;
- deterministic query and N+1 analysis with explicit limitations.

Read the [full changelog](CHANGELOG.md) for the release history.

## Documentation Map

- [Installation](https://astro-stack.github.io/django-orbit/installation/)
- [Quick Start](https://astro-stack.github.io/django-orbit/quickstart/)
- [Configuration](https://astro-stack.github.io/django-orbit/configuration/)
- [Dashboard guide](https://astro-stack.github.io/django-orbit/dashboard/)
- [Stats dashboard](https://astro-stack.github.io/django-orbit/stats/)
- [MCP reference](https://astro-stack.github.io/django-orbit/mcp/)
- [Evidence API](https://astro-stack.github.io/django-orbit/evidence-api/)
- [Security](https://astro-stack.github.io/django-orbit/security/)
- [Storage backends](https://astro-stack.github.io/django-orbit/storage-backends/)
- [Roadmap](https://astro-stack.github.io/django-orbit/roadmap/)
- [Contributing](CONTRIBUTING.md)

## Orbit Pro

Django Orbit remains MIT-licensed and useful on its own. The open source
package includes the local dashboard, watchers, local MCP tools, masking,
incident bundles and safety controls.

[Orbit Pro](https://labs.wearehik.com/django-orbit/pro/) is a separate planned
self-hosted verification layer for teams using coding agents. It will build on
the open core with release comparison, saved investigations and verification of
agent-assisted changes. Planned capabilities are not required to use Orbit
today.

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and
read the relevant documentation before changing capture, MCP or safety
behavior.

## License

MIT. See [LICENSE](LICENSE).
