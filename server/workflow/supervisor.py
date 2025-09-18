from agents.rfp_parser import RFPParserAgent
from agents.internal_rag import InternalRAGAgent
from agents.competitor_analysis import CompetitorAnalysisAgent
from agents.strategy_builder import StrategyBuilderAgent
from agents.reporter import ReporterAgent


class Supervisor:
    def __init__(self):
        # 에이전트 초기화
        self.agents = {
            "rfp": RFPParserAgent(),
            "rag": InternalRAGAgent(),
            "competitor": CompetitorAnalysisAgent(),
            "strategy": StrategyBuilderAgent(),
            "reporter": ReporterAgent(),
        }

    def route(self, task: str, user_input: str):
        """
        task 키워드에 따라 적절한 에이전트를 실행합니다.
        세션 캐시는 사용하지 않고, 단순 실행 후 결과만 반환합니다.
        """
        if "요구사항" in task or "RFP" in task:
            return self.agents["rfp"].run(user_input)
        elif "매칭" in task or "내부" in task:
            return self.agents["rag"].run(user_input)
        elif "경쟁사" in task:
            return self.agents["competitor"].run(user_input)
        elif "전략" in task:
            return self.agents["strategy"].run(user_input)
        elif "보고서" in task or "리포트" in task:
            return self.agents["reporter"].run(user_input)
        else:
            return f" 지원하지 않는 작업입니다: {task}"


if __name__ == "__main__":
    sup = Supervisor()

    # 전체 파이프라인 실행 (데모용)
    reqs = sup.route("요구사항", "sample.pdf")
    print("1. 요구사항:", reqs)

    rag = sup.route("매칭", str(reqs))
    print("2. 내부 매칭:", rag)

    comp = sup.route("경쟁사", "삼성 SDS")
    print("3. 경쟁사 분석:", comp)

    strat = sup.route("전략", f"{reqs}, {rag}, {comp}")
    print("4. 전략:", strat)

    report = sup.route("보고서", str(strat))
    print("5.최종 보고서:", report)
