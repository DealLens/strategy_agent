from langchain_core.tools import tool
from ..base_agent import BaseAgent
import json
from typing import Dict, List, Any
# B. 내부지식 매칭

@tool
def match_internal_requirements(requirements: list) -> dict:
    """내부 프로젝트/솔루션과 요구사항 매칭"""
    # 실제 RAG 검색 로직 구현
    internal_knowledge = {
        "projects": [
            {
                "name": "스마트시티 플랫폼 구축",
                "description": "IoT 기반 도시 인프라 관리 시스템",
                "technologies": ["IoT", "클라우드", "데이터 분석"],
                "capabilities": ["실시간 모니터링", "예측 분석", "자동화"]
            },
            {
                "name": "AI 기반 보안 솔루션",
                "description": "머신러닝을 활용한 이상행위 탐지 시스템",
                "technologies": ["AI/ML", "보안", "실시간 처리"],
                "capabilities": ["위협 탐지", "자동 대응", "패턴 분석"]
            },
            {
                "name": "클라우드 마이그레이션 프로젝트",
                "description": "레거시 시스템의 클라우드 전환",
                "technologies": ["클라우드", "마이크로서비스", "DevOps"],
                "capabilities": ["시스템 전환", "성능 최적화", "보안 강화"]
            }
        ],
        "solutions": [
            {
                "name": "데이터 플랫폼",
                "description": "빅데이터 처리 및 분석 플랫폼",
                "technologies": ["빅데이터", "분석", "시각화"],
                "capabilities": ["데이터 수집", "ETL", "분석", "리포팅"]
            }
        ]
    }
    
    matches = []
    gaps = []
    
    # 요구사항과 내부 지식 매칭
    for req in requirements:
        req_lower = req.lower()
        matched = False
        
        for project in internal_knowledge["projects"]:
            for tech in project["technologies"]:
                if tech.lower() in req_lower:
                    matches.append({
                        "requirement": req,
                        "project": project["name"],
                        "match_type": "기술 스택",
                        "confidence": 0.8
                    })
                    matched = True
                    break
            
            if not matched:
                for capability in project["capabilities"]:
                    if capability.lower() in req_lower:
                        matches.append({
                            "requirement": req,
                            "project": project["name"],
                            "match_type": "기능",
                            "confidence": 0.7
                        })
                        matched = True
                        break
        
        if not matched:
            gaps.append({
                "requirement": req,
                "gap_type": "기술 부족",
                "priority": "높음"
            })
    
    return {
        "matches": matches,
        "gaps": gaps,
        "total_requirements": len(requirements),
        "match_rate": len(matches) / len(requirements) if requirements else 0,
        "internal_knowledge_used": True
    }

class InternalRAGAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are an internal RAG agent. Match requirements with internal projects.",
            tools=[match_internal_requirements]
        )

def run_internal_rag(topic: str) -> str:
    """내부 RAG 실행 함수"""
    agent = InternalRAGAgent()
    return agent.run(f"다음 주제에 대한 내부 프로젝트 매칭을 수행해줘: {topic}")

if __name__ == "__main__":
    agent = InternalRAGAgent()
    output = agent.run("요구사항 리스트를 내부 프로젝트와 매칭해줘.")
    print(output)
