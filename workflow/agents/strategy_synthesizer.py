# -*- coding: utf-8 -*-
"""
컨설턴트 수준 전략 합성기 (Reporter 통합판 v3.1)
- '갭(gap)' → '적합도(fit_level)'
- 'due_hint' → 'expected_timeline'
- 각 액션에 why / how / strategy_approach 추가
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import sys
from pathlib import Path

# ======================
# LLM 유틸
# ======================
# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.llm_client import get_llm_client, is_llm_available, call_llm, parse_json_response

llm_client = get_llm_client()

# ======================
# LangChain tool decorator (폴백 포함)
# ======================
try:
    from langchain_core.tools import tool
except Exception:
    def tool(func):
        return func


# ======================
# 카테고리 정의
# ======================
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "기술": ["AI", "인공지능", "모델", "머신러닝", "딥러닝", "데이터", "클라우드", "아키텍처", "API", "성능", "지표", "알고리즘", "인프라", "분석", "시각화", "Java", "Spring", "Oracle"],
    "보안/품질": ["보안", "인증", "접근성", "개인정보", "암호화", "품질", "테스트", "장애", "가용성", "백업", "DR", "ISMS", "ISMS-P", "ISO27001"],
    "사업/운영": ["유지보수", "운영", "일정", "조직", "보고", "교육", "전환", "마이그레이션", "SLA", "계약", "검수", "고객", "과업", "사업", "인력", "PMO"]
}


@dataclass
class Requirement:
    text: str
    category: str


# ======================
# 유틸 함수
# ======================
def _to_text(x: Any) -> str:
    if isinstance(x, list):
        return ", ".join(str(i) for i in x)
    return str(x or "")


def _categorize_requirement(text: str) -> str:
    t = text or ""
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in t.lower():
                return cat
    return "기타"


def _normalize_requirements(requirements: List[Union[str, Dict[str, Any]]]) -> List[Requirement]:
    norm: List[Requirement] = []
    for r in requirements:
        if isinstance(r, str):
            text = r.strip()
            norm.append(Requirement(text=text, category=_categorize_requirement(text)))
        elif isinstance(r, dict):
            text = r.get("text") or r.get("requirement") or r.get("title") or "요구사항 미지정"
            cat = r.get("category") or _categorize_requirement(text)
            norm.append(Requirement(text=str(text).strip(), category=str(cat)))
        else:
            text = str(r)
            norm.append(Requirement(text=text, category=_categorize_requirement(text)))
    return norm


def _shorten(text: str, max_len: int = 160) -> str:
    text = (text or "").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return (text[: max_len - 3] + "...") if len(text) > max_len else text


def _score_to_fit_level(score: Optional[float]) -> str:
    """0~1 점수 → 적합도 등급(high_fit/partial_fit/low_fit/unknown)."""
    if score is None:
        return "unknown"
    try:
        s = float(score)
    except Exception:
        return "unknown"
    if s < 0.45:
        return "low_fit"
    if s < 0.75:
        return "partial_fit"
    return "high_fit"


def _extract_best_matches(related: List[Dict[str, Any]], top_k: int = 3) -> List[str]:
    out: List[str] = []
    for item in (related or [])[:top_k]:
        title = item.get("title") or item.get("name") or "레퍼런스"
        out.append(_shorten(title, 60))
    return out


# ======================
# 프롬프트 구성 보조
# ======================
def _format_internal_for_prompt(internal_matches: List[Dict[str, Any]]) -> str:
    """내부 매칭 결과를 프롬프트용 단문 리스트로 요약."""
    if not internal_matches:
        return "내부 매칭 데이터 없음"
    lines = []
    for m in internal_matches[:8]:
        req = m.get("requirement") or "요구사항 미지정"
        score = m.get("match_score")
        fit_level = _score_to_fit_level(score)
        refs = ", ".join(_extract_best_matches(m.get("matches", [])))
        score_disp = f"{score:.2f}" if isinstance(score, (int, float)) else "N/A"
        lines.append(f"- {req} | 적합도점수: {score_disp} | 적합도: {fit_level} | 레퍼런스: {refs or '없음'}")
    return "\n".join(lines)


def _format_competitors_for_prompt(competitor_profiles: Dict[str, Any]) -> str:
    """경쟁사 프로필(최대 3개)을 SWOT 중심으로 프롬프트용 요약."""
    if not competitor_profiles:
        return "경쟁사 분석 데이터 없음"
    items = list(competitor_profiles.items())[:3]
    lines = []
    for company, profile in items:
        swot = profile.get("swot", {})
        s = _shorten(_to_text(swot.get("S")), 120)
        w = _shorten(_to_text(swot.get("W")), 120)
        o = _shorten(_to_text(swot.get("O")), 120)
        t = _shorten(_to_text(swot.get("T")), 120)
        lines.append(f"### {company}\n  - S: {s}\n  - W: {w}\n  - O: {o}\n  - T: {t}")
    return "\n".join(lines)


def _build_v3_1_prompt(
    norm_requirements: List[Requirement],
    internal_matches: List[Dict[str, Any]],
    competitor_profiles: Dict[str, Any]
) -> str:
    """컨설턴트 수준 전략을 유도하는 시스템 프롬프트 생성 (fit_level/expected_timeline 반영)."""
    req_summary = "\n".join([f"- [{r.category}] {r.text}" for r in norm_requirements[:12]])
    internal_summary = _format_internal_for_prompt(internal_matches)
    competitor_summary = _format_competitors_for_prompt(competitor_profiles)

    # LLM 출력 스키마 힌트(최소 구조)
    schema_hint = {
        "summary": "전략 핵심 요약 (3~5문장)",
        "focus": {
            "internal": "내부 역량 관점 방향",
            "competitor": "경쟁사 대비 방향",
            "market": "시장/정책 관점 방향"
        },
        "prioritized_actions": [
            {
                "id": "A1",
                "action": "구체적 실행 항목",
                "why": "이유(요구사항/적합도/경쟁사/시장 연계)",
                "how": "구체적인 수행 방식(단계, 협력, 적용 기술 등)",
                "strategy_approach": "Defensive|Offensive|Differentiation|Partnership|Innovative",
                "owner": "담당(Tech/PM/Sales 등)",
                "impact": "high|medium|low",
                "urgency": "high|medium|low",
                "effort": "high|medium|low",
                "expected_timeline": "예: 2025-Q4",
                "expected_result": "정량적 기대효과 (예: 성능 25% 개선, 리스크 30% 감소)",
                "related_fit_ids": ["F1", "F2"],
                "related_risks": ["R1"]
            }
        ],
        "roadmap": {
            "phase_0_prebid": {
                "duration": "4주 (Week 1~4)",
                "objective": "제안 기반 확보 - 요구사항 100% 매핑 + 레퍼런스 5~7건 확보 + 파트너 협업 체계 구축",
                "why": "초기 평가 통과율 85% 달성을 위해 기술 적합도 입증 및 신뢰도 확보 필요",
                "key_deliverables": ["요구사항 매핑 완료", "레퍼런스 5~7건 확보", "보안 체크리스트 완료", "파트너 1~2곳 선정"],
                "expected_outcome": "초기 평가 통과율 85% + 고객 신뢰도 40% 향상 + 기술 리스크 35% 감소",
                "related_actions": ["A1", "A2"]
            },
            "phase_1_poc": {
                "duration": "8주 (Week 5~12)",
                "objective": "기술 검증 및 실증 - PoC 성공률 90% 달성 + 성능 25% 개선 입증 + 레퍼런스 3건 확보",
                "why": "성능 미입증 문제 해결이 제안 경쟁력 확보의 핵심. PoC 실패 시 제안 탈락 가능성 60%",
                "key_deliverables": ["PoC 설계 완료", "실제 데이터 검증 수행", "성능 비교 분석", "신규 레퍼런스 3건"],
                "expected_outcome": "PoC 성공률 90% + 성능 목표 110% 달성 + 기술 평가 65점 이상",
                "related_actions": ["A3", "A4"]
            },
            "phase_2_proposal": {
                "duration": "3주 (Week 13~15)",
                "objective": "제안서 완성 - 차별화 5가지 확립 + 평가 항목 100% 대응 + 경쟁력 35%→65% 향상",
                "why": "PoC 결과를 제안서에 통합하여 경쟁사 대비 차별화 명확히 제시. 완성도 95% 이상 확보",
                "key_deliverables": ["차별화 포인트 5가지", "TCO 분석 완료", "기술 제안서 작성", "리스크 대응 계획"],
                "expected_outcome": "제안서 완성도 95% + 차별화 점수 85점 이상 + 수주 확률 35%→60%",
                "related_actions": ["A5", "A6"]
            }
        },
        "risks": [
            {
                "id": "R1",
                "risk": "AI 모델 성능 목표 미달 (정확도 85% 미만) 발생 시 기술 평가 20점 감점 + 제안 탈락 가능성 60%",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Plan A (예방): 1) 사전 벤치마크 테스트 3종 (Week -2) → 2) 성능 목표 90%로 상향 → 3) 주간 성능 모니터링 → 4) 중간 점검 2회 (Week 2, 4) → 5) 튜닝 전담팀 2명 배치",
                "plan_b": "Plan B (대안): AI 성능 미달 시 → 1) 규칙 기반 로직 하이브리드 구성으로 정확도 80% 보장 → 2) AI 범위 70%로 축소, 나머지 30% 수동 처리 → 3) 6개월 내 단계적 AI 비율 확대 → 4) 추가 비용 10% 이내 → 5) 일정 영향 1주 이내",
                "trigger_condition": "PoC Week 4 중간 점검 시 성공률 70% 미만인 경우 Plan B 발동",
                "mitigation_action_ids": ["A1"]
            }
        ],
        "kpis": [
            {
                "name": "시스템 처리 성능 (TPS)",
                "target": "2,600 TPS (30% 개선, 2025년 12월, 최대 부하 테스트 기준)",
                "baseline": "현재 2,000 TPS (부하 테스트 기준), 경쟁사 평균 2,200 TPS",
                "measurement_method": "Apache JMeter 부하 테스트, 동시 사용자 1,000명 기준",
                "related_actions": ["A1", "A3"]
            }
        ],
        "differentiation": ["차별화 포인트 1", "차별화 포인트 2", "차별화 포인트 3"],
        "appendix": {
            "requirement_groups": [{"category": "기술", "items": ["요구사항1", "요구사항2"]}],
            "fit_table": [
                {
                    "id": "F1",
                    "requirement": "요구사항",
                    "fit_level": "high_fit|partial_fit|low_fit|unknown",
                    "gap_root_cause": "기술 갭의 근본 원인 (예: Java 1.6 레거시 → 보안 취약점 CVE-2021-XXXX → 인증 심사 탈락 위험)",
                    "quantitative_impact": "정량적 영향 (예: 성능 저하율 20%, 보안 취약점 15개, 유지보수 비용 연 30% 증가)",
                    "qualitative_impact": "정성적 영향 (예: 최신 AI 모델 적용 불가, 개발자 확보 어려움)",
                    "suggested_action": "갭 해결 로직 (예: Java 1.6→17 업그레이드 시 성능 25% 개선 + 보안 취약점 100% 해소. 단계: 호환성 분석 2주 → 마이그레이션 6주 → 검증 2주)",
                    "action_ids": ["A1", "A2"]
                }
            ],
            "competitor_counters": [{"company": "경쟁사명", "counter": "대응 전략 키 포인트"}]
        }
    }

    prompt = f"""
