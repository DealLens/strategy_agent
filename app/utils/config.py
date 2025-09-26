"""
설정 관리 모듈
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    """애플리케이션 설정 클래스"""
    
    def __init__(self):
        # OpenAI API 키
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        
        # Azure OpenAI 설정
        self.AOAI_API_KEY = os.getenv("AOAI_API_KEY")
        self.AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
        self.AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2024-02-15-preview")
        
        # 기타 설정
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        # API 키 검증
        self._validate_api_keys()
    
    def _validate_api_keys(self):
        """API 키 유효성 검증"""
        if not self.OPENAI_API_KEY and not self.AOAI_API_KEY:
            print("⚠️ API 키가 설정되지 않았습니다. 환경변수를 확인해주세요.")
            print("   Windows: set OPENAI_API_KEY=your_key_here")
            print("   Linux/Mac: export OPENAI_API_KEY=your_key_here")
        
        if self.OPENAI_API_KEY:
            print(f"✅ OpenAI API 키가 설정되었습니다: {self.OPENAI_API_KEY[:20]}...")
        
        if self.AOAI_API_KEY:
            print(f"✅ Azure OpenAI API 키가 설정되었습니다: {self.AOAI_API_KEY[:20]}...")
    
    def get_available_llm_config(self):
        """사용 가능한 LLM 설정 반환"""
        if self.AOAI_API_KEY and self.AOAI_ENDPOINT:
            return {
                "type": "azure",
                "api_key": self.AOAI_API_KEY,
                "endpoint": self.AOAI_ENDPOINT,
                "api_version": self.AOAI_API_VERSION
            }
        elif self.OPENAI_API_KEY:
            return {
                "type": "openai",
                "api_key": self.OPENAI_API_KEY
            }
        else:
            return None

# 전역 설정 인스턴스
config = Config()
