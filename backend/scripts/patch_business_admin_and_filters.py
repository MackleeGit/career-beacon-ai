import os
import re

# 1. Patch recommendation_service.py
rec_path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "recommendation_service.py")
with open(rec_path, "r", encoding="utf-8") as f:
    rec_text = f.read()

target_rec = """    if is_health and adapter in {"mdn", "structured_tutorial", "owasp"}:
        return False
    if is_tech and adapter == "clinical_science":
        return False"""

replacement_rec = """    is_office_admin = any(k in low_career for k in ("secretar", "administrat", "office", "clerk", "assistant", "reception", "coordinator"))

    if is_health and adapter in {"mdn", "structured_tutorial", "owasp"}:
        return False
    if is_tech and adapter == "clinical_science":
        return False
    if is_office_admin and adapter == "clinical_science":
        return False"""

if target_rec in rec_text:
    rec_text = rec_text.replace(target_rec, replacement_rec, 1)
    print("Patched recommendation_service.py (LF)")
elif target_rec.replace("\n", "\r\n") in rec_text:
    rec_text = rec_text.replace(target_rec.replace("\n", "\r\n"), replacement_rec.replace("\n", "\r\n"), 1)
    print("Patched recommendation_service.py (CRLF)")
else:
    print("Target not found in recommendation_service.py")

with open(rec_path, "w", encoding="utf-8") as f:
    f.write(rec_text)

# 2. Patch content_service.py
cs_path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "content_service.py")
with open(cs_path, "r", encoding="utf-8") as f:
    cs_text = f.read()

# Anti-history in _fetch_open_textbook
target_cs_hist = """                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or any(skip in page_title.lower() for skip in ("talk:", "user:", "template:", "category:")):
                            continue"""

replacement_cs_hist = """                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or any(skip in page_title.lower() for skip in ("talk:", "user:", "template:", "category:")):
                            continue
                        # Anti-historical / mythology filter for modern workplace skills
                        hist_skips = ("history of", "mythology", "dynasty", "ancient", "medieval", "century bc", "empire", "folklore", "poetry")
                        if any(h in page_title.lower() for h in hist_skips) and not any(k in skill_name.lower() for k in ("history", "ancient", "myth")):
                            continue"""

if target_cs_hist in cs_text:
    cs_text = cs_text.replace(target_cs_hist, replacement_cs_hist, 1)
    print("Patched open_textbook history filter (LF)")
elif target_cs_hist.replace("\n", "\r\n") in cs_text:
    cs_text = cs_text.replace(target_cs_hist.replace("\n", "\r\n"), replacement_cs_hist.replace("\n", "\r\n"), 1)
    print("Patched open_textbook history filter (CRLF)")
else:
    print("Target not found for open_textbook history filter")

# Domain anchors in resolve_career_domain
target_cs_domain = """            if prefix in {"11", "13", "41", "43"}:
                return "finance"
            if prefix in {"33", "47", "49", "51"}:
                return "safety_trades"
            if prefix == "53":
                return "transportation"

        # Tier 2: Semantic Vector Cosine Similarity against Domain Anchors
        if not hasattr(self, "_domain_anchor_vectors") or not self._domain_anchor_vectors:
            anchors = {
                "health": "healthcare medicine clinical medical doctor surgery nursing dental oral pharmacology hospital patient biology anatomy",
                "tech": "software programming technology web development cloud computer code database api network algorithms",
                "engineering": "aerospace engineering mechanical electrical civil propulsion avionics thermodynamics fluid structural robotics aeronautics CAD materials",
                "science": "biology chemistry physics laboratory scientific research genetics biochemistry environmental earth",
                "security": "cybersecurity information security vulnerability penetration testing access control incident response cryptography",
                "finance": "finance accounting banking financial economics taxation corporate balance sheet valuation audit investments",
                "safety_trades": "occupational workplace safety hazard compliance construction electrical wiring mechanical trades industrial osha",
                "transportation": "aviation pilot aircraft flight navigation aerospace transportation maritime logistics vessel air traffic control flight deck cockpit",
            }"""

replacement_cs_domain = """            if prefix in {"11", "43"}:
                return "business_admin"
            if prefix in {"13", "41"}:
                return "finance"
            if prefix in {"33", "47", "49", "51"}:
                return "safety_trades"
            if prefix == "53":
                return "transportation"

        # Deterministic check for administrative/secretarial occupations
        low_title = (career_title or "").lower()
        if any(k in low_title for k in ("secretar", "administrat", "office assistant", "clerk", "receptionist", "executive assistant")):
            return "business_admin"

        # Tier 2: Semantic Vector Cosine Similarity against Domain Anchors
        if not hasattr(self, "_domain_anchor_vectors") or not self._domain_anchor_vectors:
            anchors = {
                "health": "healthcare medicine clinical medical doctor surgery nursing dental oral pharmacology hospital patient biology anatomy",
                "tech": "software programming technology web development cloud computer code database api network algorithms",
                "engineering": "aerospace engineering mechanical electrical civil propulsion avionics thermodynamics fluid structural robotics aeronautics CAD materials",
                "science": "biology chemistry physics laboratory scientific research genetics biochemistry environmental earth",
                "security": "cybersecurity information security vulnerability penetration testing access control incident response cryptography",
                "finance": "finance accounting banking financial economics corporate budget taxation balance sheet valuation audit investments revenue",
                "business_admin": "office administration secretary executive assistant business travel coordination scheduling clerical workplace management corporate operations administrative logistics customer communication reception office technology",
                "safety_trades": "occupational workplace safety hazard compliance construction electrical wiring mechanical trades industrial osha",
                "transportation": "aviation pilot aircraft flight navigation aerospace transportation maritime logistics vessel air traffic control flight deck cockpit",
            }"""

if target_cs_domain in cs_text:
    cs_text = cs_text.replace(target_cs_domain, replacement_cs_domain, 1)
    print("Patched domain anchors (LF)")
elif target_cs_domain.replace("\n", "\r\n") in cs_text:
    cs_text = cs_text.replace(target_cs_domain.replace("\n", "\r\n"), replacement_cs_domain.replace("\n", "\r\n"), 1)
    print("Patched domain anchors (CRLF)")
else:
    print("Target not found for domain anchors")

# Add business_admin adapter order in fetch_live_source_for_skill
target_cs_order = """            elif domain == "finance":
                adapter_order.extend([
                    ("finance", lambda: self._fetch_finance_knowledge(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                ])"""

replacement_cs_order = """            elif domain == "business_admin":
                adapter_order.extend([
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            elif domain == "finance":
                adapter_order.extend([
                    ("finance", lambda: self._fetch_finance_knowledge(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                ])"""

if target_cs_order in cs_text:
    cs_text = cs_text.replace(target_cs_order, replacement_cs_order, 1)
    print("Patched adapter order for business_admin (LF)")
elif target_cs_order.replace("\n", "\r\n") in cs_text:
    cs_text = cs_text.replace(target_cs_order.replace("\n", "\r\n"), replacement_cs_order.replace("\n", "\r\n"), 1)
    print("Patched adapter order for business_admin (CRLF)")
else:
    print("Target not found for adapter order")

with open(cs_path, "w", encoding="utf-8") as f:
    f.write(cs_text)
print("Finished patching backend services.")