🎯 최적 전략 생성 가이드:

다음은 고품질 전략을 위한 권장 개수입니다:

1. appendix.competitor_counters 배열: 6개 이상 권장 (각 경쟁사당 2개씩)
2. prioritized_actions 배열: 8~10개 권장
3. kpis 배열: 8~12개 권장
4. risks 배열: 5개 이상 권장
5. differentiation 배열: 8~10개 권장

✨ 가능한 한 위 개수를 충족하여 상세하고 실행 가능한 전략을 제공하세요!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️⚠️⚠️ 중요: 이것은 실제 수십억원 규모 제안서를 위한 전략 분석입니다. 추상적이거나 간단한 응답은 절대 불가합니다!

당신은 대형 엔터프라이즈 제안의 시니어 전략 컨설턴트입니다.
아래 정보를 바탕으로 **매우 구체적이고 실행 가능하며 차별화된 전략**을 JSON으로 작성하세요.

🚨 필수 요구사항:
- 모든 수치에는 구체적인 검증 근거 필수 (PoC 결과, 벤치마크, 실측 데이터)
- 경쟁사별 고유 기술/제품명을 위에 제공된 SWOT 데이터에서 추출하여 명시
- 모든 차별화 포인트에 정량적 수치와 측정 방법 포함
- 반드시 위 절대적 필수 조건(6개, 10개, 12개, 5개, 10개)을 충족해야 함

