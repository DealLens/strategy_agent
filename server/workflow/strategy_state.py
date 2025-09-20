# LangGraph 상태 정의 - 전략분석(RAG 포함) 관련 필드 추가
from typing import Dict, List, TypedDict


class StageType:
    """전략분석 파이프라인 단계 정의"""
    RFP = "RFP_PARSER"
    INTERNAL_RAG = "INTERNAL_RAG"
    COMPETITOR = "COMPETITOR"
    STRATEGY = "STRATEGY"
    REPORT = "REPORT"

    @classmethod
    def to_korean(cls, stage: str) -> str:
        if stage == cls.RFP:
            return "RFP 파서"
        elif stage == cls.INTERNAL_RAG:
            return "내부 RAG"
        elif stage == cls.COMPETITOR:
            return "경쟁사 분석"
        elif stage == cls.STRATEGY:
            return "전략 수립"
        elif stage == cls.REPORT:
            return "리포트 작성"
        else:
            return stage


class StrategyState(TypedDict, total=False):
    """
    DealLens 전략분석 파이프라인 상태 정의
    각 노드 실행 시 필요한 값/결과를 누적 저장
    """

    # 공통 입력
    topic: str                      # 분석 주제 (예: "스마트시티 구축 RFP")
    prev_node: str                  # 이전 실행 노드
    docs: Dict[str, List]           # RAG 검색 결과 (쿼리별 문서 리스트)
    contexts: Dict[str, str]        # 문맥 정리 (예: "보안 요구사항": "검색 결과 요약")

    # RFP 파서 단계
    requirements: List[str]         # RFP 요구사항 리스트
    evaluation_criteria: List[str]  # 평가 기준 리스트

    # 내부 RAG 단계
    internal_refs: Dict[str, str]   # 내부 프로젝트/사례 레퍼런스

    # 경쟁사 분석 단계
    competitor_info: Dict[str, str] # 경쟁사 요약 정보
    risks: List[str]                # 리스크 요인

    # 전략 수립 단계
    strategy: str                   # 종합된 전략 제안

    # 리포트 단계
    report: str                     # 최종 보고서 텍스트
