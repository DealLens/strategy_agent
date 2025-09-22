"""
DealLens Supervisor Agent
Sequential pipeline execution: A(RFP Parser) → B(Internal RAG) → C(Competitor) → D(Strategy) → E(Reporter)
"""

import json
import os
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
from .agents.base_agent import BaseAgent


# Tool A: RFP Parser
@tool
def parse_rfp(pdf_path: str) -> Dict[str, List[str]]:
    """
    RFP PDF를 파싱하여 요구사항, 평가기준, 리스크를 추출합니다.
    
    Args:
        pdf_path: RFP PDF 파일 경로
        
    Returns:
        Dict with requirements, criteria, risks lists
    """
    # TODO: 실제 PDF 파싱 로직 구현 (PyPDF2, pdfplumber 등 사용)
    # 현재는 샘플 데이터 반환
    
    if not pdf_path or not os.path.exists(pdf_path):
        return {
            "requirements": [],
            "criteria": [],
            "risks": []
        }
    
    # 샘플 RFP 분석 결과
    return {
        "requirements": [
            "클라우드 인프라 구축",
            "데이터 보안 및 암호화",
            "AI/ML 기반 분석 기능",
            "실시간 모니터링 시스템",
            "모바일 앱 개발"
        ],
        "criteria": [
            "기술 적합성 (40%)",
            "가격 경쟁력 (30%)",
            "프로젝트 경험 (20%)",
            "유지보수 계획 (10%)"
        ],
        "risks": [
            "라이선스 비용 증가",
            "납기 일정 지연 가능성",
            "보안 인증 획득 지연",
            "기술 인력 부족"
        ]
    }


# Tool B: Internal RAG
@tool
def match_internal_knowledge(requirements: List[str]) -> Dict[str, List[str]]:
    """
    내부 지식베이스에서 요구사항과 매칭되는 프로젝트/솔루션을 검색합니다.
    
    Args:
        requirements: RFP에서 추출한 요구사항 리스트
        
    Returns:
        Dict with matches and references lists
    """
    # TODO: 실제 벡터 검색 로직 구현 (FAISS, Chroma 등 사용)
    # 현재는 샘플 데이터 반환
    
    if not requirements:
        return {
            "matches": [],
            "references": []
        }
    
    # 샘플 내부 매칭 결과
    return {
        "matches": [
            "스마트시티 플랫폼 구축 프로젝트 (2023)",
            "클라우드 마이그레이션 솔루션 (2022)",
            "AI 기반 데이터 분석 시스템 (2024)"
        ],
        "references": [
            "서울시 스마트시티 플랫폼 구축 사업",
            "금융권 클라우드 전환 프로젝트",
            "제조업 AI 품질관리 시스템"
        ]
    }


