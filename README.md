# 🚀 DealLens: 전략분석 에이전트

> 입찰/RFP 기반 **자동 전략분석 멀티에이전트 시스템**  
> LangChain + LangGraph + Streamlit 기반 RFP 분석 파이프라인

---

## 📌 프로젝트 개요
DealLens는 **입찰/RFP 기반 전략분석**을 지원하는 멀티에이전트 시스템입니다.  

- 📄 **RFP 문서 분석**  
- 🔍 **내부 레퍼런스 검색(RAG)**  
- 🏢 **경쟁사 분석**  
- 📊 **전략 수립**  
- 📝 **최종 보고서 생성**  

UI는 **Streamlit** 기반으로 제공되어, 브라우저에서 손쉽게 주제를 입력하고 결과를 확인할 수 있습니다.  

---

## ✨ 주요 기능
- 🗂 **RFP Parser**: 요구사항 및 평가기준 추출  
- 📚 **Internal RAG**: 내부 프로젝트/성과 데이터 검색  
- ⚔️ **Competitor Analysis**: 경쟁사 강점/약점 분석 및 리스크 도출  
- 🏗 **Strategy Builder**: 분석 결과 종합 후 전략 제안 생성  
- 📑 **Reporter**: 전체 분석 결과를 보고서 형태로 출력  

---

## 🛠 기술스택

### 🔧 Backend & Workflow
- **Python 3.10+**
- **LangChain** → LLM 기반 체인 및 에이전트 구성
- **LangGraph** → 전략분석 파이프라인 워크플로우 관리
- **FastAPI (선택)** → API 서버 구성 가능

### 📡 Retrieval & Vector Store
- **DuckDuckGo Search (DDGS)** → 외부 웹 검색
- **FAISS** → 로컬 벡터스토어
- **OpenAI Embeddings (text-embedding-3-small)** → 임베딩 생성

### 🎨 Frontend
- **Streamlit** → 브라우저 기반 UI (주제 입력 및 결과 시각화)

### ⚙️ Infra & Config
- **dotenv (.env)** → 환경변수 관리
- **Git** → 버전 관리
- **requirements.txt** → 패키지 의존성 관리
- **Supervisor**: 사용자가 요청한 작업(요구사항 분석, 내부 매칭, 경쟁사 분석, 전략, 보고서)을 자동으로 해당 에이전트에 라우팅하여 실행

---

## 🚀 실행 방법

### 1) 자동 설정 (권장)
```bash
python setup.py
```

### 2) 수동 설정

#### 패키지 설치
```bash
pip install -r requirements.txt
```

#### 환경 변수 설정
`.env` 파일을 생성하고 API 키를 설정하세요:
```bash
# Azure OpenAI 사용 시
AOAI_API_KEY=your_azure_openai_api_key_here
AOAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AOAI_DEPLOY_GPT4O=gpt-4o
AOAI_API_VERSION=2024-10-21

# 또는 OpenAI 사용 시
OPENAI_API_KEY=your_openai_api_key_here
```

### 3) 애플리케이션 실행
```bash
streamlit run main.py
```

브라우저에서 `http://localhost:8501`로 접속하여 애플리케이션을 사용할 수 있습니다.

---

## 📋 사용 방법

### 전체 파이프라인 (권장)
1. **RFP 파일 업로드**: PDF 형태의 RFP 문서를 업로드
2. **분석 주제 입력**: RFP 제목이나 프로젝트 주제를 입력
3. **추가 요청사항 입력** (선택사항): 특별히 중점을 두고 분석하고 싶은 부분 입력
4. **분석 모드 선택**: "전체 파이프라인" 선택
5. **분석 실행**: "분석 시작" 버튼을 클릭하여 A→B→C→D→E 순차 실행
6. **결과 확인**: 종합 분석 결과 및 제안 브리핑 확인

### 개별 모드
1. **분석 모드 선택**: 전략 분석, 경쟁사 분석, RFP 파서, 내부 RAG, 리포터 중 선택
2. **주제 입력**: 분석하고자 하는 RFP나 프로젝트 주제를 입력
3. **분석 실행**: "분석 시작" 버튼을 클릭하여 해당 에이전트가 분석 수행
4. **결과 확인**: 분석 결과를 확인하고 필요시 새 분석 시작

---

## ⚠️ 주의사항

- API 키가 설정되지 않은 경우 Mock 응답이 제공됩니다
- 실제 분석을 위해서는 OpenAI 또는 Azure OpenAI API 키가 필요합니다
- 대용량 RFP 문서 처리 시 시간이 소요될 수 있습니다

