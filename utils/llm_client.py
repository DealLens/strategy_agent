"""
통합 LLM 클라이언트 관리 모듈
- 중복 초기화 제거
- 일관된 모델 설정
- 에러 핸들링 강화
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class LLMClient:
    """통합 LLM 클라이언트"""
    
    def __init__(self):
        self.client = None
        self.model_config = {}
        self._initialize_client()
    
    def _initialize_client(self):
        """LLM 클라이언트 초기화"""
        try:
            # Azure OpenAI 우선
            if os.getenv("AOAI_API_KEY") and os.getenv("AOAI_ENDPOINT"):
                from openai import AzureOpenAI
                self.client = AzureOpenAI(
                    api_key=os.getenv("AOAI_API_KEY"),
                    api_version=os.getenv("AOAI_API_VERSION", "2024-02-15-preview"),
                    azure_endpoint=os.getenv("AOAI_ENDPOINT"),
                )
                self.model_config = {
                    "primary": os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o"),
                    "secondary": os.getenv("AOAI_DEPLOY_GPT4O_MINI", "gpt-4o-mini"),
                    "type": "azure"
                }
                print("✅ LLM Client: Azure OpenAI 초기화 완료")
                
            # OpenAI 대안
            elif os.getenv("OPENAI_API_KEY"):
                from openai import OpenAI
                self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.model_config = {
                    "primary": "gpt-4o",
                    "secondary": "gpt-4o-mini", 
                    "type": "openai"
                }
                print("✅ LLM Client: OpenAI 초기화 완료")
                
            else:
                print("⚠️ LLM Client: API 키 없음 → 기본 모드")
                self._print_api_setup_guide()
                
        except Exception as e:
            print(f"❌ LLM Client 초기화 실패: {e}")
            self.client = None
    
    def _print_api_setup_guide(self):
        """API 키 설정 가이드 출력"""
        print("\n" + "="*60)
        print("🔑 AI 모델 API 키 설정이 필요합니다")
        print("="*60)
        print("1. 프로젝트 루트에 .env 파일을 생성하세요")
        print("2. 다음 중 하나의 설정을 추가하세요:")
        print()
        print("   [Azure OpenAI 설정 - 권장]")
        print("   AOAI_API_KEY=your_azure_openai_api_key")
        print("   AOAI_ENDPOINT=https://your-resource-name.openai.azure.com/")
        print("   AOAI_API_VERSION=2024-02-15-preview")
        print("   AOAI_DEPLOY_GPT4O=gpt-4o")
        print("   AOAI_DEPLOY_GPT4O_MINI=gpt-4o-mini")
        print()
        print("   [또는 OpenAI 설정]")
        print("   OPENAI_API_KEY=your_openai_api_key")
        print()
        print("3. API 키를 발급받으려면:")
        print("   - Azure OpenAI: https://portal.azure.com")
        print("   - OpenAI: https://platform.openai.com")
        print()
        print("⚠️  API 키 없이는 AI 기반 전략 분석이 불가능하며,")
        print("   기본 템플릿 기반 전략만 생성됩니다.")
        print("="*60 + "\n")
    
    def is_available(self) -> bool:
        """LLM 사용 가능 여부"""
        return self.client is not None
    
    def get_model(self, use_secondary: bool = False) -> str:
        """모델명 반환"""
        if not self.model_config:
            return "gpt-4o"  # 기본값
            
        key = "secondary" if use_secondary else "primary"
        return self.model_config.get(key, "gpt-4o")
    
    def call_llm(self, prompt: str, model: Optional[str] = None, 
                 temperature: float = 0.3, max_tokens: Optional[int] = None,
                 use_secondary: bool = False) -> Optional[str]:
        """LLM 호출"""
        if not self.client:
            return None
            
        try:
            model_name = model or self.get_model(use_secondary)
            
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ LLM 호출 실패: {e}")
            return None
    
    def parse_list_response(self, response: str, category: str = "") -> List[str]:
        """다양한 포맷의 리스트 응답 파싱"""
        if not response:
            return []
        
        lines = []
        
        # 다양한 포맷 지원
        patterns = [
            r'^[-•]\s*(.+)$',           # - 또는 • 로 시작
            r'^\d+[\.\)]\s*(.+)$',      # 숫자. 또는 숫자) 로 시작
            r'^\*\s*(.+)$',             # * 로 시작
            r'^>\s*(.+)$',              # > 로 시작
        ]
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # 패턴 매칭 시도
            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    content = match.group(1).strip()
                    if content and len(content) > 3:  # 너무 짧은 항목 제외
                        lines.append(content)
                    break
        
        # 패턴 매칭이 안 되면 단순히 줄바꿈으로 분리
        if not lines:
            for line in response.split('\n'):
                line = line.strip()
                if line and len(line) > 3:
                    lines.append(line)
        
        return lines[:10]  # 최대 10개
    
    def parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """JSON 응답 파싱 (강화된 버전)"""
        if not response:
            return None
        
        # 디버깅을 위한 로그
        print(f"[JSON 파싱] 입력 텍스트 길이: {len(response)}")
        print(f"[JSON 파싱] 입력 텍스트 시작: {response[:200]}...")
        
        # 1. 직접 JSON 파싱 시도
        try:
            result = json.loads(response)
            print("[JSON 파싱] 직접 파싱 성공")
            return result
        except json.JSONDecodeError as e:
            print(f"[JSON 파싱] 직접 파싱 실패: {e}")
        
        # 2. 텍스트 정리 후 재시도
        cleaned_response = response.strip()
        
        # 불필요한 앞뒤 텍스트 제거
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:].strip()
        elif cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:].strip()
        
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3].strip()
        
        # 첫 번째 { 부터 마지막 } 까지 추출
        start_idx = cleaned_response.find('{')
        end_idx = cleaned_response.rfind('}')
        
        if start_idx >= 0 and end_idx > start_idx:
            cleaned_response = cleaned_response[start_idx:end_idx+1]
        
        try:
            result = json.loads(cleaned_response)
            print("[JSON 파싱] 정리 후 파싱 성공")
            return result
        except json.JSONDecodeError as e:
            print(f"[JSON 파싱] 정리 후 파싱 실패: {e}")
        
        # 3. JSON 블록 추출 시도 (정규식)
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[\s\S]*?\})',  # 기본 JSON 객체 (non-greedy)
        ]
        
        for i, pattern in enumerate(json_patterns):
            matches = re.findall(pattern, response, re.DOTALL)
            for j, match in enumerate(matches):
                try:
                    result = json.loads(match)
                    print(f"[JSON 파싱] 패턴 {i+1} 매치 {j+1} 파싱 성공")
                    return result
                except json.JSONDecodeError as e:
                    print(f"[JSON 파싱] 패턴 {i+1} 매치 {j+1} 파싱 실패: {e}")
                    continue
        
        # 4. 부분 JSON 추출 (첫 번째 완전한 객체)
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(response):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    try:
                        json_str = response[start_idx:i+1]
                        result = json.loads(json_str)
                        print("[JSON 파싱] 중괄호 추적 파싱 성공")
                        return result
                    except json.JSONDecodeError as e:
                        print(f"[JSON 파싱] 중괄호 추적 파싱 실패: {e}")
                        continue
        
        # 5. 마지막 시도: 응답에서 JSON 유사 부분 추출
        try:
            # 응답에서 JSON 키워드가 포함된 부분 찾기
            lines = response.split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('{') or '"summary"' in line or '"focus"' in line:
                    in_json = True
                
                if in_json:
                    json_lines.append(line)
                
                if in_json and line.endswith('}') and line.count('}') >= line.count('{'):
                    break
            
            if json_lines:
                json_text = '\n'.join(json_lines)
                result = json.loads(json_text)
                print("[JSON 파싱] 키워드 기반 추출 파싱 성공")
                return result
        except Exception as e:
            print(f"[JSON 파싱] 키워드 기반 추출 파싱 실패: {e}")
        
        print("[JSON 파싱] 모든 파싱 시도 실패")
        return None
    
    def filter_content(self, items: List[str], category: str = "") -> List[str]:
        """내용 필터링 (불필요한 항목 제거)"""
        if not items:
            return []
        
        # 제외할 키워드들
        exclude_keywords = {
            "목차", "첨부", "서약서", "조견표", "제안서 작성", "기재사항", "제출",
            "차례", "구성", "개요", "요약", "결론", "참고", "부록",
            "작성일", "작성자", "검토자", "승인자", "날짜", "시간"
        }
        
        filtered = []
        for item in items:
            # 너무 짧은 항목 제외
            if len(item.strip()) < 5:
                continue
            
            # 제외 키워드가 포함된 항목 제외
            if any(keyword in item for keyword in exclude_keywords):
                continue
            
            # 의미있는 내용만 포함
            if any(keyword in item.lower() for keyword in 
                   ["요구", "기능", "기술", "보안", "개발", "시스템", "서비스", "데이터", "ai", "클라우드"]):
                filtered.append(item.strip())
        
        return filtered[:8]  # 최대 8개

# 전역 클라이언트 인스턴스
llm_client = LLMClient()

# 편의 함수들
def get_llm_client() -> LLMClient:
    """LLM 클라이언트 인스턴스 반환"""
    return llm_client

def is_llm_available() -> bool:
    """LLM 사용 가능 여부"""
    return llm_client.is_available()

def call_llm(prompt: str, **kwargs) -> Optional[str]:
    """LLM 호출 편의 함수"""
    return llm_client.call_llm(prompt, **kwargs)

def parse_list_response(response: str, category: str = "") -> List[str]:
    """리스트 응답 파싱 편의 함수"""
    return llm_client.parse_list_response(response, category)

def parse_json_response(response: str) -> Optional[Dict[str, Any]]:
    """JSON 응답 파싱 편의 함수"""
    return llm_client.parse_json_response(response)

def filter_content(items: List[str], category: str = "") -> List[str]:
    """내용 필터링 편의 함수"""
    return llm_client.filter_content(items, category)
