"""
Management command to start the Django Orbit MCP server.

Usage:
    python manage.py orbit_mcp

The server communicates over stdio, which is the standard MCP transport
for local tools. Configure your AI assistant to launch this command —
see the README for claude_desktop_config.json and .cursor/mcp.json examples.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Start the Django Orbit MCP server (stdio transport)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--transport",
            default="stdio",
            choices=["stdio"],
            help="MCP transport to use (default: stdio)",
        )

    def handle(self, *args, **options):
        try:
            from orbit.mcp_server import create_mcp_server
        except ImportError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        # FastMCP runs tool callables inside its async event loop, but Orbit's tools use
        # the synchronous Django ORM — which otherwise raises SynchronousOnlyOperation
        # ("You cannot call this from an async context"). This is a local, single-user
        # stdio server, so allowing the ORM in the loop is safe and is the simplest fix.
        import os

        os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

        self.stderr.write(
            self.style.SUCCESS("Starting Django Orbit MCP server (stdio)...")
        )
        self.stderr.write("Connect your AI assistant to this process via MCP.")
        self.stderr.write('Use Ctrl+C to stop.\n')

        mcp = create_mcp_server()
        mcp.run(transport=options["transport"])
