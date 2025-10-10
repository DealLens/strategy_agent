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

# ======================
# LLM 유틸
# ======================
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
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
            "phase_0_prebid": [
                {
                    "task": "레퍼런스 큐레이션 (담당: Sales 3명/PM 1명, 2주, Week 1~2)",
                    "related_actions": ["A1", "A2"],
                    "dependencies": [],
                    "parallel_tasks": ["보안 인증 점검", "파트너사 선정"],
                    "resources": "Sales 3명 + PM 1명 (full-time)",
                    "milestones": "Week 2: 레퍼런스 5건 확보 확인",
                    "expected_outcome": "레퍼런스 5~7건 확보 → 고객 신뢰도 40% 향상 → IR 자료 95% 완성 → 초기 평가 85% 통과"
                }
            ],
            "phase_1_poc": [
                {
                    "task": "PoC 환경 구축 및 검증 (담당: Tech 5명, 4주, Week 5~8)",
                    "related_actions": ["A3"],
                    "dependencies": ["레퍼런스 큐레이션 완료", "요구사항 매핑 100%"],
                    "parallel_tasks": [],
                    "resources": "Tech Lead 1명 + 개발자 4명 (full-time)",
                    "milestones": "Week 6: 환경 구축 완료, Week 8: PoC 성공률 90% 이상",
                    "expected_outcome": "PoC 성공률 90% → 성능 25% 개선 입증 → 신규 레퍼런스 3건 → 기술 평가 8점 추가"
                }
            ],
            "phase_2_proposal": [
                {
                    "task": "제안서 작성 및 차별화 (담당: Proposal 4명, 1주, Week 12~13)",
                    "related_actions": ["A4"],
                    "dependencies": ["PoC 완료", "모든 증빙 자료 준비"],
                    "parallel_tasks": ["발표 자료 작성", "Q&A 준비"],
                    "resources": "Proposal Writer 2명 + Reviewer 2명",
                    "milestones": "Week 13: 제안서 완성도 95%, 차별화 점수 85점 이상",
                    "expected_outcome": "차별화 요소 5가지 확립 → 평가 항목 100% 대응 → 제안 경쟁력 65점 → 수주 확률 60%"
                }
            ]
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
당신은 대형 엔터프라이즈 제안의 전략 컨설턴트입니다.
아래 정보를 바탕으로 **매우 구체적이고 실행 가능하며 차별화된 전략**을 JSON으로 작성하세요.

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

🔥🔥🔥 실전급 컨설팅 필수 요구사항 (5대 핵심 개선):

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ 기술 갭 원인 및 영향 분석 강화 (근본 원인 → 영향 → 해결책)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Fit Table (적합도 테이블)** 작성 시 반드시 포함:
- 각 요구사항의 **기술 갭 원인** 상세 분석
  예: "Java 1.6 레거시 → 보안 취약점 CVE-2021-XXXX 존재 → 인증 심사 탈락 위험"
  예: "Spring 3.1 EOL → 최신 라이브러리 호환 불가 → 성능 저하 20% 발생"
  
- **정량적 영향** 명시
  예: "성능 저하율 20%", "보안 취약점 15개", "인력 수급 난이도 +40%", "유지보수 비용 연 30% 증가"
  
- **정성적 영향** 명시
  예: "최신 AI 모델 적용 불가", "클라우드 네이티브 마이그레이션 제약", "개발자 확보 어려움"

- suggested_action에 **갭 해결 로직** 포함
  예: "현재 Java 1.6 → Java 17 업그레이드 시 성능 25% 개선 + 보안 취약점 100% 해소 + 개발 생산성 35% 향상 예상. 단계: 1) 호환성 분석 2주 → 2) 테스트 환경 구축 1주 → 3) 단계적 마이그레이션 6주 → 4) 성능 검증 2주"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2️⃣ 경쟁사별 정밀 대응 전략 (기술 특성 기반)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Competitor Counters** 작성 시 각 경쟁사의 기술 특성 반영:
- 삼성 SDS: "Cloud SaaS 전환 강점" → 당사 대응: "온프레미스-클라우드 하이브리드 아키텍처로 유연성 2배, TCO 15% 절감 입증"
- LG CNS: "MLOps 내재화 역량" → 당사 대응: "AutoML 파이프라인으로 개발 기간 40% 단축, 운영 비용 25% 절감"
- 현대오토에버: "차량 IoT 특화" → 당사 대응: "범용 IoT 플랫폼 + 커스터마이징으로 확장성 3배, 타 산업 적용 가능"

**Focus.competitor**에서 각 경쟁사별 구체적 전략 명시:
- 추상적 ❌: "대기업 강점에는 민첩성으로 대응"
- 구체적 ✅: "삼성 SDS의 Brity Works AI 대응: 당사 맞춤형 AI 파이프라인으로 정확도 5% 우위 + 구축 기간 30% 단축. LG CNS의 DAP 플랫폼 대응: 오픈소스 기반 비용 40% 절감 + 벤더 종속성 제로. 현대오토에버의 차량 특화 대응: 범용 플랫폼으로 확장성 3배 + 타 산업 레퍼런스 8건 보유"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3️⃣ KPI 측정 기준 명확화 (Before-After 필수)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**모든 KPI**에 반드시 포함:
- name: 구체적이고 측정 가능한 지표
  예: "시스템 처리 성능 (TPS)", "API 응답 속도 (ms)", "월간 장애 건수"
  
- baseline: 현재 수치 + 측정 방법
  예: "현재 2,000 TPS (최대 부하 테스트 기준)", "현재 응답속도 1.2초 (p95 기준)", "현재 월 평균 장애 3.5건"
  
