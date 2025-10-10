# -*- coding: utf-8 -*-
"""
컨설턴트 수준 전략 합성기 (Reporter 통합판)

- 입력: RFP 요구사항, 내부 매칭, 경쟁사 분석 요약
- 출력:
    {
      "strategy": { ... 풍부한 전략 JSON ... },
      "deal_brief": "# 📈 전략 브리핑\n..."   # 1p 마크다운 요약
    }

필수 포함 기능:
- 요구사항 카테고리 분류 (기술/보안·품질/사업·운영/기타)
- 갭 분석 (match_score → high/medium/low/unknown)
- 경쟁사 요약 (상위 3개 SWOT 요약 후 카운터/차별화 유도)
- 핵심 전략 요약 (summary + focus: internal/competitor/market)
- 우선순위 액션 플랜 (impact/urgency/effort/due_hint/owner/why)
- 3단계 로드맵 (Pre-bid → PoC → Proposal)
- 리스크 & KPI (likelihood/impact/mitigation)
- Appendix (요구사항 그룹/갭 테이블/경쟁사 대응)
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

# ======================
# 통합 LLM 유틸 로딩
#   - get_llm_client / is_llm_available / call_llm / parse_json_response
# ======================
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from utils.llm_client import get_llm_client, is_llm_available, call_llm, parse_json_response

llm_client = get_llm_client()

# ======================
# LangChain tool decorator (없어도 동작하도록 폴백)
# ======================
try:
    from langchain_core.tools import tool
except Exception:  # LangChain 미사용 환경
    def tool(func):
        return func


# ======================
# 카테고리 정의 & 내부 데이터 모델
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
# 텍스트/전처리 유틸
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
    """입력 requirements 를 내부 표현 Requirement[] 로 정규화 (카테고리 자동 태깅)."""
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


def _score_to_gap_level(score: Optional[float]) -> str:
    """0~1 점수 → gap 등급(high/medium/low/unknown)."""
    if score is None:
        return "unknown"
    try:
        s = float(score)
    except Exception:
        return "unknown"
    if s < 0.45:
        return "high"
    if s < 0.75:
        return "medium"
    return "low"


def _extract_best_matches(related: List[Dict[str, Any]], top_k: int = 3) -> List[str]:
    """내부 레퍼런스 상위 K개 타이틀."""
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
        gap = _score_to_gap_level(score)
        refs = ", ".join(_extract_best_matches(m.get("matches", [])))
        score_disp = f"{score:.2f}" if isinstance(score, (int, float)) else "N/A"
        lines.append(f"- {req} | 적합도: {score_disp} | 갭: {gap} | 레퍼런스: {refs or '없음'}")
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


def _build_v2_prompt(
    norm_requirements: List[Requirement],
    internal_matches: List[Dict[str, Any]],
    competitor_profiles: Dict[str, Any]
) -> str:
    """컨설턴트 수준 전략을 유도하는 시스템 프롬프트 생성."""
    req_summary = "\n".join([f"- [{r.category}] {r.text}" for r in norm_requirements[:12]])
    internal_summary = _format_internal_for_prompt(internal_matches)
    competitor_summary = _format_competitors_for_prompt(competitor_profiles)

    # LLM 출력 스키마 힌트(최소 구조)
    schema_hint = {
        "summary": "상위 3~5문장 요약",
        "focus": {
            "internal": "내부 역량 관점 핵심 방향",
            "competitor": "경쟁사 대비 차별화/대응 방향",
            "market": "시장/정책 동향 관점 핵심 논지"
        },
        "prioritized_actions": [
            {
                "id": "A1",
                "action": "구체적 실행 항목",
                "why": "선정 근거(요구사항/갭/경쟁사 연계)",
                "owner": "담당(Tech/PM/Sales 등)",
                "impact": "high|medium|low",
                "urgency": "high|medium|low",
                "effort": "high|medium|low",
                "due_hint": "예: 2025-Q4",
                "expected_result": "예: PoC 성공률 90% 달성, 성능 25% 개선 예상",
                "related_gaps": ["G1", "G2"],
                "related_risks": ["R1"]
            }
        ],
        "roadmap": {
            "phase_0_prebid": [
                {
                    "task": "사전 IR/레퍼런스 준비",
                    "related_actions": ["A1", "A2"],
                    "expected_outcome": "예: 레퍼런스 5건 확보, 고객 신뢰도 40% 향상"
                }
            ],
            "phase_1_poc": [
                {
                    "task": "PoC 목표/지표/일정",
                    "related_actions": ["A3"],
                    "expected_outcome": "예: PoC 성공률 90%, 기술 검증 완료"
                }
            ],
            "phase_2_proposal": [
                {
                    "task": "제안서 차별화 포인트",
                    "related_actions": ["A4"],
                    "expected_outcome": "예: 차별화 스코어 85점 이상"
                }
            ]
        },
        "risks": [
            {
                "id": "R1",
                "risk": "식별된 리스크",
                "likelihood": "high|medium|low",
                "impact": "high|medium|low",
                "mitigation": "대응 방안",
                "mitigation_action_ids": ["A1", "A2"]
            }
        ],
        "kpis": [
            {
                "name": "핵심 KPI",
                "target": "목표치 (예: 성능 25% 개선)",
                "baseline": "현재치/미정",
                "related_actions": ["A1", "A3"]
            }
        ],
        "differentiation": ["차별화 포인트 1", "차별화 포인트 2", "차별화 포인트 3"],
        "appendix": {
            "requirement_groups": [{"category": "기술", "items": ["요구사항1", "요구사항2"]}],
            "gaps": [
                {
                    "id": "G1",
                    "requirement": "요구사항",
                    "gap": "high|medium|low|unknown",
                    "suggested_action": "보완 액션",
                    "action_ids": ["A1", "A2"]
                }
            ],
            "competitor_counters": [{"company": "경쟁사명", "counter": "대응 전략 키 포인트"}]
        }
    }

    prompt = f"""
