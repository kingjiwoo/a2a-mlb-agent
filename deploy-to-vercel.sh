#!/bin/bash

# Vercel로 MCP 서버와 A2A 서버 배포 스크립트

echo "🚀 Vercel 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수 정의
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vercel CLI 설치 확인
if ! command -v vercel &> /dev/null; then
    print_error "Vercel CLI가 설치되지 않았습니다."
    echo "다음 명령어로 설치하세요:"
    echo "npm install -g vercel"
    exit 1
fi

print_status "Vercel CLI 확인 완료"

# 로그인 상태 확인
if ! vercel whoami &> /dev/null; then
    print_warning "Vercel에 로그인되지 않았습니다."
    echo "로그인을 진행합니다..."
    vercel login
fi

print_status "Vercel 로그인 확인 완료"

# MCP 서버 배포
echo ""
echo "📡 MCP 서버 배포 중..."
cd vercel-mcp-server

if [ ! -f "vercel.json" ]; then
    print_error "vercel.json 파일을 찾을 수 없습니다."
    exit 1
fi

print_status "MCP 서버 Vercel 프로젝트 초기화 중..."
vercel --yes

print_status "MCP 서버 프로덕션 배포 중..."
vercel --prod --yes

MCP_URL=$(vercel ls | grep "mlb-mcp-server" | awk '{print $2}')
print_status "MCP 서버 배포 완료: $MCP_URL"

cd ..

# A2A 서버 배포
echo ""
echo "🤖 A2A 서버 배포 중..."
cd vercel-a2a-server

if [ ! -f "vercel.json" ]; then
    print_error "vercel.json 파일을 찾을 수 없습니다."
    exit 1
fi

print_status "A2A 서버 Vercel 프로젝트 초기화 중..."
vercel --yes

print_status "A2A 서버 프로덕션 배포 중..."
vercel --prod --yes

A2A_URL=$(vercel ls | grep "mlb-a2a-server" | awk '{print $2}')
print_status "A2A 서버 배포 완료: $A2A_URL"

cd ..

# 배포 결과 요약
echo ""
echo "🎉 배포 완료!"
echo "=================================="
echo "📡 MCP 서버: $MCP_URL"
echo "🤖 A2A 서버: $A2A_URL"
echo "=================================="

# 환경변수 설정 안내
echo ""
print_warning "환경변수 설정이 필요합니다:"
echo "Vercel 대시보드에서 다음 환경변수를 설정하세요:"
echo "- ANTHROPIC_API_KEY: Anthropic API 키"
echo "- ANTHROPIC_MODEL: claude-3-5-sonnet-20241022"

# 테스트 명령어 안내
echo ""
echo "🧪 테스트 명령어:"
echo "curl $MCP_URL/mcp"
echo "curl $A2A_URL/"

print_status "배포 스크립트 실행 완료!" 