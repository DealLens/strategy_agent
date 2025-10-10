import os
import sys
import asyncio
from pathlib import Path
from langchain_core.tools import tool
from retrivers.rfp_retriever import build_rfp_retriever

# ======================
# 통합 LLM 클라이언트 사용
# ======================
# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.llm_client import (
    get_llm_client,
    is_llm_available,
    call_llm,
    parse_list_response,
    filter_content,
)

llm_client = get_llm_client()


# ======================
# 유틸 함수
# ======================
async def _fetch_docs(retriever, query: str, limit: int = 5):
    try:
        docs = await asyncio.to_thread(retriever.get_relevant_documents, query)
        return [d.page_content for d in docs[:limit]]
    except Exception as e:
        return [f"❌ 오류({query}): {str(e)}"]


def _filter_requirements(requirements: list) -> list:
    """불필요한 요구사항 제거"""
    filtered = []
    for req in requirements:
        if any(kw in req for kw in ["목차", "첨부", "서약서", "조견표", "제안서 작성", "기재사항", "제출"]):
            continue
        if len(req) < 6:  # 너무 짧은 줄 제거
            continue
        filtered.append(req)
    return filtered


def _generate_comparison_table(raw_docs: list) -> dict:
    """조견표를 구조화된 형식으로 생성"""
    if not is_llm_available() or not raw_docs:
        return {"error": "LLM 없음 또는 문서 없음"}
    
    try:
        print("[RFP Parser] 📋 조견표 생성 중...")

        combined_text = "\n---\n".join([doc[:1000] for doc in raw_docs[:15]])
        if len(combined_text) > 8000:
            combined_text = combined_text[:8000] + "\n... (이하 생략)"

        prompt = f"""당신은 RFP 분석 전문가입니다. 다음 RFP 문서에서 조견표를 생성해주세요.

=== RFP 문서 내용 ===
{combined_text}

=== 조견표 형식 ===
대분류 | 중분류 | 소분류 | 위치(Page) | 내용유무 | 내용요약 | 비고
"""

        print("\n[RFP Parser] === 조견표 프롬프트 ===")
        print(prompt[:600] + " ...")

        result_text = call_llm(prompt, temperature=0.3, max_tokens=2000)

        print("[RFP Parser] === 조견표 응답 ===")
        print(result_text)

        if not result_text:
            return {"error": "LLM 호출 실패"}

        table_data = []
        lines = result_text.split("\n")
        for line in lines:
            line = line.strip()
            if "|" in line and not line.startswith("대분류") and not line.startswith("---"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 7:
                    table_data.append({
                        "대분류": parts[0],
                        "중분류": parts[1],
                        "소분류": parts[2],
                        "위치": parts[3],
                        "내용유무": parts[4],
                        "내용요약": parts[5],
                        "비고": parts[6]
                    })

        if table_data:
            print(f"[RFP Parser] ✅ 조견표 생성 완료 - {len(table_data)}개 항목")
            return {"table": table_data, "raw_text": result_text, "count": len(table_data)}
        else:
            print(f"[RFP Parser] ⚠️ 조견표 파싱 실패 - 원본 텍스트 반환")
            return {"table": [], "raw_text": result_text, "count": 0}

    except Exception as e:
        print(f"[RFP Parser] ❌ 조견표 생성 실패: {e}")
        return {"error": str(e)}


def _summarize_with_ai(raw_results: dict) -> dict:
    """AI로 RFP 결과 요약"""
    if not is_llm_available():
        print("[RFP Parser] ⚠️ LLM 없음 - fallback 적용")
        return _apply_smart_fallback(raw_results)
    
    summarized = {}
    for category, items in raw_results.items():
        if not items or "error" in str(items):
            summarized[category] = items
            continue

        combined_items = [item[:500] for item in items[:10]]
        combined_text = "\n---\n".join(combined_items)
        if len(combined_text) > 4000:
            combined_text = combined_text[:4000] + "\n... (이하 생략)"

        # 프롬프트 정의
        prompts = {
            "requirements": f"""다음 문서에서 핵심 요구사항만 5-10개 추출하세요.
- 행정적/형식적 항목(제출, 목차, 첨부, 서약서 등)은 제외
- 기술/운영/보안/개발 언어/환경 관련 요구사항만 남기세요

=== 내용 ===
{combined_text}""",

            "evaluation": f"""다음 문서에서 평가 기준과 배점을 5-10개 추출하세요.

=== 내용 ===
{combined_text}""",

            "risks": f"""다음 문서에서 리스크 요소를 3-5개 추출하세요.

=== 내용 ===
{combined_text}""",

            "table_of_contents": f"""다음 문서에서 목차 구조를 추출하세요.

=== 내용 ===
{combined_text}"""
        }

        if category not in prompts:
            summarized[category] = filter_content(items[:5], category)
            continue

        prompt = prompts[category]

        try:
            print(f"\n[RFP Parser] === {category.upper()} 프롬프트 ===")
            print(prompt[:600] + " ...")

            result_text = call_llm(prompt, temperature=0.3, max_tokens=1000)

            print(f"[RFP Parser] === {category.upper()} 응답 ===")
            print(result_text)

            if result_text:
                lines = parse_list_response(result_text, category)
                if category == "requirements":
                    lines = _filter_requirements(lines)
                lines = filter_content(lines, category)
                summarized[category] = lines
                print(f"[RFP Parser] ✅ {category} 요약 완료 - {len(lines)}개")
            else:
                summarized[category] = _apply_smart_fallback_single(items, category)
                print(f"[RFP Parser] ⚠️ {category} LLM 실패 - fallback 적용")
                
        except Exception as e:
            print(f"[RFP Parser] ❌ {category} AI 호출 실패: {e}")
            summarized[category] = _apply_smart_fallback_single(items, category)

    return summarized


def _apply_smart_fallback(raw_results: dict) -> dict:
    return {category: _apply_smart_fallback_single(items, category) 
            for category, items in raw_results.items()}


def _apply_smart_fallback_single(items: list, category: str) -> list:
    if not items:
        return []
    
    filtered_items = []
    for item in items[:10]:
        item_str = str(item)[:300]
        if any(keyword in item_str.lower() for keyword in 
               ["요구", "기능", "기술", "보안", "개발", "시스템", "서비스", "데이터", 
                "ai", "클라우드", "평가", "배점", "리스크"]):
            filtered_items.append(item_str)
    
    return filtered_items[:5]


# ======================
# Tool 정의
# ======================
@tool
def rfp_parser(pdf_path: str) -> dict:
    """
    RFP PDF를 분석하여 요구사항, 평가기준, 리스크, 조견표, 목차를 추출합니다.
    """
    print(f"\n[RFP Parser] PDF 분석 시작: {pdf_path}")
    
    try:
        retriever = build_rfp_retriever(pdf_path)
    except Exception as e:
        return {"error": f"retriever 생성 실패: {str(e)}"}

    async def run_queries():
        queries = {
            "requirements": "요구사항 OR 기술 OR 개발 OR 보안",
            "evaluation": "평가기준 OR 평가배점 OR 기술평가 OR 가격평가",
            "risks": "리스크 OR 위험 OR 문제점",
            "comparison_table": "조견표 OR 제안개요 OR 제안범위",
            "table_of_contents": "목차 OR 차례 OR 구성",
        }
        tasks = {k: _fetch_docs(retriever, v, limit=10) for k, v in queries.items()}
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))

    try:
        raw_results = asyncio.run(run_queries())
        summarized = _summarize_with_ai(raw_results)

        if raw_results.get("comparison_table"):
            comparison_table = _generate_comparison_table(raw_results["comparison_table"])
            summarized["comparison_table"] = comparison_table

        print("[RFP Parser] ✅ 전체 분석 완료")
        return summarized
    except Exception as e:
        return {"error": f"검색/요약 실패: {str(e)}"}
