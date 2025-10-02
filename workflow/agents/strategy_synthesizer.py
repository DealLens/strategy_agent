import os
import json
import re
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

# ======================
# 통합 LLM 클라이언트 사용
# ======================
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from utils.llm_client import get_llm_client, is_llm_available, call_llm, parse_json_response

llm_client = get_llm_client()


# ======================
# Strategy Synthesizer Tool
# ======================
@tool
def strategy_synthesizer(
    requirements: List[str],   # ✅ 필수: RFP에서 추출
    internal_matches: Optional[List[Dict[str, Any]]] = None,   # 선택
    competitor_profiles: Optional[Dict[str, Any]] = None       # 선택
) -> dict:
    """
    내부 매칭 + 경쟁사 분석을 종합해 AI가 전략을 도출합니다.
    """

    internal_matches = internal_matches or []
    competitor_profiles = competitor_profiles or {}

    print("\n[전략 합성] AI 분석 시작...")

    # LLM이 없으면 기본 규칙 기반
    if not is_llm_available():
        return _generate_basic_strategy(requirements, internal_matches, competitor_profiles)

    try:
        # ------------------
        # 프롬프트 생성
        # ------------------
        prompt = f"""
당신은 전문 전략 컨설턴트입니다. 
아래 정보를 기반으로 수주 전략을 JSON 형식으로 작성하세요.

## RFP 핵심 요구사항
{chr(10).join(f"- {req}" for req in requirements[:10])}

## 내부 역량 매칭 결과
{_format_internal_matches(internal_matches)}

## 경쟁사 분석
{_format_competitor_profiles(competitor_profiles)}

--- 

반드시 다음 JSON 스키마를 정확히 따라주세요:
{{
  "summary": "전략 요약 (3~5문장)",
  "actions": [
    "구체적인 액션 아이템 1",
    "구체적인 액션 아이템 2",
    "구체적인 액션 아이템 3",
    "구체적인 액션 아이템 4",
    "구체적인 액션 아이템 5"
  ],
  "swot": {{
    "S": "강점 (1문장)",
    "W": "약점 (1문장)",
    "O": "기회 (1문장)",
    "T": "위협 (1문장)"
  }},
  "differentiation": [
    "차별화 포인트 1",
    "차별화 포인트 2",
    "차별화 포인트 3"
  ]
}}

중요: JSON 형식만 반환하고 다른 설명은 추가하지 마세요.
"""
        # ------------------
        # AI 호출
        # ------------------
        result_text = call_llm(prompt, temperature=0.7)

        if result_text:
            # 개선된 JSON 파싱 로직 사용
            strategy_data = parse_json_response(result_text)
            
            if strategy_data and _validate_strategy_data(strategy_data):
                print("[전략 합성] ✅ AI 분석 완료")
                return {"strategy": strategy_data}
            else:
                print("[전략 합성] ⚠️ JSON 파싱 실패 → 기본 전략 생성")
                return _generate_basic_strategy(requirements, internal_matches, competitor_profiles)
        else:
            print("[전략 합성] ⚠️ LLM 호출 실패 → 기본 전략 생성")
            return _generate_basic_strategy(requirements, internal_matches, competitor_profiles)

    except Exception as e:
        print(f"[전략 합성] ❌ AI 분석 실패: {e}")
        return _generate_basic_strategy(requirements, internal_matches, competitor_profiles)


def _validate_strategy_data(data: Dict[str, Any]) -> bool:
    """전략 데이터 유효성 검증"""
    required_keys = ["summary", "actions", "swot", "differentiation"]
    
    # 필수 키 존재 확인
    if not all(key in data for key in required_keys):
        return False
    
    # swot 내부 구조 확인
    swot = data.get("swot", {})
    swot_keys = ["S", "W", "O", "T"]
    if not all(key in swot for key in swot_keys):
        return False
    
    # 리스트 타입 확인
    if not isinstance(data.get("actions", []), list):
        return False
    if not isinstance(data.get("differentiation", []), list):
        return False
    
    return True


# ======================
# Helper Functions
# ======================
def _format_internal_matches(matches: List[Dict]) -> str:
    if not matches:
        return "내부 매칭 데이터 없음"

    lines = []
    for match in matches[:5]:
        req = match.get("requirement", "요구사항 미지정")
        related = match.get("matches", [])
        if related:
            projects = ", ".join([p.get("title", "")[:50] for p in related[:3]])
            lines.append(f"- {req}: {len(related)}개 프로젝트 매칭 ({projects})")
        else:
            lines.append(f"- {req}: 매칭 없음 (외부 역량 필요)")
    return "\n".join(lines)


def _format_competitor_profiles(profiles: Dict) -> str:
    if not profiles:
        return "경쟁사 분석 데이터 없음"

    lines = []
    for company, profile in profiles.items():
        swot = profile.get("swot", {})
        lines.append(f"### {company}")
        if swot.get("S"):
            lines.append(f"  - 강점: {swot['S']}")
        if swot.get("W"):
            lines.append(f"  - 약점: {swot['W']}")
    return "\n".join(lines)


def _generate_basic_strategy(requirements: List[str], internal_matches: List[Dict], competitor_profiles: Dict) -> dict:
    """기본 규칙 기반 전략 생성"""
    actions = []
    for match in internal_matches:
        req = match.get("requirement")
        related = match.get("matches", [])
        if not related:
            actions.append(f"{req}: 외부 파트너십 필요")
        else:
            actions.append(f"{req}: 내부 {len(related)}개 프로젝트 활용")

    if not actions:
        actions = ["내부 역량 확보", "외부 협력사 검토", "보안 인증 준비"]

    swot = {
        "S": "내부 프로젝트 경험",
        "W": "일부 요구사항 레퍼런스 부족",
        "O": "디지털 전환 수요 증가",
        "T": "대기업 경쟁사 브랜드 파워"
    }

    differentiation = [
        "실전 프로젝트 경험",
        "빠른 의사결정",
        "고객 맞춤형 접근"
    ]

    return {
        "strategy": {
            "summary": "내부 역량을 활용하면서 부족한 부분은 외부 협력으로 보완하는 전략이 필요합니다.",
            "actions": actions[:5],
            "swot": swot,
            "differentiation": differentiation[:3]
        }
    }


# ======================
# 디버깅용 실행
# ======================
if __name__ == "__main__":
    dummy_requirements = ["AI 성능 검증", "보안 인증", "Python 개발"]
    dummy_internal_matches = [
        {"requirement": "AI 성능 검증", "matches": [{"title": "프로젝트 A"}]},
        {"requirement": "보안 인증", "matches": []}
    ]
    dummy_competitors = {
        "삼성 SDS": {"swot": {"S": "브랜드 파워", "W": "가격 경쟁력 부족"}},
        "LG CNS": {"swot": {"S": "SI 경험", "W": "민첩성 부족"}}
    }

    result = strategy_synthesizer.invoke({
        "requirements": dummy_requirements,
        "internal_matches": dummy_internal_matches,
        "competitor_profiles": dummy_competitors
    })
    print("🎯 전략 합성 결과:")
    print(result)
