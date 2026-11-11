import os

cs_path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "content_service.py")
with open(cs_path, "r", encoding="utf-8") as f:
    text = f.read()

target = """        try:
            r_srch = await client.get(
                f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(skill_name)}&utf8=&format=json",
                headers=headers,
            )
            if r_srch.status_code == 200:
                results = r_srch.json().get("query", {}).get("search", [])
                if results:
                    best_title = results[0]["title"]
                    slug2 = best_title.replace(" ", "_")
                    r_sum = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(slug2)}", headers=headers)
                    if r_sum.status_code == 200:
                        d2 = r_sum.json()
                        extract2 = d2.get("extract", "")
                        if d2.get("type") == "standard" and validate_source_content(extract2, skill_name):
                            page_url = d2.get("content_urls", {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{slug2}"
                            if page_url not in excluded:
                                return {
                                    "title": d2.get("title", best_title),
                                    "source_url": page_url,
                                    "raw_text": extract2[:5000],
                                    "source": "wikipedia",
                                    "source_adapter": "wikipedia",
                                    "trust_score": SOURCE_AUTHORITY_WEIGHTS["wikipedia"],
                                }
        except Exception as e:
            logger.debug(f"Wikipedia search fallback error: {e}")"""

replacement = """        clean_skill = re.sub(r"^(?:Coordinating|Managing|Establishing and Maintaining|Developing and Implementing|Analyzing|Evaluating)\s+", "", skill_name, flags=re.IGNORECASE).strip()
        search_queries = [skill_name]
        if clean_skill and clean_skill.lower() != skill_name.lower():
            search_queries.append(clean_skill)
            search_queries.append(f"Corporate {clean_skill.lower()}")

        for q in search_queries:
            try:
                r_srch = await client.get(
                    f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=5",
                    headers=headers,
                )
                if r_srch.status_code == 200:
                    results = r_srch.json().get("query", {}).get("search", [])
                    for res_item in results[:5]:
                        cand_title = res_item.get("title", "")
                        if not cand_title or any(skip in cand_title.lower() for skip in ("disambiguation", "list of", "portal:")):
                            continue
                        slug2 = cand_title.replace(" ", "_")
                        page_url = f"https://en.wikipedia.org/wiki/{quote_plus(slug2)}"
                        if page_url in excluded:
                            continue
                        r_sum = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(slug2)}", headers=headers)
                        if r_sum.status_code == 200:
                            d2 = r_sum.json()
                            extract2 = d2.get("extract", "")
                            if d2.get("type") == "standard" and validate_source_content(extract2, skill_name):
                                return {
                                    "title": d2.get("title", cand_title),
                                    "source_url": page_url,
                                    "raw_text": extract2[:5000],
                                    "source": "wikipedia",
                                    "source_adapter": "wikipedia",
                                    "trust_score": SOURCE_AUTHORITY_WEIGHTS["wikipedia"],
                                }
            except Exception as e:
                logger.debug(f"Wikipedia search fallback error for '{q}': {e}")"""

if target in text:
    text = text.replace(target, replacement, 1)
    print("Patched wikipedia fallback search (LF)")
elif target.replace("\n", "\r\n") in text:
    text = text.replace(target.replace("\n", "\r\n"), replacement.replace("\n", "\r\n"), 1)
    print("Patched wikipedia fallback search (CRLF)")
else:
    print("Target not found for wikipedia fallback search")

with open(cs_path, "w", encoding="utf-8") as f:
    f.write(text)
