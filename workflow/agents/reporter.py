from langchain_core.tools import tool
from typing import Dict, Any, Optional, List


def _format_list(items: List[str], prefix: str = "- ") -> str:
    """리스트를 마크다운 목록으로 변환"""
    if not items:
        return f"{prefix}해당 없음"
    return "\n".join(f"{prefix}{item}" for item in items)


def _format_competitors(competitors: Dict[str, Any]) -> str:
    """경쟁사 SWOT 분석을 마크다운으로 변환"""
    if not competitors:
        return "- 경쟁사 분석 없음"
    lines = []
    for name, profile in competitors.items():
        swot = profile.get("swot", {})
        lines.append(f"### 🏢 {name}")
        lines.append(f"- **강점(S):** {swot.get('S', 'N/A')}")
        lines.append(f"- **약점(W):** {swot.get('W', 'N/A')}")
        lines.append(f"- **기회(O):** {swot.get('O', 'N/A')}")
        lines.append(f"- **위협(T):** {swot.get('T', 'N/A')}")
        lines.append("")
    return "\n".join(lines)


@tool
def reporter(data: Optional[Dict[str, Any]] = None) -> dict:
    """
    최종 전략 보고서를 생성합니다.

    Args:
        data (dict, optional): Supervisor가 모은 A~D 단계 결과
            {
                "requirements": [...],
                "evaluation": [...],
                "risks": [...],
                "internal_matches": [...],
                "competitor_profiles": {...},
                "strategy": {...}
            }

    Returns:
        dict: {
            "deal_brief": str,   # 1~2p 요약 브리핑
            "full_report": str   # 상세 섹션 포함한 최종 보고서 (Markdown)
        }
    """
    data = data or {}

    # 데이터 추출
    requirements = data.get("requirements", [])
    evaluation = data.get("evaluation", [])
    risks = data.get("risks", [])
    internal_matches = data.get("internal_matches", [])
    competitors = data.get("competitor_profiles", {})
    strategy = data.get("strategy", {})

    # 간단 브리핑 (Deal Brief)
    deal_brief = f"""
📋 **Deal Brief**
- 요구사항: {len(requirements)}개
- 평가 기준: {len(evaluation)}개
- 리스크 후보: {len(risks)}개
- 내부 매칭: {len(internal_matches)}개
- 경쟁사 분석: {len(competitors)}개
- 전략 액션: {len(strategy.get('actions', []))}개
""".strip()

    # 상세 보고서 (Markdown)
    full_report = f"""
# 📑 전략 보고서

## 📌 요구사항 및 평가 기준
### 요구사항
{_format_list(requirements)}

### 평가 기준
{_format_list(evaluation)}

---

## ⚠️ 리스크
{_format_list(risks)}

---

## 🔍 내부 역량 매칭
{_format_list([str(m) for m in internal_matches])}

---

## 🏢 경쟁사 분석
{_format_competitors(competitors)}

---

## 🎯 제안 전략
- **핵심 전략:** {_format_list(strategy.get("actions", []))}
- **SWOT:** {strategy.get("swot", {})}

---

## ✅ 결론
이번 RFP에 대한 대응 전략은 내부 역량과 경쟁사 분석을 종합하여,
**차별화된 기술 제안**과 **효율적인 비용 구조**를 강조하는 방향으로 설정되었습니다.
"""
    return {
        "deal_brief": deal_brief.strip(),
        "full_report": full_report.strip()
    }


# 단독 실행 디버깅용
if __name__ == "__main__":
    dummy_data = {
        "requirements": ["AI 성능 검증", "보안 인증", "웹 접근성 준수"],
        "evaluation": ["기술 70%", "가격 30%"],
        "risks": ["보안 요구 불명확", "구간 암호화 모듈 노후화"],
        "internal_matches": [
            {"requirement": "AI 성능 검증", "related": ["프로젝트 A"]},
            {"requirement": "보안 인증", "related": ["프로젝트 B"]}
        ],
        "competitor_profiles": {
            "삼성 SDS": {"swot": {"S": "브랜드", "W": "비용"}},
            "포스코DX": {"swot": {"S": "제조 강점", "T": "AI 전문성 부족"}}
        },
        "strategy": {
            "actions": ["PoC 제안", "파트너 협력", "가격 경쟁력 확보"],
            "swot": {"S": "AI 역량", "W": "인력 부족"}
        }
    }

    result = reporter.run(dummy_data)  # @tool 은 run()으로 실행 가능
    print("📋 Deal Brief:\n", result["deal_brief"])
    print("\n====================\n")
    print(result["full_report"])
