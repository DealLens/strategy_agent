"""
main_mode.py
DealLens 실행 모드 라우터
"""

from typing import Optional, List

def _anonymize_company_name(company_name: str) -> str:
    """회사명을 익명화합니다."""
    company_mapping = {
        "삼성 SDS": "S사",
        "삼성SDS": "S사", 
        "LG CNS": "L사",
        "현대오토에버": "H사",
        "KT": "K사",
        "CJ올리브네트웍스": "C사",
        "CJ 올리브네트웍스": "C사",
        "SK C&C": "자사",
        "LG유플러스": "U사",
        "네이버클라우드": "N사",
        "카카오엔터프라이즈": "K사",
        "카카오": "K사",
        "포스코DX": "P사",
        "NHN": "N사"
    }
    
    return company_mapping.get(company_name, company_name)


def run_mode(mode: str, topic: str, companies: Optional[List[str]] = None, enable_rag: bool = True) -> str:
    """
    선택된 모드에 따라 해당 분석 에이전트를 실행합니다.

    Args:
        mode (str): 실행 모드
        topic (str): 분석 주제
        companies (List[str]): 경쟁사 목록
        enable_rag (bool): RAG 사용 여부

    Returns:
        str: 분석 결과 텍스트
    """

    if mode == "전체 파이프라인":
        # Supervisor를 통한 전체 파이프라인 실행
        try:
            from workflow.supervisor import supervisor
            
            user_input = f"다음 RFP를 분석해주세요: {topic}"
            if companies:
                user_input += f"\n경쟁사 분석 대상: {', '.join(companies)}"
            
            result = supervisor.invoke({"input": user_input})
            return result.get("output", "분석이 완료되었습니다.")
            
        except Exception as e:
            return f"❌ 파이프라인 실행 중 오류가 발생했습니다: {str(e)}"

    elif mode == "경쟁사 분석":
        try:
            from workflow.agents.competitor_analysis import competitor_analysis
            
            result = competitor_analysis.invoke({
                "companies": companies or ["삼성 SDS", "LG CNS", "현대오토에버"],
                "update_data": False  # 데이터 업데이트는 선택사항
            })
            
            profiles = result.get("competitor_profiles", {})
            
            # 결과 포맷팅
            output = "# 🏢 경쟁사 분석 결과\n\n"
            for company, profile in profiles.items():
                anonymized_company = _anonymize_company_name(company)
                output += f"## {anonymized_company}\n\n"
                output += f"**종합 서머리:** {profile.get('company_summary', '분석 중')}\n\n"
                output += f"**핵심 기술:** {', '.join(profile.get('key_technologies', []))}\n\n"
                output += f"**차별화 포인트:** {', '.join(profile.get('differentiation_points', []))}\n\n"
                
                # SWOT 분석
                swot = profile.get('swot', {})
                output += "**SWOT 분석:**\n"
                output += f"- 강점: {', '.join(swot.get('S', []))}\n"
                output += f"- 약점: {', '.join(swot.get('W', []))}\n"
                output += f"- 기회: {', '.join(swot.get('O', []))}\n"
                output += f"- 위협: {', '.join(swot.get('T', []))}\n\n"
                
                output += "---\n\n"
            
            return output
            
        except Exception as e:
            return f"❌ 경쟁사 분석 중 오류가 발생했습니다: {str(e)}"

    else:
        return f"❌ 지원하지 않는 모드입니다: {mode}"

