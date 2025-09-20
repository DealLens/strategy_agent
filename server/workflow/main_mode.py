"""
main_mode.py
DealLens 실행 모드 라우터
"""

# 필요한 에이전트 불러오기
from server.workflow.agents.builders.strategy_builder import run_strategy_builder
from server.workflow.agents.analyzers.competitor_analysis import run_competitor_analysis
from server.workflow.agents.parsers.rfp_parser import run_rfp_parser
from server.workflow.agents.analyzers.internal_rag import run_internal_rag
from server.workflow.agents.builders.reporter import run_reporter


def run_mode(mode: str, topic: str, enable_rag: bool = True) -> str:
    """
    선택된 모드에 따라 해당 분석 에이전트를 실행합니다.

    Args:
        mode (str): 실행 모드 ("전략 분석", "경쟁사 분석", "RFP 파서", "내부 RAG", "리포터")
        topic (str): 분석 주제 (예: RFP 제목, 프로젝트 주제)
        enable_rag (bool): RAG 사용 여부

    Returns:
        str: 분석 결과 텍스트
    """

    if mode == "전략 분석":
        # 전략 Builder → 내부 RAG/경쟁사/리스크 등을 종합
        return run_strategy_builder(topic, enable_rag=enable_rag)

    elif mode == "경쟁사 분석":
        # 경쟁사 SWOT, 레퍼런스 기반 분석
        return run_competitor_analysis(topic)

    elif mode == "RFP 파서":
        # 문서에서 요구사항, 평가기준 자동 추출
        return run_rfp_parser(topic)

    elif mode == "내부 RAG":
        # 내부 프로젝트/성과 데이터와 매칭
        return run_internal_rag(topic)

    elif mode == "리포터":
        # 최종 보고서 형태로 정리
        return run_reporter(topic)

    else:
        return f"❌ 지원하지 않는 모드입니다: {mode}"
