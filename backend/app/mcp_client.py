import json
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BACKEND_DIR = Path(__file__).resolve().parents[1]


class MCPToolClient:
    """Small MCP client that discovers tool schemas and reuses one session per batch."""

    def _server(self):
        env = {**os.environ, "PYTHONPATH": str(BACKEND_DIR)}
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            cwd=str(BACKEND_DIR),
            env=env,
        )

    @asynccontextmanager
    async def _session(self):
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(self._server()))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            yield session

    @staticmethod
    def _tool_record(tool):
        return {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": getattr(tool, "inputSchema", {}) or {},
        }

    async def list_tools(self):
        async with self._session() as session:
            result = await session.list_tools()
            return [self._tool_record(tool) for tool in result.tools]

    async def call(self, tool_name, arguments):
        results = await self.call_many(tool_name, [arguments])
        return results[0]

    async def call_many(self, tool_name, argument_sets):
        """Call a discovered tool repeatedly without spawning a new server per call."""
        async with self._session() as session:
            available = await session.list_tools()
            if tool_name not in {tool.name for tool in available.tools}:
                raise RuntimeError(f"MCP tool not found: {tool_name}")

            results = []
            for arguments in argument_sets:
                result = await session.call_tool(tool_name, arguments)
                if getattr(result, "isError", False):
                    raise RuntimeError(f"MCP tool returned an error: {result.content}")

                decoded = None
                for item in getattr(result, "content", []):
                    if getattr(item, "type", "") == "text":
                        try:
                            decoded = json.loads(item.text)
                        except (TypeError, json.JSONDecodeError):
                            decoded = {"text": item.text}
                        break
                results.append(decoded if decoded is not None else {})
            return results