당신은 대형 엔터프라이즈 제안의 전략 컨설턴트입니다.
아래 정보를 바탕으로 **실행 가능하고 차별화된 전략**을 JSON으로 작성하세요.

[요구사항(카테고리 태깅)]
{req_summary}

[내부 역량 매칭/적합도/갭]
{internal_summary}

[주요 경쟁사 SWOT(요약)]
{competitor_summary}

---
핵심 요구사항:
1) RFP 요구사항과 내부 역량의 적합도/갭을 명확히 식별하고,
2) 갭(high/medium/low/unknown) 수준별로 보완 전략을 제시하며,
3) 경쟁사 강점에는 카운터 전략, 약점은 차별화 전략으로 연결하세요.
4) 액션은 Impact × Urgency × Effort 기준으로 우선순위를 정렬하세요.
5) 로드맵은 Pre-Bid → PoC → Proposal 3단계로 작성하세요.
6) 리스크 관리와 KPI를 정의하세요.

🔥 실무급 컨설팅 강화 요구사항:
1) **근거 수치화**: 모든 액션, 로드맵, KPI에 구체적인 수치 포함 필수
   - 예: "PoC 성공률 90% → 유지보수 효율 30% 향상 기대"
   - 예: "Java 업그레이드 시 성능 25% 개선 예상"
   - expected_result, expected_outcome 필드에 반드시 퍼센티지와 수치 포함

2) **상호 연계 스토리**: ID 기반으로 흐름 연결
   - Gap(G1, G2...) → Action(A1, A2...) → Risk(R1, R2...) → KPI 연결
   - "기술 갭(G1) → PoC 액션(A3) → 성능 개선 → KPI 향상" 흐름 명확히
   - related_gaps, related_actions, related_risks 필드를 적극 활용

3) **리스크-대응 매핑**: 체계적 연결
   - 각 리스크(R1, R2...)에 대응하는 mitigation_action_ids 명시
   - 각 액션이 어떤 리스크(related_risks)를 완화하는지 명확히
   - 제안서 평가표에 바로 사용 가능한 수준으로 작성

