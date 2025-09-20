"""
search_service.py
VectorSearchService를 감싼 고수준 검색 서비스
"""

from typing import List
from langchain.schema import Document
from server.retrieval.vector_service import VectorSearchService


class SearchService:
    def __init__(self, persist_path: str = "db/faiss_index"):
        self.vector_service = VectorSearchService(persist_path=persist_path)

    def ingest_and_index(self, topic: str, role: str = "GENERAL", max_results: int = 5) -> None:
        """
        특정 주제에 대해:
        1) 검색어 개선
        2) 웹 검색
        3) 벡터스토어 인덱싱
        """
        queries = self.vector_service.improve_search_query(topic, role=role)
        docs = self.vector_service.web_search(queries, max_results=max_results)
        self.vector_service.build_index(docs)

    def search_documents(self, query: str, k: int = 3) -> List[Document]:
        """
        벡터스토어에서 쿼리 기반 검색
        """
        return self.vector_service.search(query, k=k)

    def quick_search(self, topic: str, role: str = "GENERAL", k: int = 3) -> List[Document]:
        """
        고수준 메서드: 검색어 개선 → 웹검색 → 인덱싱 → 검색까지 한 번에
        """
        self.ingest_and_index(topic, role=role)
        return self.search_documents(topic, k=k)
