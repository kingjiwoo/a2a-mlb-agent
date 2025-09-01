# third_party/mlb_api_mcp/__init__.py
# 패키지 표시 + main.py에서 내보내는 객체들을 재노출
try:
    from .main import app, create_app, mcp  # main.py에서 정의한 것들을 가져와 노출
except Exception:
    # 배포/빌드 타이밍에 따라 아직 준비 안 되었을 수도 있으므로 안전장치
    app = None
    create_app = None
    mcp = None

__all__ = ["app", "create_app", "mcp"]
