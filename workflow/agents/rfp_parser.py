from langchain_core.tools import tool
from retrivers.rfp_retriever import build_rfp_retriever

@tool
def rfp_parser(pdf_path: str) -> dict:
    """
    RFP PDF를 분석하여 요구사항, 평가기준, 리스크를 추출합니다.
    내부적으로 VectorStoreRetriever를 활용합니다.
    """
    try:
        retriever = build_rfp_retriever(pdf_path)
    except Exception as e:
        return {"error": f"RFP retriever 생성 실패: {str(e)}"}

    try:
        requirement_docs = retriever.get_relevant_documents("요구사항")
        evaluation_docs = retriever.get_relevant_documents("평가기준")
        risk_docs = retriever.get_relevant_documents("리스크 OR 위험 OR 문제점")

        requirements = [d.page_content for d in requirement_docs[:5]]
        evaluation = [d.page_content for d in evaluation_docs[:5]]
        risks = [d.page_content for d in risk_docs[:5]]

        return {
            "requirements": requirements,
            "evaluation": evaluation,
            "risks": risks
        }
    except Exception as e:
        return {"error": f"RFP 검색 실패: {str(e)}"}


# 단독 실행 디버깅용
if __name__ == "__main__":
    sample_pdf = "data/samples/sample_rfp.pdf"
    result = rfp_parser.run(sample_pdf)
    print("📋 RFP Parser 결과:")
    print(result)
