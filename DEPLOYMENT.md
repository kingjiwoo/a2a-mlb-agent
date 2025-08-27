# 🚀 MLB 이적 전문 에이전트 Vercel 배포 가이드

이 프로젝트는 MLB 이적 전문 에이전트를 Vercel에서 호스팅하기 위한 구조로 설계되었습니다.

## 📁 프로젝트 구조

```
mlb_agent/
├── api/
│   └── index.py          # Vercel Python Runtime 엔트리포인트
├── prompts/              # 프롬프트 파일들
├── mlb-api-mcp/         # MCP 서버
├── agent_executor.py     # MLB 에이전트 실행기
├── server.py             # 기존 A2A 서버
├── requirements.txt      # Python 의존성
├── Pipfile              # Python 버전 및 패키지 관리
├── vercel.json          # Vercel 배포 설정
└── README.md
```

## 🔧 주요 특징

- **A2A 서버 호스팅**: 에이전트 카드 및 통신 프로토콜 지원
- **MCP 서버 통합**: MLB API 툴들을 에이전트에서 사용
- **FastAPI 기반**: 현대적이고 빠른 Python 웹 프레임워크
- **서버리스 아키텍처**: Vercel의 Python Runtime 활용
- **CORS 지원**: 프론트엔드에서 API 호출 가능

## 🚀 배포 단계

### 1. GitHub에 코드 푸시

```bash
cd mlb_agent
git add .
git commit -m "Add Vercel deployment support"
git push origin main
```

### 2. Vercel 프로젝트 생성

1. [Vercel Dashboard](https://vercel.com/dashboard)에 접속
2. **New Project** 클릭
3. GitHub 저장소 연결
4. **Framework Preset**: `Other` 선택
5. **Root Directory**: `mlb_agent` 설정
6. **Build Command**: 비워두기 (자동 감지)
7. **Output Directory**: 비워두기 (자동 감지)

### 3. 환경변수 설정

Vercel 대시보드에서 **Settings** → **Environment Variables**에 추가:

```
ANTHROPIC_API_KEY=sk-ant-실제API키
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### 4. 배포 실행

**Deploy** 버튼을 클릭하면 자동으로 배포가 시작됩니다.

## 🌐 배포 후 접근 가능한 엔드포인트

### 기본 정보
- **루트**: `/` - 에이전트 기본 정보
- **A2A 프로토콜**: `/.well-known/agent.json` - 에이전트 카드

### API 엔드포인트
- **에이전트 카드**: `/api/agent/card`
- **스킬 목록**: `/api/agent/skills`
- **헬스 체크**: `/api/health`
- **MCP 상태**: `/api/mcp/status`

### 채팅 기능
- **일반 채팅**: `POST /api/chat`
- **스트리밍 채팅**: `POST /api/chat/stream`

## 🧪 로컬 테스트

### 1. 서버 실행

```bash
cd mlb_agent
uvicorn api.index:app --reload --port 8000
```

### 2. API 테스트

```bash
python test_vercel_api.py
```

## 📊 배포 확인

배포가 완료되면 다음 URL들로 접근 가능합니다:

- **메인 페이지**: `https://your-project.vercel.app/`
- **에이전트 카드**: `https://your-project.vercel.app/.well-known/agent.json`
- **API 문서**: `https://your-project.vercel.app/docs`

## 🔍 문제 해결

### 일반적인 문제들

1. **404 오류**
   - `api/index.py`에 `app` 변수가 제대로 export되었는지 확인
   - `vercel.json`의 `rewrites` 설정 확인

2. **Python 버전 오류**
   - `Pipfile`의 `python_version`이 3.11로 설정되어 있는지 확인

3. **의존성 설치 오류**
   - `requirements.txt`의 패키지 버전 호환성 확인
   - Vercel 로그에서 구체적인 오류 메시지 확인

4. **환경변수 오류**
   - `ANTHROPIC_API_KEY`가 올바르게 설정되었는지 확인
   - API 키 형식이 `sk-ant-`로 시작하는지 확인

### 로그 확인

Vercel 대시보드에서 **Functions** → **api/index.py** → **View Function Logs**로 상세 로그를 확인할 수 있습니다.

## 🎯 A2A 클라이언트에서 사용

배포된 에이전트를 A2A 클라이언트에서 사용하려면:

```python
from a2a.client import A2ACardResolver
from a2a.client.client_factory import ClientFactory

# 에이전트 카드 리졸버 생성
resolver = A2ACardResolver(
    base_url="https://your-project.vercel.app"
)

# 에이전트 카드 가져오기
agent_card = await resolver.get_agent_card()

# A2A 클라이언트 생성
client = ClientFactory().create(agent_card)

# 메시지 전송
response = await client.send_message(user_message)
```

## 📈 성능 최적화

- **메모리**: 현재 1024MB로 설정 (필요시 조정)
- **타임아웃**: 현재 60초로 설정 (복잡한 쿼리 처리용)
- **콜드 스타트**: 첫 요청 시 약간의 지연이 있을 수 있음

## 🔒 보안 고려사항

- **CORS**: 현재 모든 도메인 허용 (`*`), 프로덕션에서는 제한 권장
- **API 키**: 환경변수로 안전하게 관리
- **인증**: 필요시 JWT 토큰 기반 인증 추가 가능

## 📞 지원

문제가 발생하면:
1. Vercel 로그 확인
2. 로컬에서 `test_vercel_api.py` 실행하여 테스트
3. GitHub Issues에 문제 보고

---

**🎉 배포가 완료되면 MLB 이적 전문 에이전트를 전 세계 어디서나 사용할 수 있습니다!** 