반드시 다음 JSON 스키마만 반환하고, **설명은 절대 추가하지 마세요**:
{json.dumps(schema_hint, ensure_ascii=False)}
"""
    return prompt


# ======================
# 출력 유효성 검증
# ======================
def _validate_strategy_data(data: Dict[str, Any]) -> bool:
    """LLM 응답의 JSON 스키마 검증(최소 요건)."""
    required_top = ["summary", "focus", "prioritized_actions", "roadmap", "risks", "kpis", "differentiation", "appendix"]
    if not all(k in data for k in required_top):
        return False

    if not isinstance(data.get("summary", ""), str):
        return False

    focus = data.get("focus", {})
    for k in ["internal", "competitor", "market"]:
        if k not in focus or not isinstance(focus[k], str):
            return False

    if not isinstance(data.get("prioritized_actions", []), list):
        return False
    if not isinstance(data.get("differentiation", []), list):
        return False

    roadmap = data.get("roadmap", {})
    for phase in ["phase_0_prebid", "phase_1_poc", "phase_2_proposal"]:
        if phase not in roadmap:
            return False
        # LLM이 객체리스트 또는 문자열 리스트로 줄 수 있으니 최소 존재만 체크

    appendix = data.get("appendix", {})
    if not isinstance(appendix, dict):
        return False

    return True


# ======================
# 폴백(LLM 미사용/오류 시) 전략 생성
# ======================
def _fallback_strategy(
    norm_requirements: List[Requirement],
    internal_matches: List[Dict[str, Any]],
    competitor_profiles: Dict[str, Any]
) -> Dict[str, Any]:
    """LLM 실패 시 규칙 기반으로 동일 스키마 전략 생성."""
    # 요구사항별 매칭 딕셔너리
    match_by_req: Dict[str, Dict[str, Any]] = {m.get("requirement", ""): m for m in internal_matches}

    gaps: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []

    for i, r in enumerate(norm_requirements):
        m = match_by_req.get(r.text) or {}
        score = m.get("match_score")
        gap = _score_to_gap_level(score)

        if gap == "high":
            action = {
                "id": f"A{i+1}",
                "action": f"{r.text}: 외부 보안/전문 파트너 즉시 소싱",
                "why": f"내부 적합도 낮음(gap={gap})",
                "owner": "PMO",
                "impact": "high",
                "urgency": "high",
                "effort": "medium",
                "due_hint": "2025-Q4",
                "expected_result": "PoC 성공률 90% 가정 시 리스크 30% 감소",
                "related_gaps": [f"G{i+1}"],
                "related_risks": ["R1"]
            }
        elif gap == "medium":
            action = {
                "id": f"A{i+1}",
                "action": f"{r.text}: PoC로 기술 검증 및 레퍼런스 보강",
                "why": f"부분 적합(보완 필요, gap={gap})",
                "owner": "TechLead",
                "impact": "high",
                "urgency": "medium",
                "effort": "medium",
                "due_hint": "2026-Q1",
                "expected_result": "성능 20% 개선, PoC 통과율 85% 달성 예상",
                "related_gaps": [f"G{i+1}"],
                "related_risks": ["R2"]
            }
        else:
            action = {
                "id": f"A{i+1}",
                "action": f"{r.text}: 기존 레퍼런스 강조·제안서 반영",
                "why": f"적합도 양호(gap={gap})",
                "owner": "Sales/Proposal",
                "impact": "medium",
                "urgency": "low",
                "effort": "low",
                "due_hint": "2026-Q1",
                "expected_result": "기술점수 5~10% 개선 기대",
                "related_gaps": [f"G{i+1}"],
                "related_risks": []
            }

        actions.append(action)
        gaps.append({
            "id": f"G{i+1}",
            "requirement": r.text,
            "gap": gap,
            "suggested_action": action["action"],
            "action_ids": [action["id"]]
        })

    # 경쟁사 카운터
    competitor_counters: List[Dict[str, str]] = []
    for company, profile in list(competitor_profiles.items())[:3]:
        sw = profile.get("swot", {})
        if sw.get("S"):
            competitor_counters.append({
                "company": company,
                "counter": f"{company} 강점({_shorten(_to_text(sw['S']), 80)}) 대응: 고객맞춤/민첩 PoC로 차별화"
            })
        if sw.get("W"):
            competitor_counters.append({
                "company": company,
                "counter": f"{company} 약점({_shorten(_to_text(sw['W']), 80)}) 활용: 가격/일정 민첩성 강조"
            })

    # 요구사항 그룹
    groups: Dict[str, List[str]] = {}
    for r in norm_requirements:
        groups.setdefault(r.category, []).append(r.text)

    strategy = {
        "summary": "내부 적합도와 경쟁사 SWOT을 바탕으로 갭은 PoC/외부협력으로 보완하고, 강점 레퍼런스를 전면 배치합니다.",
        "focus": {
            "internal": "적합도가 높은 영역은 레퍼런스로 신뢰성 강화, 중간/낮은 영역은 PoC·파트너로 보완",
            "competitor": "대기업 강점에는 민첩성과 맞춤 제안으로 대응, 약점은 PoC 속도/가격 경쟁력으로 공략",
            "market": "디지털 전환/AI 확산 추세를 KPI와 연동해 제안서에 수치 반영"
        },
        "prioritized_actions": actions[:10],
        "roadmap": {
            "phase_0_prebid": [
                {"task": "레퍼런스 큐레이션", "related_actions": [a["id"] for a in actions[:3]], "expected_outcome": "레퍼런스 5건 확보"},
                {"task": "고객 IR 포인트 정리", "related_actions": [actions[0]["id"]], "expected_outcome": "핵심 메시지 3건 정리"},
                {"task": "보안/인증 선제 점검", "related_actions": [], "expected_outcome": "ISMS 체크리스트 100% 대비"}
            ],
            "phase_1_poc": [
                {"task": "핵심 요구 1~2개 축소 범위 PoC", "related_actions": [a["id"] for a in actions], "expected_outcome": "PoC 성공률 ≥ 90%"},
                {"task": "성공 기준/지표 명시", "related_actions": [], "expected_outcome": "KPI 정의/측정 체계 확립"},
                {"task": "기간·리스크 관리", "related_actions": [], "expected_outcome": "지연 ≤ 10%"}
            ],
            "phase_2_proposal": [
                {"task": "차별화 포인트 도식화", "related_actions": [], "expected_outcome": "차별화 점수 85점 이상"},
                {"task": "비용·일정 시나리오 2안", "related_actions": [], "expected_outcome": "TCO 대비 10~15% 절감안"},
                {"task": "리스크 및 완화책 명시", "related_actions": [], "expected_outcome": "심사 리스크 30%↓"}
            ]
        },
        "risks": [
            {"id": "R1", "risk": "보안 인증 지연", "likelihood": "medium", "impact": "high", "mitigation": "사전 심사·필수 문서 체크리스트", "mitigation_action_ids": []},
            {"id": "R2", "risk": "PoC 범위 과대", "likelihood": "medium", "impact": "medium", "mitigation": "핵심 기능 1~2개로 Scope 축소", "mitigation_action_ids": []}
        ],
        "kpis": [
            {"name": "PoC 성공 기준 달성률", "target": ">= 90%", "baseline": "-", "related_actions": [a["id"] for a in actions]},
            {"name": "제안서 기술점수", "target": ">= 상위 10%", "baseline": "-", "related_actions": [a["id"] for a in actions[:3]]}
        ],
        "differentiation": [
            "고객 맞춤형 PoC와 신속한 의사결정",
            "레퍼런스 기반 신뢰 확보",
            "민첩한 일정/가격 구성"
        ],
        "appendix": {
            "requirement_groups": [{"category": k, "items": v} for k, v in groups.items()],
            "gaps": gaps,
            "competitor_counters": competitor_counters
        }
    }

    # 리스크-액션 매핑 보정(간단 연결)
    for r in strategy["risks"]:
        if r["id"] == "R1":
            r["mitigation_action_ids"] = [a["id"] for a in actions if "보안" in a["action"] or "ISMS" in a.get("why","")]
        if r["id"] == "R2":
            r["mitigation_action_ids"] = [a["id"] for a in actions if "PoC" in a["action"]]

    return strategy


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
                line += f"  \n  └ 이유: {why}"
            owner = a.get("owner")
            if owner:
                line += f"  \n  └ 담당: {owner}"
            i, u, e = a.get("impact"), a.get("urgency"), a.get("effort")
            meta_parts = []
            if i: meta_parts.append(f"Impact:{i}")
            if u: meta_parts.append(f"Urgency:{u}")
            if e: meta_parts.append(f"Effort:{e}")
            if meta_parts:
                line += f"  \n  └ {', '.join(meta_parts)}"
            due = a.get("due_hint")
            if due:
                line += f"  \n  └ Due:{due}"
            exp = a.get("expected_result")
            if exp:
                line += f"  \n  └ 기대효과:{exp}"
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
                line += f"  \n  └ (가능성:{li or '-'}, 영향:{im or '-'})"
            mit = r.get("mitigation")
            if mit:
                line += f"  \n  └ 대응: {mit}"
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
        "# 📈 전략 브리핑",
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
        f"- **Pre-Bid**: {', '.join([i.get('task','') if isinstance(i,dict) else str(i) for i in roadmap.get('phase_0_prebid', [])]) or '-'}",
        f"- **PoC**: {', '.join([i.get('task','') if isinstance(i,dict) else str(i) for i in roadmap.get('phase_1_poc', [])]) or '-'}",
        f"- **Proposal**: {', '.join([i.get('task','') if isinstance(i,dict) else str(i) for i in roadmap.get('phase_2_proposal', [])]) or '-'}",
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
    컨설턴트 수준의 전략 합성기 (Reporter 통합)
    
    입력:
        - requirements: RFP 파서 결과 (문자열 리스트 또는 {text, category})
        - internal_matches: 내부 매칭 결과 목록 [{requirement, match_score, matches: [...] }]
        - competitor_profiles: 경쟁사별 SWOT 요약 {company: {swot: {S, W, O, T}}}
        - temperature: LLM 창의성 조정 파라미터 (기본 0.3)
    
    출력:
        - strategy: 전체 전략 JSON (요약, 포커스, 액션, 로드맵, 리스크, KPI 포함)
        - deal_brief: 1페이지 전략 브리핑 Markdown 문자열
    """
    internal_matches = internal_matches or []
    competitor_profiles = competitor_profiles or {}

    print("\n[전략 합성 v2] 시작: 컨설턴트 레벨 분석")

    # 1) 요구사항 정규화/카테고리 태깅
    norm_requirements = _normalize_requirements(requirements)

    # 2) LLM 사용 가능 여부 판단
    use_llm = is_llm_available()

    # 3) 프롬프트 생성
    prompt = _build_v2_prompt(norm_requirements, internal_matches, competitor_profiles)

    # 4) LLM 호출 or 폴백
    try:
        if use_llm:
            result_text = call_llm(prompt, temperature=temperature)
            if result_text:
                strategy_data = parse_json_response(result_text)
                if isinstance(strategy_data, dict) and _validate_strategy_data(strategy_data):
                    print("[전략 합성 v2] ✅ AI 분석 완료")
                    deal_brief = _generate_deal_brief(strategy_data)
                    return {"strategy": strategy_data, "deal_brief": deal_brief}
                else:
                    print("[전략 합성 v2] ⚠️ JSON 파싱/유효성 실패 → 폴백")
            else:
                print("[전략 합성 v2] ⚠️ LLM 응답 없음 → 폴백")
        else:
            print("[전략 합성 v2] ⚠️ LLM 미가용 → 폴백")

        # 폴백 생성
        fb = _fallback_strategy(norm_requirements, internal_matches, competitor_profiles)
        return {"strategy": fb, "deal_brief": _generate_deal_brief(fb)}

    except Exception as e:
        print(f"[전략 합성 v2] ❌ 예외 발생: {e}")
        fb = _fallback_strategy(norm_requirements, internal_matches, competitor_profiles)
        return {"strategy": fb, "deal_brief": _generate_deal_brief(fb)}