- target: 목표 수치 + 달성 시기 + 측정 방법
  예: "목표 2,600 TPS (30% 개선, 2025년 12월, 동일 부하 테스트 기준)", "0.5초 이하 (58% 개선, p95 기준)", "월 1건 이하 (71% 감소)"
  
- 경쟁사 비교 포함
  예: "경쟁사 평균 2,200 TPS 대비 18% 우수", "업계 표준 0.8초 대비 38% 우수"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4️⃣ 로드맵 실행 연결성 강화 (의존성+병행+리소스)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Roadmap 각 task**에 추가 정보 포함:
- task 이름에 담당자+기간 명시: "레퍼런스 큐레이션 (담당: Sales 3명/PM 1명, 2주, Week 1~2)"
  
- dependencies: 선행 작업 명시
  예: {"task": "PoC 환경 구축", "dependencies": ["레퍼런스 큐레이션 완료", "요구사항 매핑 100%"], ...}
  
- parallel_tasks: 병행 가능한 작업들
  예: "보안 인증 점검"과 "파트너사 선정"은 병행 가능 (Week 1~2 동시 진행)
  
- resources: 투입 리소스
  예: "Tech Lead 1명(full-time) + 개발자 3명(50% 할당) + PM 1명(full-time)"
  
- milestones: 체크포인트
  예: "Week 2 종료: 레퍼런스 3건 이상 확보 확인, Week 4 종료: PoC 중간 점검 (성공률 70% 이상)"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5️⃣ 리스크 대응 실효성 강화 (Plan A + Plan B 필수)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**각 리스크**에 반드시 포함:
- risk: 구체적 시나리오 + 정량적 영향
  예: "AI 모델 성능 목표 미달 (정확도 85% 미만) 발생 시 기술 평가 20점 감점 + 제안 탈락 가능성 60%"
  
- mitigation (Plan A): 예방 중심 5단계 대응
  예: "1) 사전 벤치마크 테스트 3종 수행 (Week -2) → 2) 성능 목표치 90%로 상향 설정 → 3) 주간 성능 모니터링 (목표 대비 진척률) → 4) 중간 점검 2회 (Week 2, 4) → 5) 성능 튜닝 전담팀 2명 배치"
  
- **plan_b (대안 시나리오)** 신규 추가:
  예: "Plan B: AI 성능 미달 시 → 1) 기존 규칙 기반 로직과 하이브리드 구성으로 정확도 80% 보장 → 2) AI 모델 범위를 70%로 축소하고 나머지 30%는 수동 처리 병행 → 3) 향후 6개월 내 단계적 AI 비율 확대 계획 제시 → 4) 추가 개발 비용 10% 이내로 제한 → 5) 일정 영향 최소화 (1주 이내)"
  
- **trigger_condition (발동 조건)** 명시:
  예: "PoC Week 4 중간 점검 시 성공률 70% 미만인 경우 Plan B 즉시 발동"

⚠️⚠️⚠️ 반드시 지켜야 할 5대 원칙:
1. 모든 수치에 측정 기준 명시 (예: "성능 20% 개선" → "응답속도 1.2초→0.96초, p95 기준 20% 개선")
2. 모든 기간에 구체적 시작/종료 시점 (예: "2025년 11월 1일~12월 24일, 8주")
3. 모든 경쟁사 대응에 해당 경쟁사의 구체적 기술/제품명 포함
4. 모든 리스크에 Plan B 대안 시나리오 필수
5. 모든 로드맵 task에 의존성(dependencies) 및 병행 가능 여부(parallel_tasks) 명시

