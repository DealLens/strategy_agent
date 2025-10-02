import os
from langchain_core.tools import tool
from typing import Dict, Any, Optional, List

# LLM 초기화
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
    AOAI_API_KEY = os.getenv("AOAI_API_KEY")
    AOAI_DEPLOY_GPT4O = os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    client = None
    if AOAI_API_KEY and AOAI_ENDPOINT:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=AOAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=AOAI_ENDPOINT,
        )
        print("✅ Reporter: Azure OpenAI 사용")
    elif OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ Reporter: OpenAI 사용")
    else:
        print("⚠️ Reporter: API 키 없음 → 기본 모드 동작")
except Exception as e:
    client = None
    print(f"⚠️ Reporter LLM 초기화 실패: {e}")


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
                line += f" | {summary[:100]}"
            if url:
                line += f" ({url})"
            formatted.append(line)
    return formatted


@tool
def reporter(data: Optional[Dict[str, Any]] = None) -> dict:
    """
    AI가 최종 보고서 요약 및 브리핑을 생성합니다.
    
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
            "deal_brief": str,   # AI가 작성한 1~2p 요약 브리핑
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

    print("\n[리포터] AI 보고서 작성 시작...")

    # 상세 섹션 (항상 제공)
    sections = {
        "요구사항": requirements[:5],
        "평가기준": evaluation[:5],
        "리스크": risks[:5],
        "내부매칭": _format_internal_matches(internal_matches, limit=5),
        "경쟁사": {k: v.get("swot", {}) for k, v in competitors.items()},
        "전략": strategy
    }

    # LLM이 없으면 기본 브리핑
    if not client:
        deal_brief = _generate_basic_brief(requirements, evaluation, risks, internal_matches, competitors, strategy)
        return {
            "deal_brief": deal_brief,
            "sections": sections
        }

    # AI로 Deal Brief 생성
    try:
        prompt = f"""
당신은 전문 전략 컨설턴트입니다. 다음 RFP 분석 결과를 바탕으로 임원진에게 보고할 1-2페이지 분량의 Deal Brief를 작성해주세요.

## RFP 핵심 요구사항 ({len(requirements)}개)
{chr(10).join(f"- {req}" for req in requirements[:10])}

## 평가 기준 ({len(evaluation)}개)
{chr(10).join(f"- {item}" for item in evaluation[:5])}

## 리스크 요소 ({len(risks)}개)
{chr(10).join(f"- {risk}" for risk in risks[:5])}

## 내부 역량 매칭 ({len(internal_matches)}개)
{_format_internal_summary(internal_matches)}

## 경쟁사 분석 ({len(competitors)}개 기업)
{_format_competitor_summary(competitors)}

## 전략 제안
{_format_strategy_summary(strategy)}

---

위 정보를 종합하여 다음 구조로 Deal Brief를 작성해주세요 (마크다운 형식):

# 📋 Deal Brief

## 1. 프로젝트 개요
(RFP 핵심을 2-3문장으로 요약)

## 2. 핵심 평가 포인트
(평가 기준과 중요도를 간략히)

## 3. 우리의 경쟁력
(내부 역량 매칭 결과를 바탕으로 강점 서술)

## 4. 주요 리스크
(리스크 요소와 대응 방안)

## 5. 경쟁사 대비 우위
(경쟁사 분석을 바탕으로 차별화 포인트)

## 6. 수주 전략
(전략 제안을 바탕으로 핵심 액션 아이템)

## 7. 추천 의견
(Go / No-Go / Conditional Go 중 하나와 그 이유)

전문적이고 간결하게 작성하되, 의사결정에 필요한 핵심 정보를 모두 담아주세요.
"""

        model = os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        
        deal_brief = response.choices[0].message.content.strip()
        print("[리포터] ✅ AI 보고서 작성 완료")
        
        return {
            "deal_brief": deal_brief,
            "sections": sections
        }
        
    except Exception as e:
        print(f"[리포터] ❌ AI 보고서 작성 실패: {e}")
        deal_brief = _generate_basic_brief(requirements, evaluation, risks, internal_matches, competitors, strategy)
        return {
            "deal_brief": deal_brief,
            "sections": sections
        }


def _format_internal_summary(matches: List[Dict]) -> str:
    """내부 매칭을 간략히 텍스트로"""
    if not matches:
        return "내부 매칭 데이터 없음"
    
    total_matched = sum(len(m.get("matches", [])) for m in matches)
    no_match = sum(1 for m in matches if not m.get("matches"))
    
    return f"총 {len(matches)}개 요구사항 중 {len(matches) - no_match}개 매칭 ({total_matched}개 프로젝트), {no_match}개 갭 존재"


def _format_competitor_summary(profiles: Dict) -> str:
    """경쟁사를 간략히 텍스트로"""
    if not profiles:
        return "경쟁사 분석 데이터 없음"
    
    lines = []
    for company, profile in profiles.items():
        swot = profile.get("swot", {})
        s = ", ".join(swot.get("S", [])[:2]) if swot.get("S") else "정보 없음"
        lines.append(f"- {company}: {s}")
    
    return "\n".join(lines)


def _format_strategy_summary(strategy: Dict) -> str:
    """전략을 간략히 텍스트로"""
    if not strategy:
        return "전략 정보 없음"
    
    summary = strategy.get("summary", "")
    actions = strategy.get("actions", [])
    
    result = []
    if summary:
        result.append(f"핵심 전략: {summary}")
    if actions:
        result.append(f"액션 아이템: {', '.join(actions[:3])}")
    
    return "\n".join(result) if result else "전략 정보 없음"


def _generate_basic_brief(requirements, evaluation, risks, internal_matches, competitors, strategy) -> str:
    """기본 브리핑 (LLM 없을 때)"""
    total_matched = sum(len(m.get("matches", [])) for m in internal_matches)
    no_match = sum(1 for m in internal_matches if not m.get("matches"))
    
    return f"""
# 📋 Deal Brief

## 프로젝트 개요
- 요구사항: {len(requirements)}개
- 평가 기준: {len(evaluation)}개
- 주요 리스크: {len(risks)}개

## 내부 역량
- 매칭된 프로젝트: {total_matched}개
- 갭 요구사항: {no_match}개

## 경쟁사 현황
- 분석 완료: {len(competitors)}개 기업

## 전략 제안
{strategy.get('summary', '전략 요약 정보가 없습니다.')}

**핵심 액션:**
{chr(10).join(f"- {action}" for action in strategy.get('actions', [])[:5])}

## 추천 의견
분석 결과를 바탕으로 수주 전략을 검토하시기 바랍니다.
""".strip()


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
            "삼성 SDS": {"swot": {"S": ["브랜드"], "W": ["비용"]}}
        },
        "strategy": {
            "summary": "내부 역량과 외부 파트너십을 조합한 전략 수립",
            "actions": ["PoC 제안", "파트너 협력"],
            "swot": {"S": "AI 역량"}
        }
    }

    result = reporter.invoke({"data": dummy_data})
    print("📋 Deal Brief:\n", result["deal_brief"])
    print("\n📑 상세 섹션:")
    for k, v in result["sections"].items():
        print(f"\n## {k}\n{v}")
