import json
import os

BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_company_profile(company: str):
    file_map = {
        "삼성 SDS": "samsung_sds.json",
        "LG CNS": "lg_cns.json",
        "포스코DX": "posco_dx.json"
    }
    filename = file_map.get(company)
    if not filename:
        return {"error": "데이터 없음"}
    path = os.path.join(BASE_PATH, "company_profiles", filename)
    return load_json(path)

def load_internal_data(filename: str):
    path = os.path.join(BASE_PATH, "internal", filename)
    return load_json(path)
