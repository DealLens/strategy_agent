# Strategy Agent - RFP 전략 분석 시스템

SK AX의 RFP(제안요청서) 분석 및 전략 수립을 위한 AI 기반 통합 플랫폼입니다.

## 🚀 주요 기능

### 1. RFP 문서 분석 (`rfp_parser`)
- PDF 형태의 RFP 문서를 자동으로 분석
- 요구사항, 평가기준, 리스크, 조견표, 목차 추출
- AI 기반 요약 및 구조화된 데이터 생성

### 2. 내부 역량 매칭 (`internal_rag`)
- SK AX의 기존 프로젝트 케이스 스터디와 요구사항 매칭
- 적합도 점수 계산 및 레퍼런스 제안
- 내부 데이터베이스 기반 유사도 검색

### 3. 경쟁사 분석 (`competitor_analysis`)
- 주요 경쟁사(삼성SDS, LG CNS, 현대오토에버) 뉴스 크롤링
- SWOT 분석 및 차별화 포인트 도출
- 경쟁사별 대응 전략 수립

### 4. 전략 합성 (`strategy_synthesizer`)
- 컨설턴트 수준의 종합 전략 분석
- 우선순위 액션 플랜 및 로드맵 제시
- 리스크 관리 및 KPI 설정

## 📁 프로젝트 구조

```
strategy_agent/
├── app/                          # Streamlit 웹 애플리케이션
│   ├── utils/
│   │   └── config.py            # 설정 관리
│   └── app.py                   # 메인 웹 앱 (28,032 lines)
├── workflow/                     # 핵심 비즈니스 로직
│   ├── agents/                  # 개별 에이전트들
│   │   ├── rfp_parser.py        # RFP 분석 에이전트
│   │   ├── internal_rag.py      # 내부 데이터 매칭
│   │   ├── competitor_analysis.py # 경쟁사 분석
│   │   └── strategy_synthesizer.py # 전략 합성
│   └── supervisor.py            # 전체 워크플로우 관리
├── utils/                       # 공통 유틸리티
│   ├── llm_client.py           # 통합 LLM 클라이언트
│   ├── data_loader.py          # 데이터 로더
│   ├── embedding_utils.py      # 임베딩 유틸리티
│   ├── ocr_utils.py           # OCR 기능
│   ├── search_utils.py        # 검색 유틸리티
│   └── state_manager.py       # 상태 관리
├── retrivers/                  # 데이터 검색기
│   ├── internal_retriever.py   # 내부 데이터 검색
│   └── rfp_retriever.py       # RFP 문서 검색
├── data/                       # 데이터 저장소
│   ├── company/               # 경쟁사 데이터
│   ├── internal/             # 내부 케이스 스터디
│   └── samples/              # 샘플 RFP 문서
└── db/                        # 벡터 데이터베이스
    └── faiss_index/          # FAISS 인덱스
```

## 🛠️ 기술 스택

- **AI/ML**: Azure OpenAI GPT-4o, OpenAI API
- **벡터 검색**: FAISS (Facebook AI Similarity Search)
- **웹 프레임워크**: Streamlit
- **문서 처리**: PyMuPDF, OCR
- **데이터 처리**: LangChain, pandas
- **웹 크롤링**: BeautifulSoup, requests

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd strategy_agent

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치 (필수)
# requirements.txt 파일에 명시된 모든 패키지를 설치해야 합니다.
pip install -r requirements.txt
```

### 2. API 키 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가:

```env
# Azure OpenAI 설정 (권장)
AOAI_API_KEY=your_azure_openai_api_key
AOAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AOAI_API_VERSION=2024-02-15-preview
AOAI_DEPLOY_GPT4O=gpt-4o
AOAI_DEPLOY_GPT4O_MINI=gpt-4o-mini
AOAI_DEPLOY_EMBED_3_LARGE=text-embedding-3-large

# 또는 OpenAI 설정
OPENAI_API_KEY=your_openai_api_key

# 기타 설정
ENVIRONMENT=development
```

### 3. 애플리케이션 실행

```bash
# Streamlit 웹 앱 실행
streamlit run app.py

# 또는 직접 실행
python app.py
```

## 📊 사용 방법

### 1. RFP 문서 업로드
- 웹 인터페이스에서 PDF 형태의 RFP 문서를 업로드
- 자동으로 문서 분석 시작

### 2. 전략 분석 실행
시스템이 자동으로 다음 단계를 수행합니다:

1. **RFP 분석**: 요구사항, 평가기준, 리스크 추출
2. **내부 매칭**: SK AX 기존 프로젝트와 매칭
3. **경쟁사 분석**: 주요 경쟁사 동향 분석
4. **전략 합성**: 종합 전략 및 액션 플랜 제시

### 3. 결과 확인
- 전략 브리핑 (1페이지 요약)
- 상세 전략 분석 리포트
- 경쟁사 대응 전략
- 리스크 관리 및 KPI

## 🔧 주요 모듈 설명

### RFP Parser
- PDF 문서를 OCR로 텍스트 추출
- AI 기반 요구사항 분류 및 요약
- 조견표 자동 생성

### Internal RAG
- SK AX 케이스 스터디 데이터베이스 구축
- 요구사항별 유사도 검색
- 적합도 점수 계산

### Competitor Analysis
- 3대 경쟁사 뉴스 크롤링 (다음, 네이버, 구글)
- SWOT 분석 및 차별화 포인트 도출
- 익명화된 경쟁사 분석 (A사, B사, C사)

### Strategy Synthesizer
- 컨설턴트 수준 전략 분석
- WooPriority 액션 플랜 및 로드맵
- 리스크 관리 및 KPI 설정

## 📈 성능 최적화

- **병렬 처리**: RFP 분석, 내부 매칭, 경쟁사 분석을 병렬로 실행
- **캐싱**: 경쟁사 데이터 캐싱으로 중복 크롤링 방지
- **벡터 검색**: FAISS를 활용한 고속 유사도 검색
- **비동기 처리**: asyncio를 활용한 비동기 워크플로우

## 🛡️ 보안 및 익명화

- **회사명 익명화**: 경쟁사 분석 시 실제 회사명을 A사, B사, C사로 익명화
- **데이터 보안**: 내부 데이터 암호화 및 접근 제어
- **API 키 관리**: 환경변수를 통한 안전한 API 키 관리

## 🔍 문제 해결

### API 연결 실패
```bash
# API 키 확인
echo $AOAI_API_KEY  # 또는 $OPENAI_API_KEY

# 네트워크 연결 확인
ping openai.azure.com  # 또는 api.openai.com
```

### 데이터 로드 실패
```bash
# 데이터 디렉토리 확인
ls -la data/internal/
ls -la data/company/
```

### 벡터 인덱스 오류
```bash
# FAISS 인덱스 재생성
rm -rf db/faiss_index/
python -c "from retrivers.internal_retriever import build_internal_retriever; build_internal_retriever()"
```

## 📝 라이선스

이 프로젝트는 SK AX 내부 사용을 위한 전용 시스템입니다.

## 🤝 기여

프로젝트 개선이나 버그 리포트는 개발팀에 문의해주세요.

## 📞 지원

---

**Version**: 3.1  
**Last Updated**: 2024년 12월  
**Author**: SK AX 신입사원 개발팀 8조
