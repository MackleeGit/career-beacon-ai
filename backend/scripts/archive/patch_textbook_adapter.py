import os

path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "content_service.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = """                        if ext_resp.status_code == 200:
                            pages = ext_resp.json().get("query", {}).get("pages", {})
                            for _, pdata in pages.items():
                                extract = strip_html_and_clean(pdata.get("extract", ""))
                                if validate_source_content(extract, skill_name):
                                    return {
                                        "title": page_title,
                                        "source_url": page_url,
                                        "raw_text": extract[:10000],
                                        "source": label,
                                        "source_adapter": "open_textbook",
                                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["open_textbook"],
                                    }"""

replacement = """                        if ext_resp.status_code == 200:
                            pages = ext_resp.json().get("query", {}).get("pages", {})
                            for _, pdata in pages.items():
                                extract = strip_html_and_clean(pdata.get("extract", ""))
                                tokens = [t.lower() for t in skill_name.split() if len(t) >= 4 and t.lower() not in {"general", "basic", "advanced", "skills"}]
                                best_idx = -1
                                for tok in tokens:
                                    idx = extract.lower().find(tok)
                                    if idx != -1:
                                        best_idx = idx
                                        break
                                start_idx = max(0, best_idx - 200) if best_idx != -1 else 0
                                slice_text = extract[start_idx:start_idx + 8000]
                                if validate_source_content(slice_text, skill_name):
                                    return {
                                        "title": page_title,
                                        "source_url": page_url,
                                        "raw_text": slice_text,
                                        "source": label,
                                        "source_adapter": "open_textbook",
                                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["open_textbook"],
                                    }"""

target_crlf = target.replace("\n", "\r\n")
replacement_crlf = replacement.replace("\n", "\r\n")

if target in text:
    text = text.replace(target, replacement, 1)
    print("Replaced LF version.")
elif target_crlf in text:
    text = text.replace(target_crlf, replacement_crlf, 1)
    print("Replaced CRLF version.")
else:
    print("Target not found directly.")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

