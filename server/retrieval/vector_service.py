"""
vector_service.py
검색(Query 개선 → 웹 검색 → 문서 → 벡터스토어 저장/검색) 풀 파이프라인
"""

import os
from typing import List, Literal
import streamlit as st

from langchain.schema import Document, HumanMessage, SystemMessage
from duckduckgo_search import DDGS
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS

from utils.config import get_llm


class VectorSearchService:
    def __init__(self, persist_path: str = "db/faiss_index"):
        self.persist_path = persist_path
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
        )
        self.vectorstore = None
        self.ddgs = DDGS()

    # 1. 쿼리 개선
    def improve_search_query(
        self,
        topic: str,
        role: Literal["STRATEGY", "COMPETITOR", "GENERAL"] = "GENERAL",
    ) -> List[str]:
        """LLM을 활용해 검색어 3개 생성"""
        template = (
            "'{topic}'에 대해 {perspective} 웹검색에 적합한 3개의 검색어를 제안해주세요. "
            "각 검색어는 25자 이내로 작성하고 콤마로 구분하세요. "
            "검색어만 제공하고 설명은 하지 마세요."
        )

        perspective_map = {
            "STRATEGY": "사업 전략 수립에 필요한 시장, 정책, 트렌드 정보를 찾고자 합니다.",
            "COMPETITOR": "경쟁사, 대체 서비스, 기술 비교 정보를 찾고자 합니다.",
            "GENERAL": "객관적인 사실과 정보를 찾고자 합니다.",
        }

        prompt = template.format(topic=topic, perspective=perspective_map[role])

        messages = [
            SystemMessage(content="당신은 검색 전문가입니다. 관련성 높은 검색어만 제안해주세요."),
            HumanMessage(content=prompt),
        ]

        response = get_llm().invoke(messages)
        queries = [q.strip() for q in response.content.split(",")]

        return queries[:3]

    # 2. 웹 검색 → Document 리스트 변환
    def web_search(self, queries: List[str], language: str = "ko", max_results: int = 5) -> List[Document]:
        documents = []

        for query in queries:
            try:
                results = self.ddgs.text(
                    query,
                    region=language,
                    safesearch="moderate",
                    timelimit="y",  # 최근 1년
                    max_results=max_results,
                )

                if not results:
                    continue

                for result in results:
                    title = result.get("title", "")
                    body = result.get("body", "")
                    url = result.get("href", "")

                    if body:
                        documents.append(
                            Document(
                                page_content=body,
                                metadata={
                                    "source": url,
                                    "topic": title,
                                    "query": query,
                                },
                            )
                        )
            except Exception as e:
                st.warning(f"검색 중 오류 발생: {str(e)}")

        return documents

    # 3. 벡터스토어 구축
    def build_index(self, docs: List[Document]):
        if not docs:
            raise ValueError("❌ 인덱싱할 문서가 없습니다.")
        texts = [d.page_content for d in docs]
        metadatas = [d.metadata for d in docs]
        self.vectorstore = FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)
        self.vectorstore.save_local(self.persist_path)

    def load_index(self):
        if os.path.exists(self.persist_path):
            self.vectorstore = FAISS.load_local(
                self.persist_path,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )

    # 4. 쿼리 검색
    def search(self, query: str, k: int = 3) -> List[Document]:
        if not self.vectorstore:
            self.load_index()
        if not self.vectorstore:
            raise ValueError("❌ Vectorstore가 초기화되지 않았습니다.")
        results = self.vectorstore.similarity_search(query, k=k)
        return results
