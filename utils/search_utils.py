from duckduckgo_search import DDGS

def search_company_info(company: str, query: str = "AI") -> list:
    """
    DuckDuckGo로 경쟁사 최신 정보 검색
    """
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(f"{company} {query}", max_results=5):
            results.append({"title": r["title"], "link": r["href"], "snippet": r["body"]})
    return results
