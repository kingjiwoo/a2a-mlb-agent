# Vercel로 MCP 서버와 A2A 서버 호스팅 가이드

## 🚀 개요

이 가이드는 MLB 이적 전문 에이전트의 MCP 서버와 A2A 서버를 Vercel에 호스팅하는 방법을 설명합니다.

## 📁 프로젝트 구조

```
mlb_agent/
├── vercel-mcp-server/          # MCP 서버
│   ├── vercel.json
│   ├── requirements.txt
│   └── api/mcp/
│       └── mcp_handler.py
├── vercel-a2a-server/          # A2A 서버
│   ├── vercel.json
│   ├── requirements.txt
│   └── api/a2a/
│       ├── agent_card.py
│       └── a2a_handler.py
└── vercel-deployment-guide.md  # 이 파일
```

## 🔧 사전 준비

### 1. Vercel CLI 설치
```bash
npm install -g vercel
```

### 2. Vercel 계정 생성 및 로그인
```bash
vercel login
```

### 3. 환경변수 설정
Vercel 대시보드에서 다음 환경변수를 설정해야 합니다:

- `ANTHROPIC_API_KEY`: Anthropic API 키
- `ANTHROPIC_MODEL`: 사용할 모델 (기본값: claude-3-5-sonnet-20241022)

## 🚀 MCP 서버 배포

### 1. MCP 서버 디렉토리로 이동
```bash
cd vercel-mcp-server
```

### 2. Vercel 프로젝트 초기화
```bash
vercel
```

### 3. 배포 설정
- Project name: `mlb-mcp-server`
- Directory: `./` (현재 디렉토리)
- Override settings: `No`

### 4. 배포 실행
```bash
vercel --prod
```

### 5. 배포 확인
배포가 완료되면 다음과 같은 URL이 제공됩니다:
```
https://mlb-mcp-server-xxxxx.vercel.app
```

## 🚀 A2A 서버 배포

### 1. A2A 서버 디렉토리로 이동
```bash
cd ../vercel-a2a-server
```

### 2. Vercel 프로젝트 초기화
```bash
vercel
```

### 3. 배포 설정
- Project name: `mlb-a2a-server`
- Directory: `./` (현재 디렉토리)
- Override settings: `No`

### 4. 배포 실행
```bash
vercel --prod
```

### 5. 배포 확인
배포가 완료되면 다음과 같은 URL이 제공됩니다:
```
https://mlb-a2a-server-xxxxx.vercel.app
```

## 🔗 서버 연결

### MCP 서버 연결
```python
# mlb-api-mcp 설정
MCP_SERVER_URL = "https://mlb-mcp-server-xxxxx.vercel.app/mcp"
```

### A2A 서버 연결
```python
# A2A 클라이언트 설정
A2A_SERVER_URL = "https://mlb-a2a-server-xxxxx.vercel.app"
```

## 📊 API 엔드포인트

### MCP 서버
- `GET /mcp`: 서버 상태 확인
- `POST /mcp`: MCP 통신

### A2A 서버
- `GET /`: 에이전트 카드
- `GET /a2a`: 서버 상태 확인
- `POST /a2a`: A2A 통신

## 🧪 테스트

### 1. MCP 서버 테스트
```bash
curl https://mlb-mcp-server-xxxxx.vercel.app/mcp
```

### 2. A2A 서버 테스트
```bash
curl https://mlb-a2a-server-xxxxx.vercel.app/
```

## ⚠️ 주의사항

### Vercel 제한사항
- **실행 시간**: 최대 10초 (Hobby 플랜), 60초 (Pro 플랜)
- **메모리**: 최대 1024MB
- **파일 크기**: 최대 50MB
- **동시 실행**: 제한적

### 권장사항
- **MCP 서버**: 간단한 요청만 처리
- **A2A 서버**: 에이전트 카드 제공 및 기본 통신
- **복잡한 AI 처리**: 별도 서버에서 처리

## 🔄 업데이트

### 코드 수정 후 재배포
```bash
vercel --prod
```

### 환경변수 수정
Vercel 대시보드 → Settings → Environment Variables에서 수정

## 📞 지원

문제가 발생하면:
1. Vercel 대시보드의 Function Logs 확인
2. 로컬에서 `vercel dev`로 테스트
3. Vercel Discord 커뮤니티 문의

## 🎯 다음 단계

1. **로컬 테스트**: `vercel dev`로 로컬에서 테스트
2. **배포**: `vercel --prod`로 프로덕션 배포
3. **연결**: 클라이언트에서 새로운 URL로 연결
4. **모니터링**: Vercel 대시보드에서 성능 모니터링 