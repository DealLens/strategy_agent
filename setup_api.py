#!/usr/bin/env python3
"""
API 키 설정 도우미
"""

import os

print("🔑 API 키 설정 도우미")
print("=" * 50)

print("\n📋 현재 상황:")
print("- API 키가 설정되지 않아 더미 모드로 동작 중")
print("- 실제 AI 분석을 위해서는 API 키가 필요함")

print("\n🚀 해결 방법:")

print("\n1️⃣ 환경변수로 임시 설정 (현재 세션에서만 유효):")
print("   PowerShell:")
print("   $env:OPENAI_API_KEY='your_actual_api_key_here'")
print("   ")
print("   CMD:")
print("   set OPENAI_API_KEY=your_actual_api_key_here")

print("\n2️⃣ .env 파일에 영구 설정:")
print("   .env 파일을 열어서:")
print("   OPENAI_API_KEY=your_actual_api_key_here")
print("   로 수정")

print("\n3️⃣ OpenAI API 키 발급:")
print("   1. https://platform.openai.com/api-keys 방문")
print("   2. 회원가입 후 API 키 발급")
print("   3. 무료 크레딧 제공 (약 $5)")

print("\n4️⃣ Azure OpenAI 사용 시:")
print("   AOAI_API_KEY=your_azure_key")
print("   AOAI_ENDPOINT=https://your-resource.openai.azure.com/")

print("\n✅ 설정 후 확인:")
print("   python -c \"from workflow.supervisor import supervisor; print('API 키 설정됨')\"")

print("\n⚠️ 주의사항:")
print("- API 키는 절대 공개하지 마세요")
print("- .env 파일은 .gitignore에 포함되어 있어야 합니다")
print("- 무료 크레딧을 사용하더라도 사용량을 모니터링하세요")

# 현재 환경변수 상태 확인
print(f"\n🔍 현재 상태:")
print(f"OPENAI_API_KEY: {'설정됨' if os.getenv('OPENAI_API_KEY') else '없음'}")
print(f"AOAI_API_KEY: {'설정됨' if os.getenv('AOAI_API_KEY') else '없음'}")

if not os.getenv('OPENAI_API_KEY') and not os.getenv('AOAI_API_KEY'):
    print("\n💡 테스트용 API 키 설정 예시:")
    print("$env:OPENAI_API_KEY='sk-test1234567890abcdefghijklmnopqrstuvwxyz'")
    print("(실제 키로 교체하세요)")