[요구사항(카테고리 태깅)]
{req_summary}

[내부 역량 매칭/적합도]
{internal_summary}

[주요 경쟁사 SWOT(요약)]
{competitor_summary}

=== 핵심 요구사항 ===
1) RFP 요구사항과 내부 역량의 적합도를 명확히 식별하고(fit_level=high_fit/partial_fit/low_fit/unknown),
2) 적합도 수준별로 보완/강화 전략을 제시하며,
3) 경쟁사 강점에는 Counter 전략, 약점은 차별화 전략으로 연결하세요.
4) 액션은 Impact × Urgency × Effort 기준으로 우선순위를 정렬하세요.
5) 로드맵은 Pre-Bid → PoC → Proposal 3단계로 작성하세요.
6) 리스크 관리와 KPI를 정의하세요.

📋 작성 가이드:
- 경쟁사 대응: 각 경쟁사별 강점 대응 + 약점 활용 (구체적 제품명, 정량 수치, 검증 근거)
- 액션: Impact/Urgency/Effort 기준 우선순위, why/how/expected_result 상세 작성
- KPI: baseline → target (측정 방법, 경쟁사 비교)
- 리스크: Plan A (예방) + Plan B (대안) + trigger_condition
- 로드맵: duration, objective, why, key_deliverables, expected_outcome (전략 수준)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 경쟁사 대응 전략 형식:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
위에 제공된 [주요 경쟁사 SWOT(요약)] 데이터를 기반으로:

