"""
main_mode.py
DealLens 실행 모드 라우터
"""

import json
from typing import Optional, List
from workflow.supervisor_agent import run_deallens_pipeline
from workflow.agents.builders.strategy_builder import run_strategy_builder
from workflow.agents.analyzers.competitor_analysis import run_competitor_analysis
from workflow.agents.parsers.rfp_parser import run_rfp_parser
from workflow.agents.analyzers.internal_rag import run_internal_rag
from workflow.agents.builders.reporter import run_reporter


def run_mode(mode: str, topic: str, companies: Optional[List[str]] = None, enable_rag: bool = True) -> str:
    """
    선택된 모드에 따라 해당 분석 에이전트를 실행합니다.

    Args:
        mode (str): 실행 모드 ("전체 파이프라인", "전략 분석", "경쟁사 분석", "RFP 파서", "내부 RAG", "리포터")
        topic (str): 분석 주제 (예: RFP 제목, 프로젝트 주제, PDF 파일 경로)
        enable_rag (bool): RAG 사용 여부

    Returns:
        str: 분석 결과 텍스트
    """

    if mode == "전체 파이프라인":
        # DealLens 슈퍼바이저를 통한 전체 파이프라인 실행
        try:
            # 사용자 프롬프트 추출 (topic에 포함된 경우)
            user_prompt = None
            if "사용자 추가 요청사항:" in topic:
                parts = topic.split("사용자 추가 요청사항:")
                topic = parts[0].strip()
                user_prompt = parts[1].strip() if len(parts) > 1 else None
            
            result = run_deallens_pipeline(topic, companies=companies, user_prompt=user_prompt)
            if result.get("error"):
                return f"❌ 오류: {result['error']}"
            
            # 결과를 보기 좋게 포맷팅
            output = f"# 🚀 DealLens 전체 파이프라인 분석 결과\n\n"
            
            # 사용자 프롬프트가 있으면 표시
            if user_prompt:
                output += f"## 💬 사용자 추가 요청사항\n"
                output += f"{user_prompt}\n\n"
            
            output += f"## 📋 RFP 요구사항\n"
            for req in result["artifacts"]["A"].get("requirements", []):
                output += f"- {req}\n"
            
            output += f"\n## 🎯 내부 역량 매칭\n"
            for match in result["artifacts"]["B"].get("matches", []):
                output += f"- {match}\n"
            
            output += f"\n## 🚀 제안 전략\n"
            for action in result["artifacts"]["D"].get("actions", []):
                output += f"- {action}\n"
            
            output += f"\n## 📊 상세 보고서\n"
            output += result["deal_brief"]
            
            return output
            
        except Exception as e:
            return f"❌ 파이프라인 실행 중 오류가 발생했습니다: {str(e)}"

    elif mode == "전략 분석":
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
