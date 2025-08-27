# MLB 이적 전문 에이전트 (MLB Transfer Specialist Agent)

## 🏟️ 프로젝트 개요

MLB 선수 이적, FA 시장, 팀 전략을 전문적으로 분석하는 AI 에이전트입니다. 
**LangGraph create_react_agent**를 활용한 **프롬프트 기반 상황별 맞춤형 응답 시스템**으로 구현되어 있으며, 
사용자의 의도에 따라 구단 관계자, 선수, 팬 각각의 관점에서 최적화된 분석과 제안을 제공합니다.

## 🌟 주요 특징

### 🔄 프롬프트 기반 상황별 맞춤형 응답
- **구단 관계자 플로우**: 선수 영입 제안, 팀 약점 분석, 연봉 규모 검토
- **선수 플로우**: 이적 필요성 제시, 적합한 팀 탐색, 이적 설득
- **팬 플로우**: 감정 공감, 논리적 이유 설명, 새로운 비전 제시

### 📊 현재 시점 가치 평가 (모든 플로우 공통)
- 최신 성적 추이와 세이버메트릭스 기반
- 객관적이고 신뢰할 수 있는 데이터 분석
- 실시간 업데이트되는 선수 및 팀 정보

### 🛠️ 기술 스택
- **LangGraph**: create_react_agent 기반 안정적인 에이전트 실행
- **LangChain**: Anthropic Claude 모델 통합
- **프롬프트 시스템**: 상황별 맞춤형 응답을 위한 구조화된 프롬프트
- **MCP (Model Context Protocol)**: mlb-api-mcp 툴 통합
- **FastAPI**: A2A (Agent-to-Agent) 서버
- **Python 3.11+**: 비동기 처리 및 타입 힌트

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
# uv를 사용한 의존성 설치
uv sync

# 또는 pip 사용
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 추가:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key_here
```

### 3. MCP 서버 실행
```bash
# mlb-api-mcp 디렉토리로 이동
cd mlb-api-mcp

# MCP 서버 실행
uv run python main.py
```

### 4. A2A 에이전트 서버 실행
```bash
# mlb_agent 디렉토리에서
uv run python server.py
```

### 5. 테스트 실행
```bash
# 간단한 테스트
uv run python simple_test.py

# 전체 테스트
uv run python test_client.py
```

## 🔧 사용법

### 기본 사용법
```python
from agent_executor import MLBTransferAgent

# 에이전트 인스턴스 생성
agent = MLBTransferAgent()

# 구단 관계자 플로우
response = await agent.invoke("양키스가 투수진을 보강하고 싶은데, 어떤 선수를 영입하면 좋을까요?")

# 선수 플로우
response = await agent.invoke("커리어 발전을 위해 이적을 고려하고 있어요")

# 팬 플로우
response = await agent.invoke("우리 팀 선수가 떠나는 이유를 설명해주세요")
```

### 플로우별 응답 예시

#### 🏟️ 구단 관계자 플로우
```
🏟️ **구단 영입 제안서**

📊 **현재 시점 가치 평가 완료**
- 분석 방법: 최신 성적 추이와 세이버메트릭스 기반
- 분석 시점: 2024년 현재

🎯 **영입 제안**
- 목표 포지션: Starting Pitcher
- 기대 기여도: 선발 로테이션 3-4번
- 계약 조건: 3년 $45M
- 제안 이유: 팀의 투수진 보강과 경험 있는 선수 영입
```

#### ⚾ 선수 플로우
```
⚾ **커리어 발전 상담 결과**

📊 **현재 시점 가치 평가 완료**
- 분석 방법: 최신 성적 추이와 세이버메트릭스 기반
- 분석 시점: 2024년 현재

🔄 **이적 필요성**
현재 팀에서의 역할 한계, 새로운 도전 기회

🏆 **최적 이적 후보**
- 추천 팀: 다저스
- 역할: 주전 선수
- 기회: 포스트시즌 경험, 큰 시장에서의 활약
```

#### 💙 팬 플로우
```
💙 **팬을 위한 이적 설명**