1. 각 경쟁사의 SWOT-S(강점)을 분석하고 → 당사의 대응 전략 제시 (정량 비교)
2. 각 경쟁사의 SWOT-W(약점)을 분석하고 → 당사의 차별화 전략 제시 (정량 비교)

반드시 위 SWOT 데이터에서 실제로 언급된 제품명, 서비스명, 특성을 활용하세요.
하드코딩된 예시를 복사하지 말고, 제공된 실제 데이터를 분석하세요.

⚠️ 각 경쟁사당 최소 2개씩 (강점 대응 1개 + 약점 활용 1개) 작성하세요!

※ 반환은 아래 JSON 스키마 **그대로**만 출력(설명 금지):
{json.dumps(schema_hint, ensure_ascii=False)}
"""
    return prompt


# ======================
# 폴백(LLM 미사용/오류 시) 간단한 오류 반환
# ======================
def _fallback_strategy(
    norm_requirements: List[Requirement],
    internal_matches: List[Dict[str, Any]],
    competitor_profiles: Dict[str, Any]
) -> Dict[str, Any]:
    """LLM 실패 시 최소한의 오류 정보만 반환."""
    return {
        "summary": f"⚠️ AI 분석을 사용할 수 없습니다. 총 {len(norm_requirements)}개 요구사항이 입력되었으나, AI 모델 연결 실패로 전략을 생성하지 못했습니다.",
        "focus": {
            "internal": "AI 분석 실패로 내부 역량 분석을 수행하지 못했습니다.",
            "competitor": f"AI 분석 실패로 경쟁사 {len(competitor_profiles)}개사에 대한 대응 전략을 생성하지 못했습니다.",
            "market": "AI 분석 실패로 시장 트렌드 분석을 수행하지 못했습니다."
        },
        "prioritized_actions": [],
        "roadmap": {
            "phase_0_prebid": {
                "duration": "N/A",
                "objective": "AI 분석 실패",
                "why": "AI 모델에 연결할 수 없어 로드맵을 생성하지 못했습니다.",
                "key_deliverables": [],
                "expected_outcome": "N/A",
                "related_actions": []
            },
            "phase_1_poc": {
                "duration": "N/A",
                "objective": "AI 분석 실패",
                "why": "AI 모델에 연결할 수 없어 로드맵을 생성하지 못했습니다.",
                "key_deliverables": [],
                "expected_outcome": "N/A",
                "related_actions": []
            },
            "phase_2_proposal": {
                "duration": "N/A",
                "objective": "AI 분석 실패",
                "why": "AI 모델에 연결할 수 없어 로드맵을 생성하지 못했습니다.",
                "key_deliverables": [],
                "expected_outcome": "N/A",
                "related_actions": []
            }
        },
        "risks": [],
        "kpis": [],
        "differentiation": [],
        "appendix": {
            "requirement_groups": [],
            "fit_table": [],
            "competitor_counters": []
        },
        "error": True,
        "error_message": "AI 모델 연결 실패로 전략을 생성할 수 없습니다."
    }


# ======================
# Reporter 통합: Deal Brief (1p)
# ======================
def _generate_deal_brief(strategy: Dict[str, Any]) -> str:
    """전략 JSON으로부터 1페이지 분량의 마크다운 브리핑 생성."""
    summary = strategy.get("summary", "전략 요약 없음")
    focus = strategy.get("focus", {})
    actions = strategy.get("prioritized_actions", []) or strategy.get("actions", [])
    roadmap = strategy.get("roadmap", {})
    diff = strategy.get("differentiation", [])
    risks = strategy.get("risks", [])
    kpis = strategy.get("kpis", [])

    def _bullet_actions(items: List[Dict[str, Any]], k: int = 5) -> List[str]:
        out = []
        for a in items[:k]:
            if not isinstance(a, dict):
                continue
            line = f"- {a.get('action', '')}"
            why = a.get("why")
            if why:
                line += f"\n  └ 이유: {why}"
            how = a.get("how")
            if how:
                line += f"\n  └ 방법: {how}"
            approach = a.get("strategy_approach")
            if approach:
                line += f"\n  └ 접근유형: {approach}"
            meta_parts = []
            i, u, e = a.get("impact"), a.get("urgency"), a.get("effort")
            if i: meta_parts.append(f"Impact:{i}")
            if u: meta_parts.append(f"Urgency:{u}")
            if e: meta_parts.append(f"Effort:{e}")
            if meta_parts:
                line += f"\n  └ {', '.join(meta_parts)}"
            tl = a.get("expected_timeline")
            if tl:
                line += f"\n  └ 예상 일정: {tl}"
            exp = a.get("expected_result")
            if exp:
                line += f"\n  └ 기대효과: {exp}"
            out.append(line)
        return out or ["- (항목 없음)"]

    def _risk_lines(rs: List[Dict[str, Any]], k: int = 5) -> List[str]:
        out = []
        for r in rs[:k]:
            if not isinstance(r, dict):
                continue
            line = f"- {r.get('risk','')}"
            li = r.get("likelihood")
            im = r.get("impact")
            if li or im:
                line += f"\n  └ (가능성:{li or '-'}, 영향:{im or '-'})"
            mit = r.get("mitigation")
            if mit:
                line += f"\n  └ 대응: {mit}"
            out.append(line)
        return out or ["- (항목 없음)"]

    def _kpi_lines(kps: List[Dict[str, Any]], k: int = 5) -> List[str]:
        out = []
        for kp in kps[:k]:
            if not isinstance(kp, dict):
                continue
            line = f"- {kp.get('name','')}: 목표={kp.get('target','-')}"
            base = kp.get("baseline")
            if base:
                line += f" (현재치={base})"
            out.append(line)
        return out or ["- (항목 없음)"]

    lines = [
        "# 📈 전략 브리핑 (v3.1)",
        "",
        "## 1) 전략 요약",
        _shorten(summary, 600),
        "",
        "## 2) 전략 포커스",
        f"- **내부**: {_shorten(focus.get('internal','-'), 400)}",
        f"- **경쟁사**: {_shorten(focus.get('competitor','-'), 400)}",
        f"- **시장**: {_shorten(focus.get('market','-'), 400)}",
        "",
        "## 3) 우선순위 액션 (Top 5)",
        *(_bullet_actions(actions, 5)),
        "",
        "## 4) 로드맵",
        f"- **Pre-Bid ({roadmap.get('phase_0_prebid', {}).get('duration', '4주')})**: {roadmap.get('phase_0_prebid', {}).get('objective', '-')}",
        f"  └ {roadmap.get('phase_0_prebid', {}).get('expected_outcome', '-')}",
        f"- **PoC ({roadmap.get('phase_1_poc', {}).get('duration', '8주')})**: {roadmap.get('phase_1_poc', {}).get('objective', '-')}",
        f"  └ {roadmap.get('phase_1_poc', {}).get('expected_outcome', '-')}",
        f"- **Proposal ({roadmap.get('phase_2_proposal', {}).get('duration', '3주')})**: {roadmap.get('phase_2_proposal', {}).get('objective', '-')}",
        f"  └ {roadmap.get('phase_2_proposal', {}).get('expected_outcome', '-')}",
        "",
        "## 5) 리스크 & 대응",
        *(_risk_lines(risks, 5)),
        "",
        "## 6) 핵심 KPI",
        *(_kpi_lines(kpis, 5)),
        "",
        "## 7) 차별화 포인트",
        *([f"- {x}" for x in diff[:5]] or ["- (항목 없음)"])
    ]
    return "\n".join(lines)


# ======================
# 메인 툴 (컨설턴트 레벨 전략 합성 + Reporter 통합)
# ======================
@tool
def strategy_synthesizer(
    requirements: List[Union[str, Dict[str, Any]]],
    internal_matches: Optional[List[Dict[str, Any]]] = None,
    competitor_profiles: Optional[Dict[str, Any]] = None,
    temperature: float = 0.3
) -> dict:
    """
    컨설턴트 수준의 전략 합성기 (Reporter 통합, v3.1)

    입력:
        - requirements: RFP 파서 결과 (문자열 리스트 또는 {text, category})
        - internal_matches: 내부 매칭 결과 목록 [{requirement, match_score, matches: [...] }]
        - competitor_profiles: 경쟁사별 SWOT 요약 {company: {swot: {S, W, O, T}}}
        - temperature: LLM 창의성 조정 파라미터 (기본 0.3)

    출력:
        - strategy: 전체 전략 JSON (요약, 포커스, 액션, 로드맵, 리스크, KPI, appendix 포함)
        - deal_brief: 1페이지 전략 브리핑 Markdown 문자열
    """
    internal_matches = internal_matches or []
    competitor_profiles = competitor_profiles or {}

    print("\n[전략 합성 v3.1] 시작: 컨설턴트 레벨 분석")

    # 1) 요구사항 정규화/카테고리 태깅
    norm_requirements = _normalize_requirements(requirements)

    # 2) 프롬프트 생성
    prompt = _build_v3_1_prompt(norm_requirements, internal_matches, competitor_profiles)

    # 3) LLM 호출 or 폴백
    try:
        if is_llm_available():
            # temperature를 높이고 max_tokens 충분히 확보하여 상세한 응답 유도
            result_text = call_llm(prompt, temperature=0.8, max_tokens=16000)
            print(f"[전략 합성 v3.1] LLM 응답 길이: {len(result_text) if result_text else 0} 문자")
            
            if result_text:
                strategy_data = parse_json_response(result_text)
                if isinstance(strategy_data, dict):
                    # 응답 품질 검증
                    competitor_counters = strategy_data.get('appendix', {}).get('competitor_counters', [])
                    actions = strategy_data.get('prioritized_actions', [])
                    
                    print(f"[전략 합성 v3.1] 경쟁사 대응 개수: {len(competitor_counters)}, 액션 개수: {len(actions)}")
                    
                    # 간단한 응답이면 재시도 (매우 완화된 기준: 1개 이상, 3개 이상)
                    # 실제로는 대부분의 응답이 이보다 많이 생성되므로 기본적으로 통과
                    if len(competitor_counters) < 1 or len(actions) < 3:
                        print("[전략 합성 v3.1] ⚠️ 응답이 너무 간단함, 상세 모드로 재시도...")
                        print(f"    - 필수: 경쟁사 대응 1개 이상, 액션 3개 이상")
                        print(f"    - 현재: 경쟁사 대응 {len(competitor_counters)}개, 액션 {len(actions)}개")
                        
                        # 더 강력한 프롬프트로 재시도
                        enhanced_prompt = f"""
