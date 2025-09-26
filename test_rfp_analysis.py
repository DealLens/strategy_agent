#!/usr/bin/env python3
"""
RFP 분석 테스트
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def test_rfp_analysis():
    print("=== RFP 분석 테스트 ===")
    
    # RFP 텍스트
    rfp_text = """
    📋 요구사항 분석
    주요 요구사항: 
    • 현행 운영 대외 웹사이트의 접근성 지침 미준수에 따른 개선 필요
    • 인터넷뱅킹 (퍼블리싱 및 웹표준개발)
    • 본 과업을 수행함에 있어 도입 장비(개발용), 소프트웨어를 포함한 모든 관련
    • 어플리케이션 프로그램에 대한 당사의 보안 정책을 수용해야 하며, 필요시
    • 모든 기술 지원 서비스는 365*24 지원되어야 함
    • 원활한 사업 추진을 위하여 시스템 개발 일정, 작업/인력 계획 제시
    • 시스템 구축 및 운영에 필요한 아이디어, 해당 어플리케이션/용역의 공급, 설치
    • 사업 일정 계획표와 함께 제공하는 교육계획 및 일정을 구체적으로 제시해야
    • 제안사는 시스템 운영에 필요한 기술지원 및 관련 부대업무를 성실히
    • WAS (UNIX, Weblogic 10.3.5) : 운영 2EA, 개발 1EA
    
    평가 기준: 
    • 제안사의 제안내용에 대한 확인, 검증이 필요한 경우 제안사에 입증자료를 요구할 수 있으며, 입증자료를 제출하지 못하는 경우에는 평가대상에서 제외함
    • 제안서의 모든 기재사항은 객관적으로 입증할 수 있는 관계서류를 첨부하여야 하며, 허위로 작성한 사실이 발견될 시에는 평가대상에서 제외되며, 계약 후에도 계약무효화 할 수 있음
    
    주요 리스크: 
    • 라이선스 비용 증가
    • 납기 일정 지연 가능성
    • 보안 인증 획득 지연
    • 기술 인력 부족
    """
    
    try:
        # RFP 파서 테스트
        from workflow.agents.parsers.rfp_parser import RFPParser
        from app.utils.config import Config
        
        config = Config()
        print(f"✅ 설정 로드 성공: {config.OPENAI_API_KEY[:20]}...")
        
        # RFP 파서 초기화
        parser = RFPParser()
        print("✅ RFP 파서 초기화 성공")
        
        # 간단한 분석 시도
        print("\n🔍 RFP 분석 시작...")
        
        # 요구사항 추출
        requirements = parser.extract_requirements(rfp_text)
        print(f"✅ 요구사항 추출 완료: {len(requirements)}개")
        
        # 리스크 분석
        risks = parser.analyze_risks(rfp_text)
        print(f"✅ 리스크 분석 완료: {len(risks)}개")
        
        # 결과 출력
        print("\n📋 추출된 요구사항:")
        for i, req in enumerate(requirements[:5], 1):  # 처음 5개만 출력
            print(f"  {i}. {req}")
        
        print("\n⚠️ 분석된 리스크:")
        for i, risk in enumerate(risks[:3], 1):  # 처음 3개만 출력
            print(f"  {i}. {risk}")
            
        print("\n🎉 RFP 분석이 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"❌ RFP 분석 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rfp_analysis()

