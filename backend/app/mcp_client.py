import asyncio
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

    @staticmethod
    def _decode_result(result):
        if getattr(result, "isError", False):
            raise RuntimeError(f"MCP tool returned an error: {result.content}")

        # MCP structured output is the application-facing data channel. Prefer
        # it when present; retain JSON text parsing for older servers.
        structured = getattr(result, "structuredContent", None)
        if structured is None:
            structured = getattr(result, "structured_content", None)
        if isinstance(structured, dict):
            return structured
        if isinstance(structured, list):
            return {"items": structured}

        for item in getattr(result, "content", []):
            if getattr(item, "type", "") == "text":
                try:
                    decoded = json.loads(item.text)
                    return decoded if isinstance(decoded, (dict, list)) else {"text": str(decoded)}
                except (TypeError, json.JSONDecodeError):
                    return {"text": str(getattr(item, "text", ""))}
        return {}

    async def discover_and_call_many(self, build_calls, tasks):
        """Discover a tool and run its independent searches in one MCP session."""
        async with self._session() as session:
            available = await session.list_tools()
            tool_records = [self._tool_record(tool) for tool in available.tools]
            tool_name, argument_sets = build_calls(tool_records, tasks)

            # Searches are independent. Gather them concurrently while preserving
            # task order in the returned list.
            raw_results = await asyncio.gather(
                *(session.call_tool(tool_name, arguments) for arguments in argument_sets)
            )
            return tool_name, [self._decode_result(result) for result in raw_results]

    async def call_many(self, tool_name, argument_sets):
        """Call a known tool concurrently using one MCP server session."""
        async with self._session() as session:
            available = await session.list_tools()
            if tool_name not in {tool.name for tool in available.tools}:
                raise RuntimeError(f"MCP tool not found: {tool_name}")
            raw_results = await asyncio.gather(
                *(session.call_tool(tool_name, arguments) for arguments in argument_sets)
            )
            return [self._decode_result(result) for result in raw_results]