🚨🚨🚨🚨🚨 STOP! 이전 응답 거부됨! 🚨🚨🚨🚨🚨

이전 응답 품질 개선 필요: 
- competitor_counters: {len(competitor_counters)}개 (권장: 6개 이상)
- prioritized_actions: {len(actions)}개 (권장: 8~10개)

🔥🔥🔥 더 상세하고 실행 가능한 전략을 작성하세요:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ competitor_counters: 6개 이상 권장
   위에 제공된 [주요 경쟁사 SWOT(요약)]을 분석하여:
   → 각 경쟁사의 강점(S)에 대한 대응 전략
   → 각 경쟁사의 약점(W)을 활용한 차별화 전략
   
   형식: {{"company": "경쟁사명", "counter": "[SWOT에서 발견한 실제 강점/약점] 대응: [구체적 수치 비교]"}}
   ⚠️ 반드시 위 SWOT 데이터의 실제 내용을 분석하여 작성 (예시 복사 금지)

2️⃣ prioritized_actions: 8~10개 권장
   → A1부터 A8 이상 (A10까지 권장)
   → 각각 why, how, strategy_approach, expected_result 모두 포함
   → 구체적이고 실행 가능한 액션 위주

3️⃣ kpis: 8~12개 권장 (기술/보안/운영 등 다양한 영역 포함)
4️⃣ risks: 5개 이상 권장 (Plan A, Plan B 모두 포함)
5️⃣ differentiation: 8~10개 권장 (정량적 수치 포함)

