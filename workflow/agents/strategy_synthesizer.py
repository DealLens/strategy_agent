from langchain_core.tools import tool
from typing import List, Dict, Any, Optional


@tool
def strategy_synthesizer(
    requirements: List[str],   # ✅ 필수: RFP에서 직접 추출 (개발언어, 요구사항 등)
    internal_matches: Optional[List[Dict[str, Any]]] = None,   # 선택
    competitor_profiles: Optional[Dict[str, Any]] = None       # 선택
) -> dict:
    """
    내부 매칭 + 경쟁사 분석을 종합해 전략을 도출합니다.

    Args:
        requirements (List[str]): RFP에서 직접 추출된 요구사항/개발언어
        internal_matches (Optional[List[Dict]]): 내부 역량 매칭 결과 (없으면 빈 리스트)
        competitor_profiles (Optional[Dict]): 경쟁사 SWOT 분석 결과 (없으면 빈 dict)

    Returns:
        dict: {
            "strategy": {
                "actions": [...],          # 갭 보완책
                "swot": {...},             # 당사 SWOT
                "differentiation": [...]   # 차별화 포인트
            }
        }
    """

    internal_matches = internal_matches or []
    competitor_profiles = competitor_profiles or {}

    # 1. 갭 분석 → 보완책(Action Plan) - 개선된 로직
    actions = []
    capability_gaps = []
    competitive_advantages = []
    
    for match in internal_matches:
        req = match.get("requirement", "")
        related = match.get("matches", [])
        
        if not related:
            capability_gaps.append(req)
            actions.append({
                "action": f"{req} 역량 보완",
                "type": "외부 파트너십",
                "priority": "High",
                "description": f"{req} 분야에서 검증된 외부 파트너 또는 컨설턴트 확보 필요",
                "timeline": "입찰 전 파트너십 체결"
            })
        elif len(related) >= 3:
            # 강한 내부 역량
            competitive_advantages.append(req)
            actions.append({
                "action": f"{req} 역량 강조",
                "type": "내부 역량",
                "priority": "High",
                "description": f"{req} 분야에서 다수의 성공 사례 보유 - 신뢰성 확보",
                "timeline": "제안서 작성 시 핵심 차별화 요소로 활용"
            })
        else:
            # 보통 수준의 내부 역량
            actions.append({
                "action": f"{req} 역량 보완",
                "type": "선택적 파트너십",
                "priority": "Medium", 
                "description": f"{req} 분야에서 일부 경험 보유하나 추가 역량 보완 권장",
                "timeline": "프로젝트 진행 중 필요시 파트너 확보"
            })

    if not actions:
        actions = [{
            "action": "내부 역량 분석 필요",
            "type": "데이터 부족",
            "priority": "High",
            "description": "내부 매칭 데이터 부족으로 구체적인 보완책 제안 불가",
            "timeline": "추가 데이터 수집 후 재분석 필요"
        }]

    # 2. 당사 SWOT - 동적 생성 (개선된 로직)
    swot = {
        "S": [],  # 강점
        "W": [],  # 약점  
        "O": [],  # 기회
        "T": []   # 위협
    }
    
    # 내부 매칭 결과 기반 SWOT 생성
    if competitive_advantages:
        swot["S"].extend([
            f"{', '.join(competitive_advantages[:3])} 분야에서 검증된 성공 사례 다수 보유",
            "다양한 프로젝트 경험을 통한 축적된 노하우",
            "고객 맞춤형 솔루션 제공 역량"
        ])
    
    if capability_gaps:
        swot["W"].extend([
            f"{', '.join(capability_gaps[:2])} 분야에서 추가 역량 보완 필요",
            "대규모 프로젝트 대응 인력 확보 필요",
            "일부 특수 기술 영역에서 전문성 부족"
        ])
    
    # 기본 SWOT 요소 (동적 생성 실패 시 fallback)
    if not swot["S"]:
        swot["S"] = [
            "AI/빅데이터 분야 선도적 연구 경험",
            "공공기관 프로젝트 다수 수행 경험",
            "기술 혁신을 통한 차별화된 솔루션 제공"
        ]
    
    if not swot["W"]:
        swot["W"] = [
            "대기업 대비 브랜드 인지도 부족",
            "특정 분야 전문 인력 확보 필요",
            "가격 경쟁력 강화 필요"
        ]
    
    if not swot["O"]:
        swot["O"] = [
            "정부 디지털 뉴딜 정책 확대",
            "AI/빅데이터 시장 급성장",
            "중소기업 디지털 전환 수요 증가"
        ]
    
    if not swot["T"]:
        swot["T"] = [
            "대기업의 가격 경쟁 압박",
            "기술 변화 속도 가속화",
            "글로벌 IT 기업의 국내 진출 확대"
        ]

    # 3. 경쟁사 대비 차별화 포인트 - 개선된 로직
    differentiation = []
    competitive_insights = []
    
    for comp, profile in competitor_profiles.items():
        swot_comp = profile.get("swot", {})
        company_summary = profile.get("company_summary", "")
        
        # 경쟁사 강점 분석 → 우리 대응 전략
        strengths = swot_comp.get("S", [])
        weaknesses = swot_comp.get("W", [])
        
        # 가격 경쟁력 분석
        if any("가격" in w or "비용" in w or "경쟁력" in w for w in weaknesses):
            differentiation.append({
                "vs_competitor": comp,
                "differentiation": "가격 경쟁력",
                "strategy": f"{comp} 대비 합리적 가격으로 가성비 우위 확보",
                "impact": "High",
                "implementation": "투명한 비용 구조 제시 및 가격 경쟁력 강조"
            })
        
        # 기술 차별화 분석
        if any("브랜드" in s or "인지도" in s for s in strengths):
            differentiation.append({
                "vs_competitor": comp,
                "differentiation": "기술 혁신성",
                "strategy": f"{comp}는 브랜드 강점 → 우리는 기술 혁신과 고객 맞춤형 솔루션으로 차별화",
                "impact": "High",
                "implementation": "최신 기술 적용 사례 및 고객 맞춤 솔루션 강조"
            })
        
        # 시장 포지셔닝 분석
        if company_summary:
            if "대기업" in company_summary or "대규모" in company_summary:
                differentiation.append({
                    "vs_competitor": comp,
                    "differentiation": "민첩성과 유연성",
                    "strategy": f"{comp} 대비 빠른 의사결정과 유연한 대응으로 고객 만족도 향상",
                    "impact": "Medium",
                    "implementation": "빠른 프로토타이핑 및 고객 피드백 반영 프로세스 강조"
                })
    
    # 기본 차별화 포인트 (경쟁사 데이터 부족 시)
    if not differentiation:
        differentiation = [{
            "vs_competitor": "전체 경쟁사",
            "differentiation": "기술 혁신과 고객 중심",
            "strategy": "최신 기술 적용과 고객 맞춤형 솔루션으로 차별화",
            "impact": "High",
            "implementation": "기술 혁신성과 고객 만족도 중심의 제안서 구성"
        }]

    return {
        "strategy": {
            "actions": actions[:5],
            "swot": swot,
            "differentiation": differentiation[:5],
            "competitive_advantages": competitive_advantages,
            "capability_gaps": capability_gaps,
            "strategic_recommendations": {
                "pricing_strategy": "경쟁사 대비 가성비 중심의 가격 전략",
                "technical_approach": "최신 기술과 검증된 방법론 적용",
                "customer_focus": "고객 맞춤형 솔루션과 지속적인 지원",
                "risk_mitigation": "단계별 검증과 품질 관리 강화"
            }
        }
    }


# 디버깅용 실행
if __name__ == "__main__":
    dummy_requirements = ["AI 성능 검증", "보안 인증", "개발언어: Python"]
    dummy_internal_matches = [
        {"requirement": "AI 성능 검증", "related": ["프로젝트 A"]},
        {"requirement": "보안 인증", "related": []}
    ]
    dummy_competitors = {
        "삼성 SDS": {"swot": {"S": "브랜드", "W": "가격 경쟁력 부족"}},
        "LG CNS": {"swot": {"S": "SI 경험", "W": "민첩성 부족"}}
    }

    result = strategy_synthesizer.invoke({
        "requirements": dummy_requirements,
        # internal_matches, competitor_profiles는 안 줘도 OK
    })
    print("🎯 전략 합성 결과:")
    print(result)
