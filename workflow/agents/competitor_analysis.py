import os
import glob
import json
from langchain_core.tools import tool

BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "company")


def load_latest_profile(path_pattern: str):
    """패턴에 맞는 파일 중 최신 버전을 로드"""
    files = glob.glob(path_pattern)
    if not files:
        return None
    latest_file = max(files, key=os.path.getctime)
    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f)


@tool
def competitor_analysis(companies: list = None) -> dict:
    """
    경쟁사 데이터 로딩 및 SWOT 생성
    Args:
        companies (list, optional): 분석할 회사 목록.
                                    None이면 data/company 폴더의 모든 회사 분석.
    """
    profiles = {}

    if companies is None:  # 전체 경쟁사 자동 탐색
        all_files = glob.glob(os.path.join(BASE_PATH, "*.json"))
        companies = list({os.path.basename(f).split("_")[0] for f in all_files})

    for c in companies:
        data = load_latest_profile(os.path.join(BASE_PATH, f"{c}_*.json"))
        if data is None:
            profiles[c] = {
                "error": "데이터 없음",
                "swot": {"S": "-", "W": "-", "O": "-", "T": "-"}
            }
            continue

        swot = {
            "S": data.get("strengths", "브랜드 인지도"),
            "W": data.get("weaknesses", "가격 경쟁력 부족"),
            "O": data.get("opportunities", "시장 성장"),
            "T": data.get("threats", "신규 경쟁사 등장")
        }

        profiles[c] = {"profile": data, "swot": swot}

    return {"competitor_profiles": profiles}


# 디버깅 / 단독 실행
if __name__ == "__main__":
    # 전체 경쟁사 자동 분석
    result = competitor_analysis.run()
    print("📊 전체 경쟁사 분석 결과:")
    for comp, info in result["competitor_profiles"].items():
        print(f"\n🔹 {comp}")
        print("  SWOT:", info.get("swot"))
