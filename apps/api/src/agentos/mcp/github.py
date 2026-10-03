import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from agentos.core.config import get_settings

_TIMEOUT_SECONDS = 30


class GitHubMCPError(Exception):
    """The GitHub MCP server rejected the token or could not reach the repository."""


@asynccontextmanager
async def github_session(token: str) -> AsyncIterator[ClientSession]:
    """An initialised, read-only session with the GitHub MCP server."""
    headers = {
        "Authorization": f"Bearer {token}",
        # Server-side guarantees that agents cannot modify anything on GitHub.
        "X-MCP-Readonly": "true",
        "X-MCP-Toolsets": "repos,issues,pull_requests",
    }
    async with (
        create_mcp_http_client(headers=headers) as http,
        streamable_http_client(get_settings().github_mcp_url, http_client=http) as streams,
        ClientSession(streams[0], streams[1]) as session,
    ):
        await session.initialize()
        yield session


async def read_only_tools(session: ClientSession) -> list[dict]:
    """The server's read-only tools in the function-calling format chat models accept."""
    tools = (await session.list_tools()).tools
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
        # Belt and braces on top of the read-only header.
        if tool.annotations is None or tool.annotations.read_only_hint is not False
    ]


async def call_tool(session: ClientSession, name: str, arguments: dict[str, Any]) -> str:
    """Call a tool and return its output as text ("Error: ..." if the tool failed)."""
    result = await session.call_tool(name, arguments, read_timeout_seconds=_TIMEOUT_SECONDS)
    parts = []
    for block in result.content:
        if getattr(block, "text", None):
            parts.append(block.text)
        elif getattr(getattr(block, "resource", None), "text", None):
            parts.append(block.resource.text)  # file contents arrive as embedded resources
    text = "\n".join(parts)
    return f"Error: {text}" if result.is_error else _compact_listing(text)


def _compact_listing(text: str) -> str:
    """Reduce a directory listing to one "type path" line per entry.

    The server returns several URLs and hashes per entry, which costs tokens and tells the
    model nothing it needs.
    """
    try:
        entries = json.loads(text)
    except ValueError:
        return text
    if not isinstance(entries, list) or not all(
        isinstance(e, dict) and "path" in e and "type" in e for e in entries
    ):
        return text
    return "\n".join(f"{e['type']} {e['path']}" for e in entries)


async def verify_repository_access(token: str, owner: str, repo: str) -> None:
    """Open a session with the GitHub MCP server and read the repository root.

    Raises GitHubMCPError with a user-facing message if either step fails.
    """
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS), github_session(token) as session:
            result = await session.call_tool(
                "get_file_contents", {"owner": owner, "repo": repo, "path": "/"}
            )
    except Exception as exc:
        raise GitHubMCPError(
            "Could not connect to GitHub. Check that the access token is valid."
        ) from exc

    if result.is_error:
        raise GitHubMCPError(
            f"GitHub could not open {owner}/{repo} with this token. "
            "Check the repository name and that the token can read it."
        )