📊 **현재 시점 가치 평가 완료**
- 분석 방법: 최신 성적 추이와 세이버메트릭스 기반
- 분석 시점: 2024년 현재

💭 **팬 감정 공감**
아쉬움과 이해, 새로운 응원 대상

🧠 **이적의 논리적 이유**
팀 재건 계획, 선수 커리어 발전
```

## 🏗️ 아키텍처

### 프롬프트 시스템 구조
```
[시작] → [사용자 메시지 분석] → [적절한 프롬프트 선택] → [create_react_agent 실행] → [응답 생성] → [종료]
                ↓
        [구단 관계자] [선수] [팬]
            ↓           ↓      ↓
        [영입 제안] [커리어 상담] [이적 설명]
            ↓           ↓      ↓
        [최종 응답 생성 및 전송]
```

### 주요 컴포넌트
- **MLBTransferAgent**: 핵심 에이전트 클래스
- **프롬프트 시스템**: 상황별 맞춤형 응답을 위한 구조화된 프롬프트
- **create_react_agent**: 안정적인 에이전트 실행 엔진
- **MCPToolWrapper**: MCP 툴을 LangChain 형식으로 변환
- **MLBTransferAgentExecutor**: A2A 프로토콜 실행자

### 프롬프트 파일 구조
```
prompts/
├── system_prompt.txt      # 전체 시스템 프롬프트
├── club_official_prompt.txt  # 구단 관계자 플로우
├── player_prompt.txt      # 선수 플로우
└── fan_prompt.txt         # 팬 플로우
```

## 🧪 테스트

### 테스트 시나리오
1. **구단 관계자 플로우**: 선수 영입 문의
2. **선수 플로우**: 커리어 발전 상담
3. **팬 플로우**: 이적 이유 문의
4. **현재 가치 평가**: 최신 데이터 기반 분석

### 테스트 실행
```bash
# 환경 설정 테스트
uv run python simple_test.py

# 전체 플로우 테스트
uv run python test_client.py
```

## 🔍 문제 해결

### 일반적인 문제들

#### 1. 의존성 문제
```bash
# 의존성 재설치
uv sync --reinstall
```

#### 2. 환경 변수 문제
```bash
# .env 파일 확인
cat .env

# 환경 변수 로드 확인
source .env && echo $ANTHROPIC_API_KEY
```

#### 3. MCP 서버 연결 문제
```bash
# MCP 서버 상태 확인
curl http://localhost:8000/health

# 포트 사용 확인
lsof -i :8000
```

#### 4. 프롬프트 파일 문제
```bash
# 프롬프트 파일 확인
ls -la prompts/

# 프롬프트 내용 확인
cat prompts/system_prompt.txt
```

### 디버깅 팁
- 로그 레벨을 INFO로 설정하여 상세한 실행 과정 확인
- create_react_agent의 각 단계별 실행 상태 모니터링
- MCP 툴 래핑 과정에서의 오류 로그 확인
- 프롬프트 파일 로드 상태 확인

## 📈 향후 계획

### 단기 계획
- [ ] 더 정교한 프롬프트 엔지니어링
- [ ] 추가 MCP 툴 통합
- [ ] 성능 최적화 및 캐싱 구현

### 장기 계획
- [ ] 다국어 지원 (한국어/영어)
- [ ] 실시간 MLB 데이터 연동
- [ ] 웹 인터페이스 개발
- [ ] 모바일 앱 연동

## 🤝 기여하기

프로젝트에 기여하고 싶으시다면:
1. 이슈 등록 또는 기존 이슈 확인
2. 포크 후 기능 브랜치 생성
3. 테스트 코드 작성 및 실행
4. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 통해 연락해주세요.

---

**⚾ MLB 이적 전문 에이전트로 더 스마트한 이적 전략을 세워보세요! 🏟️**
