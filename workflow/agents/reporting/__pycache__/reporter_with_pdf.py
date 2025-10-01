import os
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm

# ✅ 한글 폰트 등록 (윈도우 기준 맑은 고딕)
# 맥이라면 /System/Library/Fonts/Supplemental/AppleGothic.ttf 같은 경로 확인 필요
try:
    pdfmetrics.registerFont(TTFont("MalgunGothic", "C:/Windows/Fonts/malgun.ttf"))
except:
    # fallback: 기본 폰트 (한글이 깨질 수 있음)
    print("⚠️ 한글 폰트(Malgun Gothic) 등록 실패. 폰트 경로를 확인하세요.")


def _format_list(items: List[str], prefix: str = "- ") -> str:
    """리스트를 텍스트 목록으로 변환"""
    if not items:
        return f"{prefix}해당 없음"
    return "\n".join(f"{prefix}{item}" for item in items)


def _format_competitors(competitors: Dict[str, Any]) -> str:
    """경쟁사 SWOT 분석 텍스트로 변환"""
    if not competitors:
        return "- 경쟁사 분석 없음"
    lines = []
    for name, profile in competitors.items():
        swot = profile.get("swot", {})
        lines.append(f"🏢 {name}")
        lines.append(f"  - 강점(S): {swot.get('S', 'N/A')}")
        lines.append(f"  - 약점(W): {swot.get('W', 'N/A')}")
        lines.append(f"  - 기회(O): {swot.get('O', 'N/A')}")
        lines.append(f"  - 위협(T): {swot.get('T', 'N/A')}")
        lines.append("")
    return "\n".join(lines)


@tool
def reporter_with_pdf(data: Optional[Dict[str, Any]] = None,
                      output_path: str = "reports/strategy_report.pdf") -> dict:
    """
    최종 전략 보고서를 PDF 파일로 저장합니다.

    Args:
        data (dict, optional): Supervisor가 모은 결과
        output_path (str): 저장할 PDF 파일 경로

    Returns:
        dict: {
            "deal_brief": str,
            "full_report": str,
            "pdf_path": str
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

    # Deal Brief
    deal_brief = f"""
📋 Deal Brief
- 요구사항: {len(requirements)}개
- 평가 기준: {len(evaluation)}개
- 리스크 후보: {len(risks)}개
- 내부 매칭: {len(internal_matches)}개
- 경쟁사 분석: {len(competitors)}개
- 전략 액션: {len(strategy.get('actions', []))}개
""".strip()

    # Full Report (Plain Text)
    full_report = f"""
📑 전략 보고서

📌 요구사항 및 평가 기준
요구사항:
{_format_list(requirements)}

평가기준:
{_format_list(evaluation)}

⚠️ 리스크
{_format_list(risks)}

🔍 내부 역량 매칭
{_format_list([str(m) for m in internal_matches])}

🏢 경쟁사 분석
{_format_competitors(competitors)}

🎯 제안 전략
- 핵심 전략:
{_format_list(strategy.get("actions", []))}
- SWOT: {strategy.get("swot", {})}

✅ 결론
이번 RFP에 대한 대응 전략은 내부 역량과 경쟁사 분석을 종합하여,
차별화된 기술 제안과 효율적인 비용 구조를 강조하는 방향으로 설정되었습니다.
""".strip()

    # PDF 저장 경로 확인 (reports 폴더 자동 생성)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # ✅ 스타일 정의 (맑은 고딕 적용)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='KoreanTitle', fontName='MalgunGothic',
                              fontSize=16, leading=22, spaceAfter=14))
    styles.add(ParagraphStyle(name='KoreanHeading', fontName='MalgunGothic',
                              fontSize=12, leading=18, spaceAfter=10))
    styles.add(ParagraphStyle(name='KoreanBody', fontName='MalgunGothic',
                              fontSize=11, leading=16, spaceAfter=6))

    # ✅ PDF 문서 객체 생성
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    story = []

    # 표지
    story.append(Spacer(1, 200))
    story.append(Paragraph("📑 전략 제안 보고서", styles['KoreanTitle']))
    story.append(Spacer(1, 40))
    story.append(Paragraph("제출처: ○○기관", styles['KoreanBody']))
    story.append(Paragraph("작성일: 2025-09-30", styles['KoreanBody']))
    story.append(PageBreak())

    # Deal Brief
    story.append(Paragraph("📋 Deal Brief", styles['KoreanHeading']))
    story.append(Paragraph(deal_brief.replace("\n", "<br/>"), styles['KoreanBody']))
    story.append(Spacer(1, 20))

    # Full Report 본문
    story.append(Paragraph("📑 상세 전략 보고서", styles['KoreanHeading']))
    for section in full_report.split("\n\n"):
        if section.strip():
            story.append(Paragraph(section.replace("\n", "<br/>"), styles['KoreanBody']))
            story.append(Spacer(1, 12))

    # PDF 빌드
    doc.build(story)

    return {
        "deal_brief": deal_brief.strip(),
        "full_report": full_report.strip(),
        "pdf_path": os.path.abspath(output_path)
    }


# ===== 디버깅 실행 =====
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

    result = reporter_with_pdf.run(dummy_data)
    print("📋 Deal Brief:\n", result["deal_brief"])
    print("\nPDF 저장 경로:", result["pdf_path"])
