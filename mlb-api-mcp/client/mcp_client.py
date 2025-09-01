import argparse
import asyncio
import json
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.http import HttpClientParameters, http_client


async def connect_stdio(server_script: str, python_cmd: str = "python") -> ClientSession:
    exit_stack = AsyncExitStack()
    await exit_stack.__aenter__()

    params = StdioServerParameters(command=python_cmd, args=[server_script])
    stdio_transport = await exit_stack.enter_async_context(stdio_client(params))
    read, write = stdio_transport
    session = await exit_stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    # attach stack for later close
    session._exit_stack = exit_stack  # type: ignore[attr-defined]
    return session


async def connect_http(base_url: str) -> ClientSession:
    exit_stack = AsyncExitStack()
    await exit_stack.__aenter__()

    # Ensure trailing slash for Starlette Mount behavior
    if not base_url.endswith("/"):
        base_url = base_url + "/"

    params = HttpClientParameters(base_url=base_url)
    http_transport = await exit_stack.enter_async_context(http_client(params))
    read, write = http_transport
    session = await exit_stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    session._exit_stack = exit_stack  # type: ignore[attr-defined]
    return session


async def list_tools(session: ClientSession) -> None:
    resp = await session.list_tools()
    tools = resp.tools
    print(f"Tools ({len(tools)}):")
    for t in tools:
        print(f"- {t.name}: {t.description}")
        try:
            schema = json.dumps(t.inputSchema, ensure_ascii=False)
            print(f"  schema: {schema}")
        except Exception:
            pass


async def call_tool(
    session: ClientSession, tool_name: str, arguments: Optional[Dict[str, Any]] = None
) -> None:
    arguments = arguments or {}
    result = await session.call_tool(tool_name, arguments=arguments)
    # result.content is a list of content items per MCP spec
    print(json.dumps({"content": [c.model_dump() for c in result.content]}, ensure_ascii=False, indent=2))


def load_args_json(args_json: Optional[str], args_file: Optional[str]) -> Dict[str, Any]:
    if args_json:
        return json.loads(args_json)
    if args_file:
        with open(args_file, "r") as f:
            return json.load(f)
    return {}


async def main() -> None:
    parser = argparse.ArgumentParser(description="MCP test client for MLB API MCP Server")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common connection options
    parser.add_argument(
        "--mode",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode to connect to server (default: stdio)",
    )
    parser.add_argument(
        "--server-script",
        default=os.path.join(os.path.dirname(__file__), os.pardir, "main.py"),
        help="Path to server main.py (stdio mode)",
    )
    parser.add_argument(
        "--python-cmd",
        default="python",
        help="Python command to run server (stdio mode)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/mcp",
        help="HTTP base URL to the MCP endpoint (http mode). Example: http://localhost:8000/mcp",
    )

    # list-tools
    sp_list = subparsers.add_parser("list-tools", help="List available tools")
    sp_list.set_defaults(subcmd="list-tools")

    # call-tool
    sp_call = subparsers.add_parser("call-tool", help="Call a tool with JSON arguments")
    sp_call.add_argument("tool", help="Tool name")
    sp_call.add_argument(
        "--args-json",
        help="JSON string for tool arguments (e.g. '{\"season\": 2024}')",
    )
    sp_call.add_argument(
        "--args-file",
        help="Path to JSON file containing tool arguments",
    )
    sp_call.set_defaults(subcmd="call-tool")

    # example: quick demo for standings
    sp_demo = subparsers.add_parser("demo", help="Quick demo: get_mlb_standings for current year")
    sp_demo.set_defaults(subcmd="demo")

    args = parser.parse_args()

    session: Optional[ClientSession] = None
    try:
        if args.mode == "stdio":
            session = await connect_stdio(os.path.abspath(args.server_script), args.python_cmd)
        else:
            session = await connect_http(args.base_url)

        if args.subcmd == "list-tools":
            await list_tools(session)
        elif args.subcmd == "call-tool":
            tool_args = load_args_json(args.args_json, args.args_file)
            await call_tool(session, args.tool, tool_args)
        elif args.subcmd == "demo":
            await call_tool(session, "get_mlb_standings", {})
    finally:
        # Graceful shutdown
        if session is not None and hasattr(session, "_exit_stack"):
            await session._exit_stack.aclose()  # type: ignore[attr-defined]


if __name__ == "__main__":
    asyncio.run(main())

