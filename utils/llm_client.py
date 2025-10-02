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
                
        except Exception as e:
            print(f"❌ LLM Client 초기화 실패: {e}")
            self.client = None
    
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
        
        try:
            # 1. 직접 JSON 파싱 시도
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 2. JSON 블록 추출 시도 (```json ... ```)
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[\s\S]*\})',  # 기본 JSON 객체
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # 3. 부분 JSON 추출 (첫 번째 완전한 객체)
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
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
        
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
