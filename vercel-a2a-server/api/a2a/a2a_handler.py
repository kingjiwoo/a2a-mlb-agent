from http.server import BaseHTTPRequestHandler
import json
import os
from typing import Dict, Any

# 환경변수에서 API 키 가져오기
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

class A2AHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """POST 요청 처리 (A2A 통신)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # A2A 요청 처리
            response = self.handle_a2a_request(request_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def handle_a2a_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """A2A 요청을 처리합니다."""
        try:
            # 요청 타입 확인
            request_type = request_data.get("type", "unknown")
            
            if request_type == "message":
                return self.handle_message(request_data)
            elif request_type == "agent_card":
                return self.get_agent_card()
            else:
                return {"error": f"Unknown request type: {request_type}"}
                
        except Exception as e:
            return {"error": f"Request handling error: {str(e)}"}
    
    def handle_message(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 메시지를 처리합니다."""
        try:
            # 메시지 내용 추출
            message_content = request_data.get("content", "")
            session_id = request_data.get("session_id", "default")
            
            # 간단한 응답 생성 (실제로는 AI 모델을 사용해야 함)
            response = {
                "type": "response",
                "session_id": session_id,
                "content": f"MLB 이적 전문 에이전트가 메시지를 받았습니다: {message_content}",
                "timestamp": "2024-01-01T00:00:00Z"
            }
            
            return response
            
        except Exception as e:
            return {"error": f"Message handling error: {str(e)}"}
    
    def get_agent_card(self) -> Dict[str, Any]:
        """에이전트 카드를 반환합니다."""
        from .agent_card import create_agent_card
        return create_agent_card()
    
    def do_GET(self):
        """GET 요청 처리 (상태 확인)"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        status_response = {
            "status": "A2A Server Running", 
            "endpoint": "/a2a",
            "model": ANTHROPIC_MODEL
        }
        self.wfile.write(json.dumps(status_response).encode())
    
    def do_OPTIONS(self):
        """CORS preflight 요청 처리"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

# Vercel Function 진입점
def handler(request, context):
    """Vercel Function 메인 핸들러"""
    if request.method == 'POST':
        return A2AHandler().do_POST()
    elif request.method == 'GET':
        return A2AHandler().do_GET()
    elif request.method == 'OPTIONS':
        return A2AHandler().do_OPTIONS()
    else:
        return {"error": "Method not allowed"}, 405 