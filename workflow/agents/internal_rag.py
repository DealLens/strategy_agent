from langchain_core.tools import tool
from retrivers.internal_retriever import build_internal_retriever

@tool
def internal_rag(requirements: list) -> dict:
    """
    내부 데이터(JSON)를 VectorStoreRetriever에 임베딩 후
    요구사항별 매칭 결과를 반환합니다.
    """
    try:
        retriever = build_internal_retriever()
    except Exception as e:
        return {"error": f"Internal retriever 생성 실패: {str(e)}"}

    matches = []
    for req in requirements:
        try:
            related_docs = retriever.get_relevant_documents(req)
            matches.append({
                "requirement": req,
                "related": [d.page_content for d in related_docs]
            })
        except Exception as e:
            matches.append({
                "requirement": req,
                "error": f"검색 실패: {str(e)}"
            })

    return {"internal_matches": matches}


# 단독 실행 디버깅용
if __name__ == "__main__":
    sample_requirements = ["AI 성능 검증", "보안 인증", "SLA 99.9%"]
    result = internal_rag.run(sample_requirements)
    print("📋 Internal RAG 결과:")
    for r in result["internal_matches"]:
        print(f"- {r['requirement']}: {r.get('related', [])}")
