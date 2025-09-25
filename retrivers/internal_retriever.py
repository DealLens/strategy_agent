import os
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain.docstore.document import Document
from utils.data_loader import load_internal_data

# 환경 변수
AOAI_DEPLOY_EMBED_3_LARGE = os.getenv("AOAI_DEPLOY_EMBED_3_LARGE")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")


def build_internal_retriever():
    """
    내부 JSON 데이터 기반 VectorStoreRetriever 생성
    - projects.json / modules.json / people.json / skax_case_studies.json
    """
    try:
        projects = load_internal_data("projects.json")
        modules = load_internal_data("modules.json")
        people = load_internal_data("people.json")
        case_studies = load_internal_data("skax_case_studies.json")
    except Exception as e:
        raise RuntimeError(f"내부 데이터 로드 실패: {str(e)}")

    raw_docs = []

    if projects:
        for p in projects:
            raw_docs.append(
                Document(page_content=f"프로젝트: {p.get('name')} - {p.get('description')}")
            )

    if modules:
        for m in modules:
            raw_docs.append(
                Document(page_content=f"모듈: {m.get('name')} - {m.get('description')}")
            )

    if people:
        for person in people:
            raw_docs.append(
                Document(page_content=f"인력: {person.get('name')} - {person.get('skills')}")
            )

    if case_studies:
        for c in case_studies:
            raw_docs.append(
                Document(page_content=f"케이스 스터디: {c.get('title')} - {c.get('summary')}")
            )

    if not raw_docs:
        raise ValueError("⚠️ 내부 데이터가 비어있습니다. retriever를 생성할 수 없습니다.")

    # 문서 분할
    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = splitter.split_documents(raw_docs)

    # 임베딩 모델
    embeddings = AzureOpenAIEmbeddings(
        model=AOAI_DEPLOY_EMBED_3_LARGE,
        openai_api_version="2024-05-01-preview",
        api_key=AOAI_API_KEY,
        azure_endpoint=AOAI_ENDPOINT,
    )

    # 벡터스토어 생성
    vectorstore = FAISS.from_documents(split_docs, embeddings)

    # Retriever 반환
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )
    return retriever
