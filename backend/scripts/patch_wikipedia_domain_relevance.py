import re

file_path = "backend/app/services/content_service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update signature
old_sig = 'async def _fetch_wikipedia_fallback(\n        self,\n        client: httpx.AsyncClient,\n        skill_name: str,\n        excluded: set,\n    ) -> Optional[Dict[str, Any]]:'
new_sig = 'async def _fetch_wikipedia_fallback(\n        self,\n        client: httpx.AsyncClient,\n        skill_name: str,\n        excluded: set,\n        career_title: str = "",\n    ) -> Optional[Dict[str, Any]]:'

if old_sig not in content:
    # Try CRLF
    old_sig = old_sig.replace('\n', '\r\n')
    new_sig = new_sig.replace('\n', '\r\n')

assert old_sig in content, "Signature not found in content_service.py"
content = content.replace(old_sig, new_sig, 1)

# 2. Add topical filtering in search loop
old_block = '''                        cand_title = res_item.get("title", "")
                        if not cand_title or any(skip in cand_title.lower() for skip in ("disambiguation", "list of", "portal:")):
                            continue'''

new_block = '''                        cand_title = res_item.get("title", "")
                        if not cand_title or any(skip in cand_title.lower() for skip in ("disambiguation", "list of", "portal:", "template:", "category:")):
                            continue

                        # Anti-historical/mythology filter for modern workplace skills
                        hist_skips = ("history of", "mythology", "dynasty", "ancient", "medieval", "century bc", "empire", "folklore")
                        if any(h in cand_title.lower() for h in hist_skips) and not any(k in skill_name.lower() for k in ("history", "ancient", "myth")):
                            continue

                        # Strict Title Topical Relevance: The Wikipedia title must contain at least one topical token from skill or career
                        title_clean = cand_title.lower()
                        skill_words = [t.lower() for t in skill_name.split() if len(t) >= 4 and t.lower() not in {"general", "basic", "advanced", "skills"}]
                        career_words = [t.lower() for t in career_title.split() if len(t) >= 4 and t.lower() not in {"general", "assistant"}]
                        if skill_words or career_words:
                            if not (any(w in title_clean for w in skill_words) or any(w in title_clean for w in career_words)):
                                continue'''

if old_block not in content:
    old_block = old_block.replace('\n', '\r\n')
    new_block = new_block.replace('\n', '\r\n')

assert old_block in content, "Search loop block not found in content_service.py"
content = content.replace(old_block, new_block, 1)

# 3. Pass career_title to fallback call
old_call = 'wiki_res = await self._fetch_wikipedia_fallback(client, skill_name, excluded)'
new_call = 'wiki_res = await self._fetch_wikipedia_fallback(client, skill_name, excluded, career_title=career_title)'

if old_call not in content:
    old_call = old_call.replace('\n', '\r\n')
    new_call = new_call.replace('\n', '\r\n')

assert old_call in content, "Fallback call not found in content_service.py"
content = content.replace(old_call, new_call, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully patched content_service.py with Wikipedia domain and topical verification!")
