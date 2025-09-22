"""
RFP Parser Agent
RFP 문서에서 요구사항, 평가기준, 일정 등을 자동 추출
"""

from langchain.tools import tool
from typing import List, Dict, Any
import json
import re
import pdfplumber
import os
from datetime import datetime


@tool
def parse_rfp_document(rfp_content: str) -> str:
    """
    RFP 문서를 분석하여 요구사항, 평가기준, 일정 등을 추출합니다.
    
    Args:
        rfp_content: RFP 문서 내용 (텍스트)
    
    Returns:
        JSON 형태의 구조화된 RFP 분석 결과
    """
    # 고급 NLP 파싱을 위한 정규식 패턴들
    requirements = []
    evaluation_criteria = []
    timeline = []
    budget_info = []
    technical_specs = []
    compliance_requirements = []
    
    # 요구사항 추출 (더 정교한 패턴 매칭)
    req_patterns = [
        r'요구사항[:\s]*([^\.]+)',
        r'필수사항[:\s]*([^\.]+)',
        r'기능\s*요구사항[:\s]*([^\.]+)',
        r'성능\s*요구사항[:\s]*([^\.]+)',
        r'보안\s*요구사항[:\s]*([^\.]+)',
        r'인터페이스\s*요구사항[:\s]*([^\.]+)',
        r'데이터\s*요구사항[:\s]*([^\.]+)',
        r'시스템\s*요구사항[:\s]*([^\.]+)',
        r'(\d+\.\s*[^\.]+요구사항[^\.]*)',
        r'(\d+\)\s*[^\.]+요구사항[^\.]*)',
        r'(-?\s*[^\.]+요구사항[^\.]*)',
        r'(\*\s*[^\.]+요구사항[^\.]*)'
    ]
    
    for pattern in req_patterns:
        matches = re.findall(pattern, rfp_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 10:  # 의미있는 길이의 텍스트만
                requirements.append(match.strip())
    
    # 평가기준 추출
    eval_patterns = [
        r'평가기준[:\s]*([^\.]+)',
        r'점수[:\s]*([^\.]+)',
        r'가중치[:\s]*([^\.]+)',
        r'기술력[:\s]*([^\.]+)',
        r'경험[:\s]*([^\.]+)',
        r'가격[:\s]*([^\.]+)',
        r'제안서\s*품질[:\s]*([^\.]+)',
        r'평가\s*항목[:\s]*([^\.]+)'
    ]
    
    for pattern in eval_patterns:
        matches = re.findall(pattern, rfp_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 5:
                evaluation_criteria.append(match.strip())
    
    # 일정 추출
    timeline_patterns = [
        r'일정[:\s]*([^\.]+)',
        r'마감일[:\s]*([^\.]+)',
        r'제출[:\s]*([^\.]+)',
        r'계약[:\s]*([^\.]+)',
        r'착수[:\s]*([^\.]+)',
        r'완료[:\s]*([^\.]+)',
        r'(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)',
        r'(\d{4}-\d{2}-\d{2})'
    ]
    
    for pattern in timeline_patterns:
        matches = re.findall(pattern, rfp_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 3:
                timeline.append(match.strip())
    
    # 예산 정보 추출
    budget_patterns = [
        r'예산[:\s]*([^\.]+)',
        r'비용[:\s]*([^\.]+)',
        r'가격[:\s]*([^\.]+)',
        r'금액[:\s]*([^\.]+)',
        r'(\d+억원)',
        r'(\d+만원)',
        r'(\d+원)'
    ]
    
    for pattern in budget_patterns:
        matches = re.findall(pattern, rfp_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 2:
                budget_info.append(match.strip())
    
    # 기술 사양 추출
    tech_patterns = [
        r'기술\s*사양[:\s]*([^\.]+)',
        r'아키텍처[:\s]*([^\.]+)',
        r'플랫폼[:\s]*([^\.]+)',
        r'프레임워크[:\s]*([^\.]+)',
        r'데이터베이스[:\s]*([^\.]+)',
        r'클라우드[:\s]*([^\.]+)',
        r'AI[:\s]*([^\.]+)',
        r'머신러닝[:\s]*([^\.]+)'
    ]
    
    for pattern in tech_patterns:
        matches = re.findall(pattern, rfp_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 5:
                technical_specs.append(match.strip())
    
    # 규정 준수 요구사항 추출
    compliance_patterns = [
        r'규정\s*준수[:\s]*([^\.]+)',
        r'인증[:\s]*([^\.]+)',
        r'표준[:\s]*([^\.]+)',
        r'법규[:\s]*([^\.]+)',
        r'개인정보\s*보호[:\s]*([^\.]+)',
        r'보안[:\s]*([^\.]+)',
        r'ISO[:\s]*([^\.]+)',
        r'K-ISMS[:\s]*([^\.]+)'
    ]
    
    for pattern in compliance_patterns:
        matches = re.findall(pattern, rfp_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 3:
                compliance_requirements.append(match.strip())
    
    # 중복 제거 및 정리
    requirements = list(set(requirements))[:10]  # 최대 10개
    evaluation_criteria = list(set(evaluation_criteria))[:8]
    timeline = list(set(timeline))[:6]
    budget_info = list(set(budget_info))[:5]
    technical_specs = list(set(technical_specs))[:8]
    compliance_requirements = list(set(compliance_requirements))[:6]
    
    result = {
        "requirements": requirements if requirements else ["요구사항을 자동으로 추출할 수 없습니다."],
        "evaluation_criteria": evaluation_criteria if evaluation_criteria else ["평가기준을 자동으로 추출할 수 없습니다."],
        "timeline": timeline if timeline else ["일정 정보를 자동으로 추출할 수 없습니다."],
        "budget_info": budget_info if budget_info else ["예산 정보를 자동으로 추출할 수 없습니다."],
        "technical_specs": technical_specs if technical_specs else ["기술 사양을 자동으로 추출할 수 없습니다."],
        "compliance_requirements": compliance_requirements if compliance_requirements else ["규정 준수 요구사항을 자동으로 추출할 수 없습니다."],
        "summary": f"RFP 문서에서 {len(requirements)}개의 요구사항, {len(evaluation_criteria)}개의 평가기준, {len(timeline)}개의 일정 정보, {len(budget_info)}개의 예산 정보, {len(technical_specs)}개의 기술 사양, {len(compliance_requirements)}개의 규정 준수 요구사항을 추출했습니다.",
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


def extract_pdf_content(pdf_path: str) -> str:
    """
    PDF 파일에서 텍스트 내용을 추출하고 전처리합니다.
    
    Args:
        pdf_path: PDF 파일 경로
    
    Returns:
        전처리된 텍스트 내용
    """
    try:
        content = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    # 페이지별 텍스트 전처리
                    cleaned_text = clean_text(page_text)
                    content += f"\n--- 페이지 {page_num} ---\n"
                    content += cleaned_text
        return content
    except Exception as e:
        print(f"PDF 추출 오류: {e}")
        return f"PDF 파일을 읽을 수 없습니다: {e}"


def clean_text(text: str) -> str:
    """
    PDF에서 추출한 텍스트를 정리합니다.
    
    Args:
        text: 원본 텍스트
    
    Returns:
        정리된 텍스트
    """
    if not text:
        return ""
    
    # 1. 기본 정리
    cleaned = text.strip()
    
    # 2. 페이지 번호 제거 (페이지 하단의 숫자들)
    import re
    
    # 페이지 번호 패턴 제거 (예: "1", "2", "3" 등 단독 숫자)
    cleaned = re.sub(r'^\s*\d+\s*$', '', cleaned, flags=re.MULTILINE)
    
    # 3. 불필요한 기호 정리
    # 연속된 특수문자 제거
    cleaned = re.sub(r'[^\w\s가-힣.,!?;:()\[\]{}"\'-]', ' ', cleaned)
    
    # 4. 띄어쓰기 정리
    # 연속된 공백을 하나로
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # 5. 줄바꿈 정리
    # 연속된 줄바꿈을 두 개로 제한
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
    
    # 6. 문장 경계 정리
    # 문장 끝에 공백이 없으면 추가
    cleaned = re.sub(r'([.!?])([A-Z가-힣])', r'\1 \2', cleaned)
    
    # 7. 숫자와 단어 사이 공백 추가
    cleaned = re.sub(r'(\d)([A-Z가-힣])', r'\1 \2', cleaned)
    cleaned = re.sub(r'([A-Z가-힣])(\d)', r'\1 \2', cleaned)
    
    # 8. 특정 패턴 정리
    # "제 1 장" -> "제1장"
    cleaned = re.sub(r'제\s+(\d+)\s+장', r'제\1장', cleaned)
    cleaned = re.sub(r'제\s+(\d+)\s+절', r'제\1절', cleaned)
    cleaned = re.sub(r'제\s+(\d+)\s+조', r'제\1조', cleaned)
    
    # 9. 괄호 안 공백 정리
    cleaned = re.sub(r'\(\s+', '(', cleaned)
    cleaned = re.sub(r'\s+\)', ')', cleaned)
    
    # 10. 마지막 정리
    cleaned = cleaned.strip()
    
    return cleaned


def extract_structured_requirements(text: str) -> List[str]:
    """
    구조화된 요구사항을 추출합니다.
    
    Args:
        text: 정리된 텍스트
    
    Returns:
        요구사항 리스트
    """
    requirements = []
    
    # 1. 번호가 있는 목록 추출
    numbered_patterns = [
        r'(\d+\.\s*[^\.\n]+)',
        r'(\d+\)\s*[^\.\n]+)',
        r'(\d+\)\s*[^\.\n]+)'
    ]
    
    for pattern in numbered_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 15 and any(keyword in match.lower() for keyword in ['요구', '필수', '기능', '성능', '보안']):
                requirements.append(match.strip())
    
    # 2. 불릿 포인트 추출
    bullet_patterns = [
        r'(-?\s*[^\.\n]+)',
        r'(\*\s*[^\.\n]+)',
        r'(•\s*[^\.\n]+)'
    ]
    
    for pattern in bullet_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 15 and any(keyword in match.lower() for keyword in ['요구', '필수', '기능', '성능', '보안']):
                requirements.append(match.strip())
    
    # 3. 중복 제거 및 정리
    unique_requirements = []
    for req in requirements:
        req = req.strip()
        if req not in unique_requirements and len(req) > 10:
            unique_requirements.append(req)
    
    return unique_requirements[:15]  # 최대 15개


def extract_evaluation_criteria(text: str) -> List[str]:
    """
    평가기준을 추출합니다.
    
    Args:
        text: 정리된 텍스트
    
    Returns:
        평가기준 리스트
    """
    criteria = []
    
    # 평가기준 관련 패턴
    eval_patterns = [
        r'평가\s*기준[:\s]*([^\.\n]+)',
        r'평가\s*항목[:\s]*([^\.\n]+)',
        r'점수[:\s]*([^\.\n]+)',
        r'가중치[:\s]*([^\.\n]+)',
        r'(\d+%[^\.\n]*)',
        r'(\d+점[^\.\n]*)',
        r'(기술력[^\.\n]*)',
        r'(가격[^\.\n]*)',
        r'(경험[^\.\n]*)',
        r'(품질[^\.\n]*)'
    ]
    
    for pattern in eval_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 5:
                criteria.append(match.strip())
    
    return criteria[:10]  # 최대 10개


def run_rfp_parser(topic: str) -> str:
    """
    RFP 파서 실행 함수
    
    Args:
        topic: 분석할 RFP 주제 또는 파일 경로
    
    Returns:
        분석 결과 문자열
    """
    # 파일 경로인지 확인
    if os.path.isfile(topic) and topic.lower().endswith('.pdf'):
        rfp_content = extract_pdf_content(topic)
        if "PDF 파일을 읽을 수 없습니다" in rfp_content:
            return f"❌ **PDF 파일 읽기 오류**\n\n{rfp_content}"
        
        # 구조화된 추출 사용
        requirements = extract_structured_requirements(rfp_content)
        evaluation_criteria = extract_evaluation_criteria(rfp_content)
        
        # 기존 패턴 매칭도 병행
        parsed_data = parse_rfp_document(rfp_content)
        parsed_json = json.loads(parsed_data)
        
        # 구조화된 추출 결과와 병합
        all_requirements = list(set(requirements + parsed_json.get("requirements", [])))
        all_criteria = list(set(evaluation_criteria + parsed_json.get("evaluation_criteria", [])))
        
        parsed_json["requirements"] = all_requirements[:15]
        parsed_json["evaluation_criteria"] = all_criteria[:10]
        
        # PDF 분석 결과 사용
        parsed_data = parsed_json
        
    else:
        # 실제 RFP 내용 (여기서는 예시)
        rfp_content = f"""
        RFP 제목: {topic}
        
        프로젝트 개요:
        - 스마트시티 구축을 위한 통합 플랫폼 개발
        - AI 기반 데이터 분석 및 예측 시스템
        - 실시간 모니터링 및 제어 시스템
        
        주요 요구사항:
        1. 클라우드 기반 아키텍처
        2. 실시간 데이터 처리 능력
        3. 보안 및 개인정보 보호
        4. 모바일 앱 지원
        5. API 제공
        
        평가기준:
        - 기술력: 40%
        - 경험: 30%
        - 가격: 20%
        - 제안서 품질: 10%
        
        일정:
        - 제안서 제출: 2024년 12월 31일
        - 계약 체결: 2025년 1월 15일
        - 프로젝트 착수: 2025년 2월 1일
        - 프로젝트 완료: 2025년 12월 31일
        """
        
        result = parse_rfp_document(rfp_content)
        parsed_data = json.loads(result)
    
    output = f"# 📋 RFP 분석 결과\n\n"
    output += f"**분석 주제:** {topic}\n"
    output += f"**분석 일시:** {parsed_data['analysis_date']}\n\n"
    
    # 핵심 정보만 간결하게 표시
    output += f"## 📊 핵심 정보 요약\n"
    output += f"- **요구사항:** {len(parsed_data['requirements'])}개\n"
    output += f"- **평가기준:** {len(parsed_data['evaluation_criteria'])}개\n"
    output += f"- **일정 항목:** {len(parsed_data['timeline'])}개\n"
    output += f"- **예산 정보:** {len(parsed_data['budget_info'])}개\n"
    output += f"- **기술 사양:** {len(parsed_data['technical_specs'])}개\n"
    output += f"- **규정 준수:** {len(parsed_data['compliance_requirements'])}개\n\n"
    
    # 주요 요구사항만 5개까지
    if parsed_data["requirements"]:
        output += f"## 📝 주요 요구사항 (상위 5개)\n"
        for i, req in enumerate(parsed_data["requirements"][:5], 1):
            output += f"**{i}.** {req}\n"
        if len(parsed_data["requirements"]) > 5:
            output += f"*... 외 {len(parsed_data['requirements']) - 5}개*\n"
        output += "\n"
    
    # 평가기준만 3개까지
    if parsed_data["evaluation_criteria"]:
        output += f"## ⚖️ 평가기준 (상위 3개)\n"
        for i, criteria in enumerate(parsed_data["evaluation_criteria"][:3], 1):
            output += f"**{i}.** {criteria}\n"
        if len(parsed_data["evaluation_criteria"]) > 3:
            output += f"*... 외 {len(parsed_data['evaluation_criteria']) - 3}개*\n"
        output += "\n"
    
    # 일정 정보만 3개까지
    if parsed_data["timeline"]:
        output += f"## 📅 주요 일정 (상위 3개)\n"
        for i, timeline_item in enumerate(parsed_data["timeline"][:3], 1):
            output += f"**{i}.** {timeline_item}\n"
        if len(parsed_data["timeline"]) > 3:
            output += f"*... 외 {len(parsed_data['timeline']) - 3}개*\n"
        output += "\n"
    
    # 기술 사양만 3개까지
    if parsed_data["technical_specs"]:
        output += f"## 🔧 주요 기술 사양 (상위 3개)\n"
        for i, tech in enumerate(parsed_data["technical_specs"][:3], 1):
            output += f"**{i}.** {tech}\n"
        if len(parsed_data["technical_specs"]) > 3:
            output += f"*... 외 {len(parsed_data['technical_specs']) - 3}개*\n"
        output += "\n"
    
    # 분석 요약
    output += f"## 📊 분석 요약\n"
    output += f"{parsed_data['summary']}\n"
    
    return output