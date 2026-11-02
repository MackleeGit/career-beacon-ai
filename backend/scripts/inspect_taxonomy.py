import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

def inspect_taxonomy():
    print("=" * 70)
    print("TAXONOMY INSPECTION REPORT: CAREERS & SKILLS")
    print("=" * 70)

    # 1. Careers check
    c_res = supabase_client.table("careers").select("id, title, source_origin, review_status").execute()
    careers = c_res.data or []

    plural_titles = []
    all_other_titles = []
    slash_or_comma_titles = []

    for c in careers:
        t = (c.get("title") or "").strip()
        tl = t.lower()
        if "all other" in tl:
            all_other_titles.append(t)
        # Check plural ending
        words = t.split()
        if words and words[-1].endswith("s") and not words[-1].endswith("ss") and not words[-1].endswith("ics") and not words[-1].endswith("us") and not words[-1].endswith("is"):
            plural_titles.append((c["id"], t))

    print(f"Total Careers: {len(careers)}")
    print(f"Titles with 'All Other': {len(all_other_titles)}")
    if all_other_titles:
        print("  Sample:", all_other_titles[:5])

    print(f"Titles ending in plural 's': {len(plural_titles)}")
    for cid, t in plural_titles[:15]:
        print(f"  * [{cid[:8]}] {t}")

    # 2. Check careers with 0 skills
    cs_res = supabase_client.table("career_skills").select("career_id, skill_id, importance").execute()
    career_skills = cs_res.data or []
    career_ids_with_skills = set(cs["career_id"] for cs in career_skills)
    careers_without_skills = [c for c in careers if c["id"] not in career_ids_with_skills]

    print(f"\nCareers with 0 mapped skills: {len(careers_without_skills)}")
    if careers_without_skills:
        for c in careers_without_skills[:10]:
            print(f"  * [{c['id'][:8]}] {c['title']} (source: {c.get('source_origin')})")

    # 3. Check sample major careers and their essential skills
    test_searches = ["Software Developer", "Registered Nurse", "Data Scientist", "Accountant"]
    print("\nSAMPLE MAJOR CAREERS & ESSENTIAL SKILLS:")
    for query in test_searches:
        matches = [c for c in careers if query.lower() in c["title"].lower()]
        if matches:
            target = matches[0]
            # Fetch skills
            skills_res = (
                supabase_client.table("career_skills")
                .select("importance, skills(name, category)")
                .eq("career_id", target["id"])
                .execute()
            )
            items = skills_res.data or []
            essential = [i["skills"]["name"] for i in items if i.get("importance") == "essential" and i.get("skills")]
            optional = [i["skills"]["name"] for i in items if i.get("importance") == "optional" and i.get("skills")]
            print(f"\n--- {target['title']} (ID: {target['id'][:8]}..., source: {target.get('source_origin')}) ---")
            print(f"  Essential ({len(essential)}): {', '.join(essential[:8])}")
            print(f"  Optional ({len(optional)}): {', '.join(optional[:8])}")
        else:
            print(f"\n--- {query}: NOT FOUND ---")

if __name__ == "__main__":
    inspect_taxonomy()

