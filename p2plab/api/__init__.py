"""Public surface of the `p2plab.api` package.

The `app` and `run_server` exports are intentionally **lazy**: importing
`p2plab.api` should not require FastAPI to be installed, since the CLI
dual-track subcommands and the plugin discovery code do not need an
HTTP runtime.

Use `from p2plab.api.fastapi_server import app, run_server` directly
when you need them (the `serve` subcommand does this).
"""

from .workspace import WorkspaceManager  # FastAPI-free

__all__ = ["WorkspaceManager"]
