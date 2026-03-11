import json

def load_texts(file_path="texts.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_script_text(text_id=None, file_path="texts.json"):
    data = load_texts(file_path)
    default_id = data.get("default_text_id", "")
    target_id = text_id if text_id else default_id

    for item in data.get("texts", []):
        if item.get("id") == target_id:
            return item.get("content", ""), target_id

    return "", target_id

def get_default_text_id(file_path="texts.json"):
    data = load_texts(file_path)
    return data.get("default_text_id", "")

def get_all_text_ids(file_path="texts.json"):
    data = load_texts(file_path)
    return [item.get("id") for item in data.get("texts", []) if "id" in item]