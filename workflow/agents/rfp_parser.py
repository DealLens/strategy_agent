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
            "requirements": """
                프로젝트 요구사항 기능 명세 기술 스펙 시스템 요구사항 
                비기능 요구사항 성능 요구사항 보안 요구사항 개발 언어 
                플랫폼 환경 인프라 요구사항 데이터베이스 요구사항 
                API 요구사항 인터페이스 요구사항
            """,
            "evaluation": """
                평가기준 평가 항목 평가 기준 평가 방법 평가 요소 
                평가 점수 평가 비율 기술 평가 가격 평가 사업수행능력 
                평가 평가 기준표 평가 기준서 평가 가중치 기술 점수 
                가격 점수 사업수행능력 점수 총점 산출 방법
            """,
            "risks": """
                리스크 위험 요소 문제점 제약사항 주의사항 
                고려사항 한계점 제약 조건 제한사항 예상 문제 
                잠재적 위험 기술적 위험 사업적 위험 계약 위험 
                일정 위험 예산 위험 품질 위험 보안 위험
            """,
            "schedule": """
                일정 스케줄 계획 일정표 마일스톤 단계별 일정 
                개발 일정 프로젝트 일정 납기 일정 제출 일정 
                시작일 완료일 기간 기한 날짜 일정 관리 
                단계별 계획 프로젝트 계획
            """,
            "budget": """
                예산 비용 가격 금액 예상 비용 총 사업비 
                단가 견적 가격 정책 가격 산정 방법 
                비용 분석 예산 계획 투자 비용 운영 비용 
                유지보수 비용 라이선스 비용
            """
        }
        tasks = {k: _fetch_docs(retriever, v) for k, v in queries.items()}
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))

    try:
        return asyncio.run(run_queries())
    except Exception as e:
        return {"error": f"RFP 검색 실패: {str(e)}"}
