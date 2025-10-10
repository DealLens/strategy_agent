import os
from langchain_openai import AzureOpenAIEmbeddings

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv가 없어도 환경변수는 사용 가능

AOAI_DEPLOY_EMBED_3_LARGE = os.getenv("AOAI_DEPLOY_EMBED_3_LARGE", "text-embedding-3-large")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")

def get_embeddings():
    """Azure OpenAI 임베딩 객체 반환"""
    # 환경 변수 검증
    if not AOAI_API_KEY or not AOAI_ENDPOINT:
        raise ValueError(
            "Azure OpenAI 환경 변수가 설정되지 않았습니다.\n"
            "필요한 환경 변수: AOAI_API_KEY, AOAI_ENDPOINT\n"
            "설정 방법:\n"
            "  Mac/Linux: export AOAI_API_KEY='your-key'\n"
            "  Windows: set AOAI_API_KEY=your-key"
        )
    
    return AzureOpenAIEmbeddings(
        model=AOAI_DEPLOY_EMBED_3_LARGE,
        openai_api_version="2024-05-01-preview",
        api_key=AOAI_API_KEY,
        azure_endpoint=AOAI_ENDPOINT,
    )