# ======================
# Alias for backward compatibility
# ======================
strategy_synthesizer_v2 = strategy_synthesizer


# ======================
# 디버그 단독 실행
# ======================
if __name__ == "__main__":
    dummy_requirements = [
        "AI 모델 성능 검증 및 모니터링 체계 구축",
        "보안 인증(ISO/ISMS-P) 및 접근성 준수",
        "클라우드 상용/국산 혼합 아키텍처 설계",
        "운영 전환 및 유지보수 체계 수립"
    ]

    dummy_internal_matches = [
        {"requirement": "AI 모델 성능 검증 및 모니터링 체계 구축", "match_score": 0.82,
         "matches": [{"title": "A사 AI 모델 관측성 프로젝트"}, {"title": "B사 예측정비 PoC"}]},
        {"requirement": "보안 인증(ISO/ISMS-P) 및 접근성 준수", "match_score": 0.41, "matches": []},
        {"requirement": "클라우드 상용/국산 혼합 아키텍처 설계", "match_score": 0.67,
         "matches": [{"title": "하이브리드 멀티클라우드 전환"}]},
    ]

    dummy_competitors = {
        "삼성 SDS": {"swot": {"S": "브랜드/클라우드 생태계 연계", "W": "가격 민첩성 제한", "O": "AI 클라우드 성장", "T": "신규 경쟁자 등장"}},
        "LG CNS": {"swot": {"S": "대규모 SI 경험", "W": "민첩성 부족", "O": "공공 클라우드 확대", "T": "예산 압박"}},
        "네이버클라우드": {"swot": {"S": "국산 클라우드 생태계", "W": "특정 산업 레퍼런스 제한", "O": "공공 클라우드 확대", "T": "글로벌 경쟁 심화"}}
    }

    result = strategy_synthesizer.invoke({
        "requirements": dummy_requirements,
        "internal_matches": dummy_internal_matches,
        "competitor_profiles": dummy_competitors,
        "temperature": 0.2
    })

    print("\n🎯 전략 합성 v2 결과(JSON):")
    print(json.dumps(result, ensure_ascii=False, indent=2))
