import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 텍스트 추출 (단순 텍스트, OCR 없음)"""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()
