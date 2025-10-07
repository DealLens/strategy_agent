from langchain_core.tools import tool
from typing import Dict, Any, Optional, List


def _format_internal_matches(matches: List[Dict[str, Any]], limit: int = 5) -> List[str]:
    """내부 매칭 결과를 요구사항-기사 형태로 정리"""
    formatted = []
    for idx, m in enumerate(matches[:limit]):
        req = m.get("requirement", "요구사항 미지정")
        related = m.get("matches", [])
        if not related:
            formatted.append(f"🔹 {req} (매칭된 사례 없음)")
            continue

        formatted.append(f"🔹 **{req}**")
        for r in related[:3]:  # 각 요구사항별 최대 3개만 표시
            title = r.get("title", "제목 없음")
            summary = r.get("summary", "")
            url = r.get("url", "")
            line = f"   - {title}"
            if summary:
                line += f" | {summary}"
            if url:
                line += f" ({url})"
            formatted.append(line)
    return formatted


@tool
def reporter(data: Optional[Dict[str, Any]] = None) -> dict:
    """
    최종 보고서 요약 및 브리핑을 생성합니다.
    
    Args:
        data (dict, optional): Supervisor가 모은 A~D 단계 결과
            {
                "requirements": [...],
                "evaluation": [...],
                "risks": [...],
                "internal_matches": [
                    {
                        "requirement": str,
                        "matches": [
                            {"title": str, "summary": str, "url": str}
                        ]
                    }
                ],
                "competitor_profiles": {...},
                "strategy": {...}
            }

    Returns:
        dict: {
            "deal_brief": str,   # 1~2p 요약 브리핑
            "sections": dict     # 상세 섹션 (요구사항/리스크/전략/경쟁사)
        }
    """
    data = data or {}

    requirements = data.get("requirements", [])
    evaluation = data.get("evaluation", [])
    risks = data.get("risks", [])
    internal_matches = data.get("internal_matches", [])
    competitors = data.get("competitor_profiles", {})
    strategy = data.get("strategy", {})

    # 상세한 Deal Brief 생성
    deal_brief = f"""
🎯 **입찰 전략 분석 요약**

📊 **프로젝트 개요**
- 핵심 요구사항: {len(requirements)}개 항목
- 평가 기준: {len(evaluation)}개 (기술/가격/사업수행능력)
- 잠재 리스크: {len(risks)}개 식별
- 내부 매칭 사례: {len(internal_matches)}개 요구사항 대응
- 경쟁사 분석: {len(competitors)}개 기업 분석 완료

🚀 **핵심 전략 방향**
- 차별화 포인트: {len(strategy.get('differentiation', []))}개 도출
- 실행 계획: {len(strategy.get('actions', []))}개 액션 아이템
- 경쟁 우위: {len(strategy.get('competitive_advantages', []))}개 강점 영역
- 보완 필요: {len(strategy.get('capability_gaps', []))}개 역량 갭

💡 **주요 인사이트**
- 기술적 접근: {strategy.get('strategic_recommendations', {}).get('technical_approach', '분석 필요')}
- 가격 전략: {strategy.get('strategic_recommendations', {}).get('pricing_strategy', '분석 필요')}
- 고객 중심: {strategy.get('strategic_recommendations', {}).get('customer_focus', '분석 필요')}
""".strip()

    # 상세 섹션 - 구조화된 형식으로 개선
    sections = {
        "📋 RFP 요구사항 분석": {
            "핵심 요구사항": requirements[:5],
            "평가 기준": evaluation[:5],
            "잠재 리스크": risks[:5]
        },
        "🔍 내부 역량 매칭": {
            "매칭 결과": _format_internal_matches(internal_matches, limit=5),
            "강점 영역": strategy.get('competitive_advantages', []),
            "보완 필요 영역": strategy.get('capability_gaps', [])
        },
        "⚔️ 경쟁사 분석": {
            company: {
                "회사 개요": profile.get("company_summary", "")[:200] + "..." if profile.get("company_summary") else "분석 필요",
                "SWOT 분석": profile.get("swot", {}),
                "핵심 기술": profile.get("key_technologies", [])[:3],
                "차별화 포인트": profile.get("differentiation_points", [])[:3]
            } for company, profile in competitors.items()
        },
        "🚀 전략 제안": {
            "차별화 전략": strategy.get('differentiation', []),
            "실행 계획": strategy.get('actions', []),
            "전략적 추천사항": strategy.get('strategic_recommendations', {})
        },
        "📊 SWOT 분석": strategy.get('swot', {})
    }

    return {
        "deal_brief": deal_brief.strip(),
        "sections": sections
    }


# 단독 실행 디버깅용
if __name__ == "__main__":
    dummy_data = {
        "requirements": ["AI 성능 검증", "보안 인증"],
        "evaluation": ["기술 80%", "가격 20%"],
        "risks": ["보안 요구 불명확"],
        "internal_matches": [
            {
                "requirement": "AI 성능 검증",
                "matches": [
                    {
                        "title": "제조 A사의 설비 정보 구축",
                        "summary": "생산시간 단축을 위한 SK㈜ C&C 솔루션 적용",
                        "url": "https://www.skax.co.kr/case-study/story/2412"
                    }
                ]
            },
            {
                "requirement": "보안 인증",
                "matches": [
                    {
                        "title": "금융 보안 프로젝트",
                        "summary": "금융기관 대상 보안 모듈 구축",
                        "url": "https://www.skax.co.kr/case-study/story/2420"
                    }
                ]
            }
        ],
        "competitor_profiles": {
            "삼성 SDS": {"swot": {"S": "브랜드", "W": "비용"}}
        },
        "strategy": {
            "actions": ["PoC 제안", "파트너 협력"],
            "swot": {"S": "AI 역량"}
        }
    }

    result = reporter.run(dummy_data)
    print("📋 Deal Brief:\n", result["deal_brief"])
    print("\n📑 상세 섹션:")
    for k, v in result["sections"].items():
        print(f"\n## {k}\n{v}")
