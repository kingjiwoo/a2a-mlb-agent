from http.server import BaseHTTPRequestHandler
import json
from mcp import ServerSession
from mcp.server.stdio import stdio_server
import asyncio
import sys
import os

# MCP 서버 설정
class MCPServer:
    def __init__(self):
        self.server = stdio_server()
        self.session = None
    
    async def handle_request(self, request_data):
        """MCP 요청을 처리합니다."""
        try:
            if not self.session:
                self.session = ServerSession(self.server)
                await self.session.start()
            
            # MCP 요청 처리
            response = await self.session.handle_request(request_data)
            return response
        except Exception as e:
            return {"error": str(e)}

# Vercel Function 핸들러
class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """POST 요청 처리 (MCP 통신)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # MCP 서버로 요청 전달
            mcp_server = MCPServer()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                response = loop.run_until_complete(
                    mcp_server.handle_request(request_data)
                )
            finally:
                loop.close()
            
            # 응답 반환
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_GET(self):
        """GET 요청 처리 (상태 확인)"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        status_response = {"status": "MCP Server Running", "endpoint": "/mcp"}
        self.wfile.write(json.dumps(status_response).encode())

# Vercel Function 진입점
def handler(request, context):
    """Vercel Function 메인 핸들러"""
    if request.method == 'POST':
        return MCPHandler().do_POST()
    elif request.method == 'GET':
        return MCPHandler().do_GET()
    else:
        return {"error": "Method not allowed"}, 405 