✨ 더 풍부하고 실행 가능한 전략을 제공하세요!

원래 요청:
{prompt}

지금 즉시 위 개수를 충족하는 JSON을 생성하세요!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
                        
                        result_text = call_llm(enhanced_prompt, temperature=0.95, max_tokens=16000)
                        if result_text:
                            strategy_data_retry = parse_json_response(result_text)
                            if isinstance(strategy_data_retry, dict):
                                # 재시도 결과 재검증
                                retry_counters = strategy_data_retry.get('appendix', {}).get('competitor_counters', [])
                                retry_actions = strategy_data_retry.get('prioritized_actions', [])
                                print(f"[전략 합성 v3.1] 재시도 결과 - 경쟁사 대응: {len(retry_counters)}개, 액션: {len(retry_actions)}개")
                                
                                if len(retry_counters) >= 1 and len(retry_actions) >= 3:
                                    print("[전략 합성 v3.1] ✅ 재시도 성공: 상세 응답 확보")
                                    strategy_data = strategy_data_retry
                                else:
                                    print("[전략 합성 v3.1] ⚠️ 재시도 실패: 여전히 간단함")
                                    # 재시도 실패해도 원래 데이터가 있으면 그것을 사용
                                    if len(competitor_counters) > 0 or len(actions) > 0:
                                        print("[전략 합성 v3.1] 📝 최초 응답 데이터라도 사용")
                                        # strategy_data를 그대로 사용 (이미 설정됨)
                                    else:
                                        print("[전략 합성 v3.1] ⚠️ 데이터 부족 → 폴백 사용")
                                        fb = _fallback_strategy(norm_requirements, internal_matches, competitor_profiles)
                                        return {
                                            "strategy": fb, 
                                            "deal_brief": _generate_deal_brief(fb),
                                            "status": "error",
                                            "message": "❌ AI 응답이 불충분하여 전략을 생성하지 못했습니다. AI 모델이 정상적으로 작동하지 않았거나 응답 품질이 기준에 미달했습니다. (경쟁사 대응 1개 이상, 액션 3개 이상 필요)"
                                        }
                    
                    print("[전략 합성 v3.1] ✅ AI 분석 완료")
                    deal_brief = _generate_deal_brief(strategy_data)
                    return {
                        "strategy": strategy_data, 
                        "status": "success",
                        "message": "✅ AI 기반 전략 분석이 성공적으로 완료되었습니다."
                    }
                else:
                    print("[전략 합성 v3.1] ⚠️ JSON 파싱 실패 → 폴백")
            else:
                print("[전략 합성 v3.1] ⚠️ LLM 응답 없음 → 폴백")
        else:
            print("[전략 합성 v3.1] ⚠️ LLM 미가용 → 폴백")

        # 폴백 생성 (이미 상세하게 개선됨)
        print("[전략 합성 v3.1] 폴백 전략 사용 (상세 모드)")
        fb = _fallback_strategy(norm_requirements, internal_matches, competitor_profiles)
        
        # LLM 미가용 이유 판단
        if not is_llm_available():
            error_msg = "❌ AI 모델에 연결할 수 없습니다. API 키 설정을 확인하거나 네트워크 연결 상태를 점검해주세요."
        elif not result_text:
            error_msg = "❌ AI 모델이 응답하지 않았습니다. 잠시 후 다시 시도해주세요."
        else:
            error_msg = "❌ AI 응답을 JSON으로 파싱할 수 없습니다. AI 모델의 응답 형식이 올바르지 않습니다."
        
        return {
            "strategy": fb, 
            "deal_brief": _generate_deal_brief(fb),
            "status": "fallback",
            "message": error_msg
        }

    except Exception as e:
        print(f"[전략 합성 v3.1] ❌ 예외 발생: {e}")
        fb = _fallback_strategy(norm_requirements, internal_matches, competitor_profiles)
        return {
            "strategy": fb, 
            "deal_brief": _generate_deal_brief(fb),
            "status": "error",
            "message": f"❌ 오류 발생: {str(e)}. 전략을 생성할 수 없습니다."
        }


# ======================
# Backward compatibility aliases
# ======================
strategy_synthesizer_v3 = strategy_synthesizer
strategy_synthesizer_v2 = strategy_synthesizer
