import os

cs_path = os.path.abspath("backend/app/services/content_service.py")
with open(cs_path, "r", encoding="utf-8") as f:
    text = f.read()

old_pref = """            if prefix in {"33", "47", "49", "51"}:
                return "safety_trades" """

# check without trailing space
old_pref = '            if prefix in {"33", "47", "49", "51"}:\n                return "safety_trades"'
new_pref = '            if prefix in {"33", "47", "49", "51"}:\n                return "safety_trades"\n            if prefix == "53":\n                return "transportation"'

old_anchor = '                "safety_trades": "occupational workplace safety hazard compliance construction electrical wiring mechanical trades industrial osha",\n            }'
new_anchor = '                "safety_trades": "occupational workplace safety hazard compliance construction electrical wiring mechanical trades industrial osha",\n                "transportation": "aviation pilot aircraft flight navigation aerospace transportation maritime logistics vessel air traffic control flight deck cockpit",\n            }'

old_eng = """            elif domain == "engineering":
                adapter_order.extend([
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("osha", lambda: self._fetch_osha_standards(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                ])"""

new_eng = """            elif domain == "engineering":
                adapter_order.extend([
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                    ("osha", lambda: self._fetch_osha_standards(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            elif domain == "transportation":
                adapter_order.extend([
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("osha", lambda: self._fetch_osha_standards(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])"""

assert old_pref in text, "old_pref not found"
assert old_anchor in text, "old_anchor not found"
assert old_eng in text, "old_eng not found"

text = text.replace(old_pref, new_pref, 1)
text = text.replace(old_anchor, new_anchor, 1)
text = text.replace(old_eng, new_eng, 1)

with open(cs_path, "w", encoding="utf-8") as f:
    f.write(text)

print("PASS: Transportation domain and real open-source engineering adapters updated.")

