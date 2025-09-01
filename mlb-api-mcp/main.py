import argparse
import os
import warnings

import uvicorn
from fastmcp import FastMCP
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from generic_api import setup_generic_tools
from mlb_api import setup_mlb_tools

# Suppress websockets deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="uvicorn.protocols.websockets")

# -------------- FastMCP 서버 구성 --------------
mcp = FastMCP("MLB API MCP Server")

# MCP 툴 등록
setup_mlb_tools(mcp)
setup_generic_tools(mcp)

# -------------- 커스텀 라우트 --------------
@mcp.custom_route("/", methods=["GET"])
async def root(request):
    return RedirectResponse(url="/docs")

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "ok"})

@mcp.custom_route("/info", methods=["GET"])
async def mcp_info(request):
    tools_list = await mcp.get_tools()
    return JSONResponse(
        {
            "status": "running",
            "protocol": "mcp",
            "server_name": "MLB API MCP Server",
            "description": "Model Context Protocol server for MLB statistics and baseball data",
            "mcp_endpoint": "/mcp",
            "tools_available": len(tools_list),
            "note": "This is an MCP server. Use MCP-compatible clients to interact with the tools.",
        }
    )

@mcp.custom_route("/tools", methods=["GET"])
async def list_tools(request):
    tools = []
    tools_list = await mcp.get_tools()
    for tool_name, tool in tools_list.items():
        tools.append(
            {
                "name": tool_name,
                "description": getattr(tool, "description", None) or "No description available",
                "parameters": getattr(tool, "parameters", None) or {},
            }
        )
    return JSONResponse({"tools": tools})

@mcp.custom_route("/docs", methods=["GET"])
async def docs(request):
    tools_list = await mcp.get_tools()
    docs_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MLB API MCP Server Documentation</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .endpoint {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .method {{ font-weight: bold; color: #0066cc; }}
            .path {{ font-weight: bold; color: #cc6600; }}
            .tools {{ margin: 10px 0; }}
            .tool {{ margin: 5px 0; padding: 10px; background: #f5f5f5; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <h1>MLB API MCP Server Documentation</h1>
        <p>A Model Context Protocol server that provides comprehensive access to MLB statistics and baseball data.</p>
        
        <h2>Available Endpoints</h2>
        
        <div class="endpoint">
            <span class="method">GET</span> <span class="path">/health</span>
            <p>Health check endpoint</p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <span class="path">/info</span>
            <p>Information about the MCP server</p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <span class="path">/tools</span>
            <p>List all available MCP tools</p>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> <span class="path">/mcp</span>
            <p>MCP protocol endpoint for MCP-compatible clients</p>
        </div>
        
        <h2>Available MCP Tools ({len(tools_list)} total)</h2>
        <div class="tools">
    """
    for tool_name, tool in tools_list.items():
        description = getattr(tool, "description", None) or "No description available"
        docs_html += f'<div class="tool"><strong>{tool_name}</strong>: {description}</div>'
    docs_html += """
        </div>
        
        <h2>Usage</h2>
        <p>This server implements the Model Context Protocol (MCP). Use MCP-compatible clients to interact with the tools.</p>
        <p>For direct HTTP access, you can use the endpoints listed above.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=docs_html)

# -------------- 서브앱/서버 공용 팩토리 --------------
def create_app():
    """
    FastMCP가 제공하는 HTTP 서브앱(FastAPI/Starlette)을 생성해서 반환.
    - CORS 허용
    - '/mcp' → '/mcp/' 경로 보정(Starlette Mount 트레일링 슬래시 이슈)
    """
    cors = Middleware(
        CORSMiddleware,
        allow_origins=["*"],           # 프로덕션에선 도메인 제한 권장
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
        max_age=86400,
    )

    starlette_app = mcp.http_app(middleware=[cors])

    # '/mcp' → '/mcp/' 보정 미들웨어
    class MCPPathRedirect:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope.get("type") == "http" and scope.get("path") == "/mcp":
                scope["path"] = "/mcp/"
                scope["raw_path"] = b"/mcp/"
            await self.app(scope, receive, send)

    return MCPPathRedirect(starlette_app)

# ✅ 모듈 임포트 시점에 app 노출(서브앱 마운트용)
app = create_app()

# -------------- 단독 실행(로컬 개발용) --------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLB API MCP Server")
    parser.add_argument("--http", action="store_true", help="Run server with HTTP transport")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port (default: 8000, env PORT overrides)")
    args = parser.parse_args()

    if args.http:
        port = int(os.environ.get("PORT", args.port))
        print(f"Starting MLB API MCP Server on port {port}...")
        print(f"- Documentation: http://localhost:{port}/docs")
        print(f"- Health check: http://localhost:{port}/health")
        print(f"- MCP server info: http://localhost:{port}/info")
        print(f"- Tools list: http://localhost:{port}/tools")
        print(f"- MCP protocol: http://localhost:{port}/mcp")

        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    else:
        # stdio(스미서리 등)
        mcp.run(transport="stdio")