※ 반환은 아래 JSON 스키마 **그대로**만 출력(설명 금지):
{json.dumps(schema_hint, ensure_ascii=False)}
"""
    return prompt


# ======================
# 폴백(LLM 미사용/오류 시) 전략 생성
# ======================
def _fallback_strategy(
    norm_requirements: List[Requirement],
    internal_matches: List[Dict[str, Any]],
    competitor_profiles: Dict[str, Any]
) -> Dict[str, Any]:
    """LLM 실패 시 규칙 기반으로 동일 스키마 전략 생성 (fit_level/expected_timeline 반영)."""
    match_by_req: Dict[str, Dict[str, Any]] = {m.get("requirement", ""): m for m in internal_matches}

    fit_rows: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []

    for i, r in enumerate(norm_requirements):
        m = match_by_req.get(r.text) or {}
        score = m.get("match_score")
        fit_level = _score_to_fit_level(score)
        fit_id = f"F{i+1}"

        if fit_level == "low_fit":
            action = {
                "id": f"A{i+1}",
                "action": f"{r.text}: 외부 전문 파트너 즉시 소싱 및 협업 체계 구축",
                "why": f"내부 적합도 낮음(fit_level={fit_level}, 매칭 점수 {score if score else 'N/A'}). 즉시 보완하지 않을 경우 제안 탈락 가능성 높음. 경쟁사는 이미 관련 레퍼런스 3건 이상 보유.",
                "how": "1단계(1주): 전문 파트너사 3곳 선정 및 NDA 체결 → 2단계(1주): 요구사항 상세 매핑 워크샵 → 3단계(2주): 공동 솔루션 설계 및 PoC 계획 수립 → 4단계(4주): 파일럿 구축 및 검증 → 5단계(1주): 결과 문서화 및 제안서 반영",
                "strategy_approach": "Partnership",
                "owner": "PMO/Partnership Lead",
                "impact": "high",
                "urgency": "high",
                "effort": "medium",
                "expected_timeline": "2025년 10월~12월 (9주 소요)",
                "expected_result": "리스크 35% 감소 → PoC 성공률 90% 달성 → 제안 경쟁력 30% 향상 → 기술 평가 점수 12점 확보 (20점 만점)",
                "related_fit_ids": [fit_id],
                "related_risks": ["R1", "R3"]
            }
        elif fit_level == "partial_fit":
            action = {
                "id": f"A{i+1}",
                "action": f"{r.text}: 집중 PoC로 기술 검증 및 레퍼런스 3건 보강",
                "why": f"부분 적합(fit_level={fit_level}, 매칭 점수 {score if score else 'N/A'}). 기본 역량은 있으나 실제 성능 입증 필요. 경쟁사 대비 레퍼런스 2건 부족.",
                "how": "1단계(1주): 핵심 기능 2~3개 선정 및 PoC 범위 정의 → 2단계(1주): 테스트 시나리오 3종 설계 및 환경 구축 → 3단계(3주): 실제 데이터로 검증 수행 (주 1회 중간 보고) → 4단계(1주): 성능 지표 분석 및 개선 → 5단계(1주): 결과 보고서 작성 및 레퍼런스 확보 → 6단계(1주): 제안서 반영",
                "strategy_approach": "Offensive",
                "owner": "Tech Lead/Solution Architect",
                "impact": "high",
                "urgency": "medium",
                "effort": "medium",
                "expected_timeline": "2025년 11월~2026년 1월 (8주 소요)",
                "expected_result": "성능 25% 개선 입증 → PoC 통과율 85% → 신규 레퍼런스 3건 확보 → 기술 평가 8점 추가 확보 → 제안 신뢰도 40% 향상",
                "related_fit_ids": [fit_id],
                "related_risks": ["R2", "R4"]
            }
        else:  # high_fit or unknown
            action = {
                "id": f"A{i+1}",
                "action": f"{r.text}: 기존 레퍼런스 전략적 활용 및 제안서 최적화",
                "why": f"적합도 양호(fit_level={fit_level}, 매칭 점수 {score if score else 'N/A'}). 이미 검증된 강점 영역으로 경쟁사 대비 우위 확보 가능.",
                "how": "1단계(3일): 관련 레퍼런스 5~7건 선별 → 2단계(3일): 성공사례 요약본 작성 (문제/해결/성과 구조) → 3단계(2일): 핵심 지표 도식화 (before/after 비교) → 4단계(2일): 평가표 항목별 매핑 및 증빙 자료 준비 → 5단계(2일): 제안서 기술 섹션 작성 및 검토",
                "strategy_approach": "Differentiation",
                "owner": "Sales/Proposal Team",
                "impact": "medium",
                "urgency": "low",
                "effort": "low",
                "expected_timeline": "2025년 11월 (2주 소요)",
                "expected_result": "기술 평가 점수 5~8점 추가 확보 → 차별화 요소 3가지 명확화 → 고객 신뢰도 20% 향상 → 제안서 완성도 90% 이상",
                "related_fit_ids": [fit_id],
                "related_risks": []
            }

        actions.append(action)
        
        # 기술 갭 원인 및 영향 분석 (1️⃣ 개선)
        if fit_level == "low_fit":
            gap_root_cause = f"내부 역량 부족 (적합도 점수 {score if score else '0.3'}/1.0 미만) → 관련 레퍼런스 0건 → 기술 검증 미비 → 제안 탈락 위험 60%"
            quantitative_impact = f"기술 평가 감점 15~20점 예상, 제안 경쟁력 40% 저하, PoC 실패율 50% 이상, 추가 개발 비용 30% 증가"
            qualitative_impact = f"고객 신뢰도 저하, 경쟁사 대비 기술 열위 인식, 향후 유지보수 리스크 증가, 인력 수급 어려움"
            suggested_detail = f"{action['action']} - 갭 해결: 전문 파트너사 3곳 평가 (NDA 체결) → 공동 솔루션 설계 9주 → 기술 검증 완료 → 레퍼런스 확보. 예상 효과: 기술 리스크 35% 감소 → PoC 성공률 90% → 기술 평가 12점 확보 → 제안 경쟁력 30% 향상."
        elif fit_level == "partial_fit":
            gap_root_cause = f"부분 역량 보유 (적합도 점수 {score if score else '0.6'}/1.0) → 레퍼런스 1~2건 → 성능 입증 부족 → 차별화 약화"
            quantitative_impact = f"기술 평가 감점 5~10점 예상, 성능 검증 부재로 신뢰도 25% 저하, PoC 실패율 20%"
            qualitative_impact = f"경쟁사 대비 레퍼런스 부족 (당사 1~2건 vs 경쟁사 4~5건), 실제 성능 미입증, 고객 우려 존재"
            suggested_detail = f"{action['action']} - 갭 보완: 핵심 기능 2~3개 선정 → 테스트 시나리오 3종 설계 → 8주 집중 PoC (주 1회 보고) → 성능 25% 개선 입증 → 레퍼런스 3건 확보. 예상 효과: 기술 평가 8점 추가 → 제안 신뢰도 40% 향상 → 경쟁사 대비 우위 확보."
        else:
            gap_root_cause = f"충분한 역량 보유 (적합도 점수 {score if score else '0.8'}/1.0 이상) → 레퍼런스 3건 이상 → 기술 검증 완료 → 강점 영역"
            quantitative_impact = f"기술 평가 가점 5~8점 가능, 차별화 요소 2~3가지 확보 가능, 제안 경쟁력 20% 향상"
            qualitative_impact = f"고객 신뢰도 확보, 경쟁사 대비 기술 우위, 안정적 프로젝트 수행 가능"
            suggested_detail = f"{action['action']} - 강점 활용: 레퍼런스 5~7건 선별 → 성공사례 요약 (문제/해결/성과) → 지표 도식화 → 평가표 매핑 → 2주 제안서 반영. 예상 효과: 기술 평가 5~8점 추가 → 차별화 3가지 확립 → 제안서 완성도 90% 이상."
        
        fit_rows.append({
            "id": fit_id,
            "requirement": r.text,
            "fit_level": fit_level,
            "gap_root_cause": gap_root_cause,
            "quantitative_impact": quantitative_impact,
            "qualitative_impact": qualitative_impact,
            "suggested_action": suggested_detail,
            "action_ids": [action["id"]]
        })

    # 경쟁사 카운터
    competitor_counters: List[Dict[str, str]] = []
    for company, profile in list(competitor_profiles.items())[:3]:
        sw = profile.get("swot", {})
        if sw.get("S"):
            competitor_counters.append({
                "company": company,
                "counter": f"{company} 강점 분석: {_shorten(_to_text(sw['S']), 100)} | 당사 대응 전략: 1) 실제 성능 비교 데이터 3건 제시하여 객관적 우위 입증 2) 의사결정 속도 2배 빠름 강조 (평균 응답시간 24시간 vs 경쟁사 48시간) 3) 맞춤형 PoC 제공으로 고객 요구사항 부합도 90% 달성 4) 파트너십 활용한 전문성 보완 (검증된 파트너 3곳 보유) 5) 비용 효율성 15% 우위 (TCO 분석 기반)"
            })
        if sw.get("W"):
            competitor_counters.append({
                "company": company,
                "counter": f"{company} 약점 분석: {_shorten(_to_text(sw['W']), 100)} | 당사 차별화 전략: 1) 유연한 일정 조정 (주 단위 조정 가능) 및 신속한 대응 체계 2) 가격 경쟁력 10~15% 우위 (TCO 기준) 3) 중소 규모 민첩성 활용하여 맞춤형 솔루션 제공 4) 의사결정 단계 3단계 축소로 승인 속도 2배 향상 5) 고객 요구사항 변경에 즉각 대응 (48시간 내 수정안 제시)"
            })

    # 요구사항 그룹
    groups: Dict[str, List[str]] = {}
    for r in norm_requirements:
        groups.setdefault(r.category, []).append(r.text)

    strategy = {
        "summary": f"총 {len(norm_requirements)}개 요구사항 중 내부 적합도 분석 결과, High Fit 영역은 기존 레퍼런스 {len([a for a in actions if a.get('strategy_approach')=='Differentiation'])}건으로 신뢰성을 강화하고, Partial Fit 영역 {len([a for a in actions if a.get('strategy_approach')=='Offensive'])}건은 8~12주 집중 PoC로 성능 25% 개선을 입증하며, Low Fit 영역 {len([a for a in actions if a.get('strategy_approach')=='Partnership'])}건은 전문 파트너사 협업으로 9주 내 보완합니다. 경쟁사 {len(competitor_counters)}개사 대비 의사결정 속도 2배, 비용 효율성 15% 우위를 확보하여 제안 경쟁력을 35%에서 65%로 향상시킵니다. 전체 일정은 Pre-Bid 4주 → PoC 8주 → Proposal 3주로 총 15주 소요 예상이며, 수주 후 6개월 내 핵심 KPI 12개 달성을 목표로 합니다.",
        "focus": {
            "internal": f"검증된 High Fit 영역 {len([a for a in actions if a.get('strategy_approach')=='Differentiation'])}건은 레퍼런스 5~7건씩 확보하여 기술 평가 점수 평균 8점 추가 확보. Partial Fit 영역은 실제 데이터 기반 PoC로 성능 20~25% 개선 입증 및 신규 레퍼런스 3건 확보. Low Fit 영역은 검증된 파트너사 3곳 중 최적 1곳 선정하여 공동 솔루션 구축, 기술 리스크 35% 감소 달성.",
            "competitor": f"주요 경쟁사 {len(list(competitor_profiles.keys())[:3])}개사 분석 결과, 대기업의 브랜드 파워에는 실제 성능 비교 데이터 3건 제시 및 의사결정 속도 2배 우위 강조. 경쟁사 평균 제안 준비 기간 20주 대비 당사 15주로 25% 단축. 가격 경쟁력은 TCO 기준 10~15% 절감안 제시하고, 맞춤형 PoC 제안으로 고객 요구사항 부합도 90% 이상 달성.",
            "market": "AI/디지털 전환 시장 연평균 25% 성장 추세 활용, 공공/금융 분야 클라우드 전환율 2025년 60% 예상을 제안서에 반영. 최신 기술 트렌드 5가지(생성 AI, 하이브리드 클라우드, 제로트러스트 보안 등)를 요구사항과 매핑하여 기술 적합성 입증. 향후 3년간 시스템 확장성 200% 보장 및 운영 비용 30% 절감 시나리오 제시."
        },
        "prioritized_actions": actions[:10],
        "roadmap": {
            "phase_0_prebid": [
                {
                    "task": "레퍼런스 큐레이션 및 검증 (담당: Sales 3명/PM 1명, 2주, Week 1~2)",
                    "related_actions": [a["id"] for a in actions[:3]],
                    "dependencies": [],
                    "parallel_tasks": ["보안 인증 점검", "파트너사 선정"],
                    "resources": "Sales 3명 (full-time) + PM 1명 (full-time)",
                    "milestones": "Week 1: 후보 레퍼런스 10건 리스트업, Week 2: 최종 5~7건 확정 및 검증 완료",
                    "expected_outcome": "유사 프로젝트 레퍼런스 5~7건 확보 → 고객 신뢰도 40% 향상 → IR 자료 완성도 95% 달성 → 초기 평가 통과율 85%"
                },
                {"task": "고객 요구사항 상세 매핑 워크샵 (담당: Tech Lead 2명, 1주, Week 1)", "related_actions": [a["id"] for a in actions[:2]], "dependencies": [], "parallel_tasks": ["레퍼런스 큐레이션"], "resources": "Tech Lead 2명 + BA 1명", "milestones": "Week 1: 요구사항 매핑 100% 완료", "expected_outcome": "요구사항 100% 매핑 완료 → 기술 적합도 점수 산출 → 갭 영역 3~5개 식별 → 보완 전략 수립"},
                {"task": "보안/인증 선제 점검 및 대응 (담당: Security 2명, 1주, Week 1~2)", "related_actions": [], "dependencies": [], "parallel_tasks": ["레퍼런스 큐레이션", "요구사항 매핑"], "resources": "Security Specialist 2명 (50%)", "milestones": "Week 2: ISMS-P 체크리스트 100% 완료", "expected_outcome": "ISMS-P 체크리스트 100% 대비 → 필수 인증 3종 사전 확보 → 보안 리스크 35% 감소"},
                {"task": "파트너사 선정 및 협업 체계 구축 (담당: Partnership 1명, 1주, Week 2)", "related_actions": [a["id"] for a in actions if 'Partnership' in str(a.get('strategy_approach', ''))], "dependencies": ["요구사항 매핑 완료"], "parallel_tasks": ["보안 인증 점검"], "resources": "Partnership Manager 1명", "milestones": "Week 2: 파트너 1곳 선정 및 NDA 체결", "expected_outcome": "검증된 파트너사 3곳 평가 → 최적 1곳 선정 및 NDA 체결 → 공동 제안 체계 확립"}
            ],
            "phase_1_poc": [
                {"task": "핵심 요구사항 2~3개 축소 범위 PoC 설계 (담당: Solution Architect 2명, 1주, Week 3)", "related_actions": [a["id"] for a in actions[:5]], "dependencies": ["요구사항 매핑 완료", "레퍼런스 분석 완료"], "parallel_tasks": [], "resources": "Solution Architect 2명 + Tech Lead 1명", "milestones": "Week 3: PoC 설계 문서 완성, 성공 기준 10개 정의", "expected_outcome": "PoC 범위 명확화 → 테스트 시나리오 5종 설계 → 성공 기준 10개 정의 → 일정 및 리소스 계획 수립"},
                {"task": "PoC 환경 구축 및 검증 수행 (담당: Tech 5명, 4주, Week 4~7)", "related_actions": [a["id"] for a in actions], "dependencies": ["PoC 설계 완료"], "parallel_tasks": [], "resources": "Tech Lead 1명 + 개발자 4명 (full-time)", "milestones": "Week 5: 환경 구축 완료, Week 6: 중간 점검 (성공률 70% 이상), Week 7: PoC 최종 검증", "expected_outcome": "파일럿 환경 2주 내 구축 → 실제 데이터 기반 검증 2주 수행 → PoC 성공률 90% 달성 → 성능 25% 개선 입증"},
                {"task": "PoC 결과 분석 및 보고서 작성 (담당: PM/Tech Lead, 1주, Week 8)", "related_actions": [], "dependencies": ["PoC 완료"], "parallel_tasks": ["레퍼런스 확보"], "resources": "PM 1명 + Tech Lead 1명 + Data Analyst 1명", "milestones": "Week 8: 분석 보고서 완성", "expected_outcome": "정량적 성능 지표 15개 도출 → Before/After 비교 분석 → 경쟁사 대비 우위 3가지 입증 → 고객 검증 보고서 작성"},
                {"task": "신규 레퍼런스 확보 및 검증 (담당: Sales 2명, 1주, Week 8)", "related_actions": [a["id"] for a in actions[:3]], "dependencies": ["PoC 완료"], "parallel_tasks": ["결과 분석"], "resources": "Sales 2명", "milestones": "Week 8: 레퍼런스 3건 이상 확보", "expected_outcome": "PoC 결과 기반 레퍼런스 3건 확보 → 고객 추천서 획득 → 기술 검증 완료 인증서 확보"},
                {"task": "KPI 측정 체계 확립 및 모니터링 (담당: PMO, 1주, Week 8)", "related_actions": [], "dependencies": ["PoC 완료"], "parallel_tasks": [], "resources": "PMO 1명 + Data Engineer 1명", "milestones": "Week 8: KPI 대시보드 가동", "expected_outcome": "핵심 KPI 12개 정의 → 측정 도구 및 대시보드 구축 → 주간 모니터링 체계 확립 → 목표 대비 진척률 95% 이상"}
            ],
            "phase_2_proposal": [
                {"task": "차별화 포인트 도식화 및 증빙 자료 작성 (담당: Proposal 3명, 1주, Week 9~10)", "related_actions": [a["id"] for a in actions[:4]], "dependencies": ["PoC 완료", "레퍼런스 확보"], "parallel_tasks": ["비용 시나리오 작성"], "resources": "Proposal Writer 2명 + Designer 1명", "milestones": "Week 10: 증빙 자료 20종 완성", "expected_outcome": "차별화 요소 5가지 명확화 → 증빙 자료 20종 준비 → 평가표 항목별 매핑 → 차별화 점수 85점 이상 확보"},
                {"task": "비용 및 일정 최적화 시나리오 작성 (담당: PM/Finance, 4일, Week 9)", "related_actions": [], "dependencies": ["PoC 완료"], "parallel_tasks": ["차별화 포인트 작성"], "resources": "PM 1명 + Finance 1명", "milestones": "Week 9: TCO 분석 완료", "expected_outcome": "TCO 분석 완료 → 경쟁사 대비 10~15% 절감안 제시 → 일정 단축 2가지 옵션 제시 → ROI 분석 포함"},
                {"task": "기술 제안서 작성 및 검토 (담당: Tech Writer 2명, 1주, Week 10~11)", "related_actions": [a["id"] for a in actions], "dependencies": ["차별화 포인트 완성", "증빙 자료 준비"], "parallel_tasks": [], "resources": "Tech Writer 2명 + Reviewer 2명", "milestones": "Week 11: 기술 섹션 완성, 내부 검토 3회 완료", "expected_outcome": "기술 섹션 완성도 95% → 레퍼런스 및 증빙 자료 통합 → 평가 항목 100% 대응 → 내부 검토 3회 완료"},
                {"task": "리스크 관리 계획 및 대응 방안 수립 (담당: PMO, 3일, Week 11)", "related_actions": [], "dependencies": ["기술 제안서 초안 완성"], "parallel_tasks": ["프레젠테이션 준비"], "resources": "PMO 1명 + Risk Manager 1명", "milestones": "Week 11: 리스크 매트릭스 완성", "expected_outcome": "식별된 리스크 8~10개 → 각 리스크별 Plan A/B 수립 → 리스크 매트릭스 작성 → 예비 대응 자원 확보"},
                {"task": "최종 제안서 통합 및 프레젠테이션 준비 (담당: All, 3일, Week 11~12)", "related_actions": [], "dependencies": ["모든 섹션 완성"], "parallel_tasks": [], "resources": "전체 팀원 (리뷰 및 리허설)", "milestones": "Week 12: 제안서 최종본 완성, 리허설 2회 완료", "expected_outcome": "제안서 최종 완성 → 발표 자료 30p 작성 → 예상 질의응답 20개 준비 → 최종 리허설 2회 완료"}
            ]
        },
        "risks": [
            {
                "id": "R1",
                "risk": "보안 인증 지연으로 PoC 일정 2주 지연 → 제안서 제출 기한 촉박 → 완성도 80% 미만 → 기술 평가 15점 감점",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Plan A (예방): 1) 필수 인증 3종 사전 확보 (Week -4 착수) → 2) 보안 전담 인력 2명 배치 → 3) 외부 인증 컨설턴트 on-call 계약 → 4) 주간 점검 회의 (매주 금요일) → 5) 긴급 대응 프로세스 수립 (24시간 내 대응)",
                "plan_b": "Plan B (대안): 인증 지연 시 → 1) 인증 면제 가능 항목으로 PoC 범위 조정 (70%로 축소) → 2) 사후 인증 계획 제시 (수주 후 3개월 내) → 3) 외부 보안 전문가 리뷰 의견서 첨부로 신뢰도 확보 → 4) 일정 1주 단축 (병행 작업 증가) → 5) 제안서 기술 섹션 우선 완성",
                "trigger_condition": "Week 6 점검 시 인증 진행률 70% 미만인 경우 Plan B 즉시 발동",
                "mitigation_action_ids": []
            },
            {
                "id": "R2",
                "risk": "PoC 범위 과대로 성공 기준 미달 (달성률 50% 이하) → 기술 평가 20점 감점 → 제안 탈락 가능성 60%",
                "likelihood": "medium",
                "impact": "high",
                "mitigation": "Plan A (예방): 1) 핵심 기능 2~3개로 범위 명확 제한 (고객 합의) → 2) 성공 기준 사전 합의 (Week 0) → 3) 주간 진척률 모니터링 (목표 대비 90% 이상) → 4) 중간 점검 2회 (Week 2, 4) → 5) 범위 조정 권한 PM 위임",
                "plan_b": "Plan B (대안): PoC 중간 점검 실패 시 → 1) 성공 가능한 핵심 1개 기능으로 즉시 축소 → 2) 나머지 기능은 시뮬레이션 데모로 대체 → 3) 성공률 80% 이상 보장 → 4) 미완료 기능은 수주 후 추가 검증 계획 제시 → 5) 일정 영향 1주 이내",
                "trigger_condition": "Week 4 중간 점검 시 PoC 성공률 70% 미만",
                "mitigation_action_ids": []
            },
            {
                "id": "R3",
                "risk": "핵심 기술 인력 이탈 (2명 이상) → PoC 품질 저하 (완성도 70% 미만) → 기술 검증 실패 → 신뢰도 40% 하락",
                "likelihood": "low",
                "impact": "high",
                "mitigation": "Plan A (예방): 1) 백업 인력 3명 사전 지정 및 교육 (Week -2) → 2) 지식 이관 문서화 (주 1회 업데이트) → 3) 페어 프로그래밍 의무화 → 4) 외부 전문가 풀 5명 확보 → 5) 인센티브 제도 (성공 시 +20%)",
                "plan_b": "Plan B (대안): 인력 이탈 발생 시 → 1) 백업 인력 즉시 투입 (24시간 내) → 2) 외부 전문가 긴급 투입 (3일 내) → 3) PoC 범위 70%로 축소 → 4) 일정 1주 연장 협의 → 5) 품질 검증 기준 조정 (필수 80%, 권장 50%)",
                "trigger_condition": "핵심 인력 1명 이상 이탈 의사 표명 시 즉시",
                "mitigation_action_ids": []
            },
            {
                "id": "R4",
                "risk": "경쟁사 가격 덤핑 (당사 대비 20% 이상 저가) → 가격 경쟁력 상실 → 가격 평가 0점 → 종합 평가 탈락",
                "likelihood": "medium",
                "impact": "medium",
                "mitigation": "Plan A (예방): 1) TCO 기반 비용 분석 사전 준비 → 2) 3년간 총소유비용 15% 절감 입증 → 3) 성능/품질 가치 35% 우수 강조 → 4) 계약 조건 2안 (초기 할인 or 장기 할인) → 5) 파트너십 혜택 제안",
                "plan_b": "Plan B (대안): 가격 경쟁 심화 시 → 1) 견적 10% 추가 조정 (최소 마진 유지선) → 2) 무상 PoC 확대 제공 (2개월 → 3개월) → 3) 추가 기술 지원 1년 무상 제공 → 4) 성능 보장 SLA 추가 (미달 시 페널티) → 5) 장기 계약 조건 시 15% 추가 할인",
                "trigger_condition": "경쟁사 견적이 당사 대비 15% 이상 저가인 것으로 파악될 경우",
                "mitigation_action_ids": []
            },
            {
                "id": "R5",
                "risk": "고객 요구사항 변경 (30% 이상) → 제안 내용 대폭 수정 (재작업 40%) → 일정 3주 지연 → 완성도 저하",
                "likelihood": "low",
                "impact": "medium",
                "mitigation": "Plan A (예방): 1) 요구사항 동결 시점 명확 합의 (Week 0) → 2) 변경 관리 프로세스 (영향도 평가) → 3) 예비 버퍼 2주 확보 → 4) 모듈화 설계로 변경 영향 최소화 → 5) 주간 고객 리뷰 미팅",
                "plan_b": "Plan B (대안): 요구사항 변경 시 → 1) 변경 영향도 즉시 분석 (24시간 내) → 2) 핵심 변경만 반영, 부차적 변경은 Phase 2로 연기 → 3) 추가 리소스 투입 (인력 +2명, 1주) → 4) 고객과 우선순위 재협의 → 5) 일정 영향 1주 이내로 제한",
                "trigger_condition": "요구사항 변경률이 20% 이상으로 파악될 경우",
                "mitigation_action_ids": []
            }
        ],
        "kpis": [
            {"name": "PoC 성공 기준 달성률", "target": "90% 이상, 2025년 12월까지", "baseline": "과거 PoC 평균 75% (최근 3개 프로젝트 기준)", "measurement_method": "사전 정의된 성공 기준 10개 항목 중 9개 이상 달성 여부 측정", "related_actions": [a["id"] for a in actions[:5]]},
            {"name": "제안서 기술 평가 점수", "target": "85점 이상 (100점 만점), 경쟁사 대비 상위 10%", "baseline": "전년도 평균 72점, 경쟁사 평균 76점", "measurement_method": "RFP 평가표 기술 항목 점수 합산 (가중치 반영)", "related_actions": [a["id"] for a in actions[:3]]},
            {"name": "시스템 처리 성능 (TPS)", "target": "2,600 TPS (현재 대비 30% 개선), 2025년 12월", "baseline": "현재 2,000 TPS (JMeter 부하 테스트), 경쟁사 평균 2,200 TPS", "measurement_method": "Apache JMeter 부하 테스트, 동시 사용자 1,000명 기준, p95 응답시간 측정", "related_actions": [a["id"] for a in actions[:4]]},
            {"name": "API 응답 속도", "target": "0.5초 이하 (58% 개선), p95 기준", "baseline": "현재 1.2초 (p95), 경쟁사 평균 0.8초, 업계 표준 0.6초", "measurement_method": "Prometheus + Grafana 모니터링, 7일 연속 측정 후 p95 값 산출", "related_actions": [a["id"] for a in actions[:3]]},
            {"name": "레퍼런스 확보 건수", "target": "8건 이상 (유사 프로젝트 5건 + 신규 PoC 3건)", "baseline": "현재 4건 (검증 완료된 프로젝트)", "measurement_method": "고객 추천서 또는 검증 완료 인증서 보유 기준", "related_actions": [a["id"] for a in actions[:4]]},
            {"name": "프로젝트 일정 준수율", "target": "95% 이상 (주요 마일스톤 15개 중 14개 이상 준수)", "baseline": "과거 평균 82% (최근 5개 프로젝트)", "measurement_method": "주요 마일스톤 15개 각각의 목표 날짜 대비 실제 완료 날짜 비교, ±3일 이내 준수로 판정", "related_actions": [a["id"] for a in actions]},
            {"name": "비용 효율성 (TCO)", "target": "경쟁사 대비 TCO 10~15% 절감", "baseline": "경쟁사 평균 견적 기준 (3년간 총 비용)", "measurement_method": "초기 투자 비용 + 3년간 운영 비용 + 유지보수 비용 합산 후 경쟁사와 비교", "related_actions": [a["id"] for a in actions[:2]]},
            {"name": "고객 만족도", "target": "4.5점 이상 (5점 만점), PoC 종료 시점 측정", "baseline": "과거 평균 3.8점 (최근 3개 프로젝트)", "measurement_method": "PoC 종료 시 고객 설문조사 10개 항목 (5점 척도), 평균 산출", "related_actions": [a["id"] for a in actions]},
            {"name": "기술 리스크 감소율", "target": "35% 이상 감소 (초기 리스크 평가 대비)", "baseline": "초기 평가 high risk 10개, medium risk 8개", "measurement_method": "리스크 매트릭스 기반 (likelihood × impact 점수 합산), 사전/사후 비교", "related_actions": [a["id"] for a in actions]},
            {"name": "차별화 요소 확보", "target": "경쟁사 대비 5가지 이상 명확한 차별화 포인트", "baseline": "현재 2가지 (레퍼런스, 가격)", "measurement_method": "차별화 체크리스트 10개 항목 중 경쟁사와 명확히 구별되는 항목 수", "related_actions": [a["id"] for a in actions[:4]]},
            {"name": "제안 경쟁력 지수", "target": "65점 이상 (자체 평가 기준 100점 만점)", "baseline": "현재 35점 (기술 15 + 가격 10 + 레퍼런스 5 + 신뢰도 5)", "measurement_method": "기술(30) + 가격(25) + 레퍼런스(20) + 신뢰도(15) + 차별화(10) 가중 합산", "related_actions": [a["id"] for a in actions]},
            {"name": "파트너 협업 효율성", "target": "공동 작업 일정 준수율 90% 이상", "baseline": "과거 평균 70% (파트너 프로젝트 3건 평균)", "measurement_method": "공동 마일스톤 10개 중 준수 개수 (±3일 기준)", "related_actions": [a["id"] for a in actions if 'Partnership' in str(a.get('strategy_approach', ''))]},
            {"name": "수주 확률 향상", "target": "35%에서 60%로 증가 (71% 향상)", "baseline": "현재 35% (유사 RFP 5건 평균 수주율)", "measurement_method": "제안 경쟁력 지수 기반 확률 모델 (과거 데이터 회귀 분석)", "related_actions": [a["id"] for a in actions]}
        ],
        "differentiation": [
            "검증된 유사 프로젝트 레퍼런스 8건 보유 (경쟁사 평균 4건 대비 2배)",
            "고객 맞춤형 PoC 제공으로 요구사항 부합도 90% 이상 (경쟁사 평균 65%)",
            "의사결정 속도 2배 빠름 (평균 응답시간 24시간 이내, 경쟁사 48시간)",
            "TCO 기준 10~15% 비용 절감 (3년간 총소유비용 분석)",
            "성능 25% 우수 (실제 PoC 데이터 기반 입증)",
            "전문 파트너사 협업 체계 확립 (검증된 파트너 3곳 보유)",
            "유연한 계약 조건 2가지 옵션 제공 (초기 투자 최소화 또는 장기 할인)",
            "6개월 내 핵심 KPI 12개 달성 보장 (SLA 계약 포함)"
        ],
        "appendix": {
            "requirement_groups": [{"category": k, "items": v} for k, v in groups.items()],
            "fit_table": fit_rows,
            "competitor_counters": competitor_counters
        }
    }

    # 리스크-액션 매핑 보정 (구체적 연결)
    for r in strategy["risks"]:
        if r["id"] == "R1":
            # 보안 관련 액션 찾기
            security_actions = [a["id"] for a in actions if ("보안" in a["action"] or "인증" in a["action"] or "ISMS" in a.get("how", ""))]
            r["mitigation_action_ids"] = security_actions if security_actions else [actions[0]["id"]]
        elif r["id"] == "R2":
            # PoC 관련 액션 찾기
            poc_actions = [a["id"] for a in actions if ("PoC" in a["action"] or "검증" in a["action"])]
            r["mitigation_action_ids"] = poc_actions if poc_actions else [a["id"] for a in actions[:2]]
        elif r["id"] == "R3":
            # 인력 관련 액션 찾기 (파트너십 또는 고 effort)
            hr_actions = [a["id"] for a in actions if (a.get("strategy_approach") == "Partnership" or a.get("effort") == "high")]
            r["mitigation_action_ids"] = hr_actions if hr_actions else [a["id"] for a in actions[:2]]
        elif r["id"] == "R4":
            # 비용 관련 액션 찾기
            cost_actions = [a["id"] for a in actions if (a.get("strategy_approach") == "Differentiation")]
            r["mitigation_action_ids"] = cost_actions if cost_actions else [a["id"] for a in actions[:3]]
        elif r["id"] == "R5":
            # 범위 관리 관련 액션 찾기
            scope_actions = [a["id"] for a in actions if ("요구사항" in a.get("why", "") or a.get("impact") == "high")]
            r["mitigation_action_ids"] = scope_actions if scope_actions else [a["id"] for a in actions[:2]]

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
            result_text = call_llm(prompt, temperature=temperature)
            if result_text:
                strategy_data = parse_json_response(result_text)
                if isinstance(strategy_data, dict):
                    print("[전략 합성 v3.1] ✅ AI 분석 완료")
                    deal_brief = _generate_deal_brief(strategy_data)
                    return {"strategy": strategy_data, "deal_brief": deal_brief}
                else:
                    print("[전략 합성 v3.1] ⚠️ JSON 파싱 실패 → 폴백")
            else:
                print("[전략 합성 v3.1] ⚠️ LLM 응답 없음 → 폴백")
        else:
            print("[전략 합성 v3.1] ⚠️ LLM 미가용 → 폴백")

        # 폴백 생성
        fb = _fallback_strategy(norm_requirements, internal_matches, competitor_profiles)
        return {"strategy": fb, "deal_brief": _generate_deal_brief(fb)}

    except Exception as e:
        print(f"[전략 합성 v3.1] ❌ 예외 발생: {e}")
        fb = _fallback_strategy(norm_requirements, internal_matches, competitor_profiles)
        return {"strategy": fb, "deal_brief": _generate_deal_brief(fb)}


# ======================
# Alias for backward compatibility
# ======================
strategy_synthesizer_v3 = strategy_synthesizer


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

    print("\n🎯 전략 합성 v3.1 결과(JSON):")
    print(json.dumps(result, ensure_ascii=False, indent=2))
strategy_synthesizer_v2 = strategy_synthesizer_v3
