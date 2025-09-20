#  DealLens: 전략분석 에이전트



##  프로젝트 개요
DealLens는 **입찰/RFP 기반 전략분석**을 지원하는 멀티에이전트 시스템입니다.  
LangChain + LangGraph 기반으로 **RFP 문서 분석 → 내부 레퍼런스 검색(RAG) → 경쟁사 분석 → 전략 수립 → 최종 보고서 생성**까지 전체 프로세스를 자동화합니다.  
UI는 **Streamlit** 기반으로 구성되어 있으며, 사용자는 브라우저에서 손쉽게 주제를 입력해 전략분석을 실행할 수 있습니다.  


## 주요 기능
- **RFP Parser**: 요구사항 및 평가기준 추출  
- **Internal RAG**: 내부 프로젝트/성과 데이터 검색  
- **Competitor Analysis**: 경쟁사 강점/약점 분석 및 리스크 도출  
- **Strategy Builder**: 분석 결과 종합 후 전략 제안 생성  
- **Reporter**: 전체 분석 결과를 보고서 형태로 출력


## 기술스택

### Backend & Workflow
- **Python 3.10+**
- **LangChain**: LLM 기반 체인 및 에이전트 구성
- **LangGraph**: 전략분석 파이프라인 워크플로우 관리
- **FastAPI (선택적)**: API 서버 구성 가능

### Retrieval & Vector Store
- **DuckDuckGo Search (DDGS)**: 외부 웹 검색
- **FAISS**: 로컬 벡터스토어
- **OpenAI Embeddings (text-embedding-3-small)**: 임베딩 생성

### Frontend
- **Streamlit**: 브라우저 기반 UI (분석 주제 입력 및 결과 시각화)

### Infra & Config
- **dotenv (.env)**: 환경변수 관리
- **Git**: 버전 관리
- **requirements.txt**: 패키지 의존성 관리

