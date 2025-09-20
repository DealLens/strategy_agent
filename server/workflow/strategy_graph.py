from langgraph.graph import StateGraph, END
from workflow.state import StrategyState
from workflow.agents.rfp_parser import RFPParser
from workflow.agents.internal_rag import InternalRAG
from workflow.agents.competitor_analysis import CompetitorAnalysis
from workflow.agents.strategy_builder import StrategyBuilder
from workflow.agents.reporter import Reporter


def create_strategy_graph():
    """DealLens 전략분석 그래프 정의"""
    workflow = StateGraph(StrategyState)

    # 에이전트 초기화
    rfp_parser = RFPParser()
    internal_rag = InternalRAG()
    competitor = CompetitorAnalysis()
    strategy_builder = StrategyBuilder()
    reporter = Reporter()

    # 노드 추가
    workflow.add_node("RFP_PARSER", rfp_parser.run)
    workflow.add_node("INTERNAL_RAG", internal_rag.run)
    workflow.add_node("COMPETITOR", competitor.run)
    workflow.add_node("STRATEGY", strategy_builder.run)
    workflow.add_node("REPORT", reporter.run)

    # 실행 순서
    workflow.add_edge("RFP_PARSER", "INTERNAL_RAG")
    workflow.add_edge("INTERNAL_RAG", "COMPETITOR")
    workflow.add_edge("COMPETITOR", "STRATEGY")
    workflow.add_edge("STRATEGY", "REPORT")
    workflow.add_edge("REPORT", END)

    # 시작점
    workflow.set_entry_point("RFP_PARSER")

    return workflow.compile()
