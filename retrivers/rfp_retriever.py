import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings

AOAI_DEPLOY_EMBED_3_LARGE = os.getenv("AOAI_DEPLOY_EMBED_3_LARGE")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")


def build_rfp_retriever(pdf_path: str):
    """PDF → Split → Embedding → VectorStoreRetriever 생성"""
    loader = PyMuPDFLoader(pdf_path)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
    split_docs = text_splitter.split_documents(docs)

    embeddings = AzureOpenAIEmbeddings(
        model=AOAI_DEPLOY_EMBED_3_LARGE,
        openai_api_version="2024-05-01-preview",
        api_key=AOAI_API_KEY,
        azure_endpoint=AOAI_ENDPOINT,
    )

    vectorstore = FAISS.from_documents(split_docs, embeddings)
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    return retriever
