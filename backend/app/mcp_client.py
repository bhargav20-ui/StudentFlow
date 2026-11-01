import sys, os
from pathlib import Path
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
BACKEND_DIR=Path(__file__).resolve().parents[1]
class MCPToolClient:
    async def list_tools(self):
        server=StdioServerParameters(command=sys.executable,args=["-m","mcp_server.server"],cwd=str(BACKEND_DIR),env={**os.environ,"PYTHONPATH":str(BACKEND_DIR)})
        async with AsyncExitStack() as stack:
            read,write=await stack.enter_async_context(stdio_client(server))
            session=await stack.enter_async_context(ClientSession(read,write))
            await session.initialize()
            tools=await session.list_tools()
            return [{"name":x.name,"description":x.description or ""} for x in tools.tools]

    async def call(self,tool_name,arguments):
        server=StdioServerParameters(command=sys.executable,args=["-m","mcp_server.server"],cwd=str(BACKEND_DIR),env={**os.environ,"PYTHONPATH":str(BACKEND_DIR)})
        async with AsyncExitStack() as stack:
            read,write=await stack.enter_async_context(stdio_client(server))
            session=await stack.enter_async_context(ClientSession(read,write))
            await session.initialize()
            tools=await session.list_tools()
            if tool_name not in {x.name for x in tools.tools}: raise RuntimeError(f"MCP tool not found: {tool_name}")
            result=await session.call_tool(tool_name,arguments)
            if getattr(result,"isError",False): raise RuntimeError(f"MCP tool error: {result.content}")
            for item in getattr(result,"content",[]):
                if getattr(item,"type","")=="text":
                    import json
                    try:return json.loads(item.text)
                    except Exception:return {"text":item.text}
            return {}