# Tool C: Competitor Analysis
@tool
def load_competitor_data(companies: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    경쟁사 데이터를 로드하여 프로필 정보를 반환합니다.
    
    Args:
        companies: 분석할 경쟁사 목록
        
    Returns:
        Dict with company profiles
    """
    # TODO: 실제 경쟁사 데이터베이스 연결
    # 현재는 샘플 데이터 반환
    
    if not companies:
        companies = ["삼성 SDS", "LG CNS", "포스코DX", "KT", "현대오토에버", "카카오", "CJ 올리브네트웍스"]
    
    profiles = {}
    for company in companies:
        profiles[company] = {
            "strengths": [
                "대규모 인프라 보유",
                "다양한 프로젝트 경험",
                "전문 인력 확보"
            ],
            "weaknesses": [
                "높은 비용 구조",
                "복잡한 의사결정 체계"
            ],
            "opportunities": [
                "공공 시장 확대",
                "디지털 전환 가속화"
            ],
            "threats": [
                "중소기업 경쟁 심화",
                "기술 변화 속도"
            ],
            "recent_projects": [
                "정부 클라우드 구축",
                "스마트시티 플랫폼"
            ]
        }
    
    return {"profiles": profiles}


# Tool D: Strategy Synthesis
@tool
def synthesize_strategy(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    RFP 요구사항, 내부 매칭, 경쟁사 분석을 종합하여 전략을 수립합니다.
    
    Args:
        inputs: Dict containing requirements, internal_match, competitors
        
    Returns:
        Dict with actions, our_swot, differentiation
    """
    # 샘플 전략 수립 결과
    return {
        "actions": [
            "보안 인증 획득 (ISO 27001, K-ISMS)",
            "클라우드 전문 인력 확보",
            "AI/ML 기술 역량 강화",
            "파트너십 네트워크 구축",
            "가격 경쟁력 확보 방안 수립"
        ],
        "our_swot": {
            "strengths": [
                "유연한 개발 프로세스",
                "빠른 의사결정 체계",
                "혁신적 기술 적용"
            ],
            "weaknesses": [
                "대규모 프로젝트 경험 부족",
                "보안 인증 미보유"
            ],
            "opportunities": [
                "중소기업 시장 진출",
                "특화 솔루션 개발"
            ],
            "threats": [
                "대기업 가격 경쟁",
                "기술 인력 확보 어려움"
            ]
        },
        "differentiation": [
            "맞춤형 솔루션 제공",
            "빠른 프로토타이핑",
            "지속적인 기술 지원",
            "경쟁력 있는 가격 정책"
        ]
    }


# Tool E: Report Generation
@tool
def generate_report(all_results: Dict[str, Any]) -> str:
    """
    모든 분석 결과를 종합하여 최종 보고서를 생성합니다.
    
    Args:
        all_results: 모든 단계의 분석 결과
        
    Returns:
        마크다운 형태의 보고서 문자열
    """
    # 샘플 보고서 생성
    report = """# RFP 분석 및 제안 전략 보고서

## 📋 요구사항 분석
- **주요 요구사항**: 클라우드 인프라, 데이터 보안, AI/ML 기능, 실시간 모니터링, 모바일 앱
- **평가 기준**: 기술 적합성(40%), 가격 경쟁력(30%), 프로젝트 경험(20%), 유지보수 계획(10%)
- **주요 리스크**: 라이선스 비용, 납기 지연, 보안 인증, 인력 부족

## 🎯 내부 역량 매칭
- **매칭 프로젝트**: 스마트시티 플랫폼, 클라우드 마이그레이션, AI 데이터 분석
- **레퍼런스**: 서울시 스마트시티, 금융권 클라우드, 제조업 AI 품질관리

## ⚔️ 경쟁사 분석
- **주요 경쟁사**: 삼성 SDS, LG CNS, 포스코DX, KT, 현대오토에버, 카카오, CJ 올리브네트웍스
- **공통 강점**: 대규모 인프라, 다양한 경험, 전문 인력
- **공통 약점**: 높은 비용, 복잡한 의사결정

## 🚀 제안 전략
### 핵심 액션
1. **보안 인증 획득** (ISO 27001, K-ISMS)
2. **클라우드 전문 인력 확보**
3. **AI/ML 기술 역량 강화**
4. **파트너십 네트워크 구축**
5. **가격 경쟁력 확보**

### 차별화 전략
- 맞춤형 솔루션 제공
- 빠른 프로토타이핑
- 지속적인 기술 지원
- 경쟁력 있는 가격 정책

## 📊 SWOT 분석
| 강점 | 약점 |
|------|------|
| 유연한 개발 프로세스 | 대규모 프로젝트 경험 부족 |
| 빠른 의사결정 체계 | 보안 인증 미보유 |
| 혁신적 기술 적용 | |

| 기회 | 위협 |
|------|------|
| 중소기업 시장 진출 | 대기업 가격 경쟁 |
| 특화 솔루션 개발 | 기술 인력 확보 어려움 |

## 💡 결론 및 권고사항
본 RFP는 클라우드 기반 스마트시티 플랫폼 구축 사업으로, 내부 역량과 높은 매칭도를 보입니다. 
보안 인증 획득과 전문 인력 확보를 통해 경쟁력을 강화하고, 차별화된 솔루션 제공으로 
성공적인 수주 가능성을 높일 수 있습니다.
"""
    
    return report


class DealLensSupervisor:
    """
    DealLens 슈퍼바이저 에이전트
    A → B → C → D → E 순서로 파이프라인을 실행합니다.
    """
    
    def __init__(self):
        self.tools = [
            parse_rfp,
            match_internal_knowledge, 
            load_competitor_data,
            synthesize_strategy,
            generate_report
        ]
    
    def execute_pipeline(self, pdf_path: str, companies: Optional[List[str]] = None, user_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        전체 파이프라인을 순차적으로 실행합니다.
        
        Args:
            pdf_path: RFP PDF 파일 경로
            companies: 분석할 경쟁사 목록 (선택사항)
            user_prompt: 사용자 추가 요청사항 (선택사항)
            
        Returns:
            최종 결과 JSON
        """
        # 1) RFP 경로 검증
        if not pdf_path:
            return {
                "error": "RFP 파일 경로 필요",
                "artifacts": {},
                "deal_brief": "",
                "qa_ready": False
            }
        
        # 2) A: RFP Parser
        try:
            A_artifacts = parse_rfp.invoke({"pdf_path": pdf_path})
            # 사용자 프롬프트가 있으면 요구사항에 추가
            if user_prompt:
                A_artifacts["user_requirements"] = [user_prompt]
        except Exception as e:
            A_artifacts = {"requirements": [], "criteria": [], "risks": []}
            if user_prompt:
                A_artifacts["user_requirements"] = [user_prompt]
        
        # 3) B: Internal RAG
        try:
            # 사용자 요구사항도 포함하여 검색
            all_requirements = A_artifacts.get("requirements", [])
            if user_prompt:
                all_requirements.append(f"사용자 요청: {user_prompt}")
                
            B_artifacts = match_internal_knowledge.invoke({
                "requirements": all_requirements
            })
        except Exception as e:
            B_artifacts = {"matches": [], "references": []}
        
        # 4) C: Competitor Analysis
        try:
            if not companies:
                companies = ["삼성 SDS", "LG CNS", "포스코DX", "KT", "현대오토에버", "카카오", "CJ 올리브네트웍스"]
            C_artifacts = load_competitor_data.invoke({"companies": companies})
        except Exception as e:
            C_artifacts = {"profiles": {}}
        
        # 5) D: Strategy Synthesis
        try:
            strategy_inputs = {
                "requirements": A_artifacts.get("requirements", []),
                "criteria": A_artifacts.get("criteria", []),
                "risks": A_artifacts.get("risks", []),
                "internal_match": B_artifacts,
                "competitors": C_artifacts,
                "user_prompt": user_prompt
            }
            D_artifacts = synthesize_strategy.invoke({"inputs": strategy_inputs})
        except Exception as e:
            D_artifacts = {"actions": [], "our_swot": {}, "differentiation": []}
        
        # 6) E: Report Generation
        try:
            all_results = {
                "requirements": A_artifacts.get("requirements", []),
                "criteria": A_artifacts.get("criteria", []),
                "risks": A_artifacts.get("risks", []),
                "internal_match": B_artifacts,
                "competitors": C_artifacts,
                "strategy": D_artifacts,
                "user_prompt": user_prompt
            }
            deal_brief = generate_report.invoke({"all_results": all_results})
        except Exception as e:
            deal_brief = "보고서 생성 중 오류가 발생했습니다."
        
        # 최종 결과 반환
        return {
            "artifacts": {
                "A": A_artifacts,
                "B": B_artifacts,
                "C": C_artifacts,
                "D": D_artifacts
            },
            "deal_brief": deal_brief,
            "qa_ready": True
        }


# 편의 함수
def run_deallens_pipeline(pdf_path: str, companies: Optional[List[str]] = None, user_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    DealLens 파이프라인을 실행하는 편의 함수
    
    Args:
        pdf_path: RFP PDF 파일 경로
        companies: 분석할 경쟁사 목록 (선택사항)
        user_prompt: 사용자 추가 요청사항 (선택사항)
        
    Returns:
        최종 결과 JSON
    """
    supervisor = DealLensSupervisor()
    return supervisor.execute_pipeline(pdf_path, companies, user_prompt)


if __name__ == "__main__":
    # 테스트 실행
    supervisor = DealLensSupervisor()
    result = supervisor.execute_pipeline("sample_rfp.pdf")
    print(json.dumps(result, ensure_ascii=False, indent=2))
