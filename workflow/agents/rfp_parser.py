import asyncio
from langchain_core.tools import tool
from retrivers.rfp_retriever import build_rfp_retriever

async def _fetch_docs(retriever, query: str, limit: int = 5):
    try:
        docs = await asyncio.to_thread(retriever.get_relevant_documents, query)
        return [d.page_content for d in docs[:limit]]
    except Exception as e:
        return [f"❌ 오류({query}): {str(e)}"]

@tool
def rfp_parser(pdf_path: str) -> dict:
    """
    RFP PDF를 분석하여 요구사항, 평가기준, 리스크를 추출합니다.
    내부적으로 VectorStoreRetriever를 활용하며 asyncio를 사용해 병렬 처리합니다.
    """
    try:
        retriever = build_rfp_retriever(pdf_path)
    except Exception as e:
        return {"error": f"RFP retriever 생성 실패: {str(e)}"}

    async def run_queries():
        queries = {
            "requirements": "요구사항",
            "evaluation": "평가기준",
            "risks": "리스크 OR 위험 OR 문제점",
        }
        tasks = {k: _fetch_docs(retriever, v) for k, v in queries.items()}
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))

    try:
        return asyncio.run(run_queries())
    except Exception as e:
        return {"error": f"RFP 검색 실패: {str(e)}"}
