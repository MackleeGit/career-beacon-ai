import os

cs_path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "content_service.py")
with open(cs_path, "r", encoding="utf-8") as f:
    text = f.read()

target = """                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or any(skip in page_title.lower() for skip in ("talk:", "user:", "template:", "category:")):
                            continue
                        # Anti-historical / mythology filter for modern workplace skills
                        hist_skips = ("history of", "mythology", "dynasty", "ancient", "medieval", "century bc", "empire", "folklore", "poetry")
                        if any(h in page_title.lower() for h in hist_skips) and not any(k in skill_name.lower() for k in ("history", "ancient", "myth")):
                            continue"""

replacement = """                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or any(skip in page_title.lower() for skip in ("talk:", "user:", "template:", "category:")):
                            continue
                        # Anti-historical / mythology / philosophy / fiction filter for modern workplace skills
                        hist_skips = ("history of", "mythology", "dynasty", "ancient", "medieval", "century bc", "empire", "folklore", "poetry", "ontology", "philosophy of", "fiction", "novel")
                        if any(h in page_title.lower() for h in hist_skips) and not any(k in skill_name.lower() for k in ("history", "ancient", "myth", "philosophy")):
                            continue

                        # Strict Title Topical Relevance: The textbook title must contain at least one topical token from skill or career
                        title_clean = page_title.lower()
                        skill_words = [t.lower() for t in skill_name.split() if len(t) >= 4 and t.lower() not in {"general", "basic", "advanced", "skills"}]
                        career_words = [t.lower() for t in career_title.split() if len(t) >= 4 and t.lower() not in {"general", "assistant"}]
                        if not (any(w in title_clean for w in skill_words) or any(w in title_clean for w in career_words)):
                            continue"""

if target in text:
    text = text.replace(target, replacement, 1)
    print("Patched open_textbook title topical relevance (LF)")
elif target.replace("\n", "\r\n") in text:
    text = text.replace(target.replace("\n", "\r\n"), replacement.replace("\n", "\r\n"), 1)
    print("Patched open_textbook title topical relevance (CRLF)")
else:
    print("Target not found for open_textbook title relevance")

with open(cs_path, "w", encoding="utf-8") as f:
    f.write(text)
