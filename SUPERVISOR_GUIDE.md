# 🚀 DealLens Supervisor Agent 가이드

## 📌 개요

DealLens Supervisor Agent는 RFP 업로드 시 **세션 캐시 없이** 매 요청마다 하위 에이전트들을 순차 호출하여 제안 브리핑과 Q&A 가능한 아티팩트를 생성하는 핵심 컴포넌트입니다.

## 🔄 실행 순서

```
A(RFP Parser) → B(Internal RAG) → C(Competitor) → D(Strategy) → E(Reporter)
```

### 1. A: RFP Parser
- **입력**: PDF 파일 경로
- **출력**: `{requirements[], criteria[], risks[]}`
- **기능**: RFP 문서에서 요구사항, 평가기준, 리스크 추출

### 2. B: Internal RAG
- **입력**: A단계의 requirements 리스트
- **출력**: `{matches[], references[]}`
- **기능**: 내부 지식베이스에서 매칭되는 프로젝트/솔루션 검색

### 3. C: Competitor Analysis
- **입력**: 분석할 경쟁사 목록 (기본값: 삼성 SDS, LG CNS, 포스코DX, KT, 현대오토에버, 카카오, CJ 올리브네트웍스)
- **출력**: `{profiles: {<회사명>: {...}, ...}}`
- **기능**: 경쟁사 프로필 및 SWOT 분석

### 4. D: Strategy Synthesis
- **입력**: A, B, C 단계의 모든 결과
- **출력**: `{actions[], our_swot{}, differentiation[]}`
- **기능**: 종합 분석을 통한 전략 수립

### 5. E: Report Generation
- **입력**: 모든 단계의 결과
- **출력**: 마크다운 형태의 보고서 문자열
- **기능**: 최종 제안 브리핑 생성

## 📊 최종 반환 포맷

```json
{
  "artifacts": {
    "A": { "requirements": [...], "criteria": [...], "risks": [...] },
    "B": { "matches": [...], "references": [...] },
    "C": { "profiles": { "<회사>": {...}, ... } },
    "D": { "actions": [...], "our_swot": {...}, "differentiation": [...] }
  },
  "deal_brief": "<E가 생성한 1~2p 요약(마크다운 허용)>",
  "qa_ready": true
}
```

## 🛠 사용 방법

### Python에서 직접 사용
```python
from workflow.supervisor_agent import run_deallens_pipeline

# 전체 파이프라인 실행
result = run_deallens_pipeline("path/to/rfp.pdf")

# 경쟁사 목록 지정
result = run_deallens_pipeline("path/to/rfp.pdf", ["삼성 SDS", "LG CNS"])
```

### Streamlit UI에서 사용
1. "전체 파이프라인" 모드 선택
2. RFP 파일 경로 또는 주제 입력
3. "분석 시작" 클릭

## ⚙️ 정책

### 캐시 금지
- 이전 호출 결과를 추정해서 재사용하지 않음
- 매 요청마다 상기 순서로 재실행

### 결측 허용
- 특정 단계가 부족해도 파이프라인을 멈추지 않음
- 가능한 부분만 합성하고 "부족/미확인"으로 표기

### 숫자 일관성
- 평가 가중치/컷오프 등 수치가 없으면 null로 표기

### 간결성
- 보고서 본문은 간결한 불릿 중심
- 표/섹션 헤더를 활용

## 🔧 확장 가능한 툴

현재 구현된 툴들은 샘플 데이터를 반환합니다. 실제 운영을 위해서는 다음 기능들을 구현해야 합니다:

### parse_rfp()
- PyPDF2, pdfplumber 등을 사용한 실제 PDF 파싱
- OCR 기능 (이미지 기반 PDF)
- 구조화된 데이터 추출

### match_internal_knowledge()
- FAISS, Chroma 등 벡터 데이터베이스 연결
- 임베딩 기반 유사도 검색
- 내부 프로젝트 데이터베이스 연동

### load_competitor_data()
- 경쟁사 정보 데이터베이스 연결
- 웹 스크래핑 또는 API 연동
- 실시간 정보 업데이트

### synthesize_strategy()
- LLM 기반 전략 수립 로직
- SWOT 분석 자동화
- 차별화 전략 도출

### generate_report()
- 템플릿 기반 보고서 생성
- 마크다운/HTML 출력
- 차트/그래프 포함

## 🚨 오류 처리

- RFP 경로가 없으면 즉시 "RFP 파일 경로 필요" 메시지 반환
- 각 단계별 예외 처리로 파이프라인 중단 방지
- 부분적 결과라도 최대한 활용

## 📈 성능 최적화

- 병렬 처리 가능한 단계 식별
- 캐싱 전략 수립 (필요시)
- 메모리 사용량 최적화
- 대용량 PDF 처리 최적화
