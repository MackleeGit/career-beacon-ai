import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import supabase_client

def inspect_web_dev_skills():
    career_id = "de6cab44-2961-4694-b46e-b38d724db3e3"
    c_res = supabase_client.table("careers").select("id, title, onet_soc_code").eq("id", career_id).execute()
    print("Career:", c_res.data)

    cs_res = supabase_client.table("career_skills").select("skill_id, importance, importance_score, tier, rank, skills(id, name, category)").eq("career_id", career_id).execute()
    print(f"Total career_skills for Web Developer: {len(cs_res.data)}")
    
    categories = {}
    for cs in cs_res.data:
        sk = cs.get("skills")
        if sk:
            cat = sk.get("category", "Uncategorized")
            categories.setdefault(cat, []).append((sk.get("name"), cs.get("importance"), cs.get("tier")))

    print("\nBreakdown by skill category:")
    for cat, items in categories.items():
        print(f"  Category: '{cat}' ({len(items)} skills)")
        for name, imp, tier in items[:5]:
            print(f"    - {name} [importance: {imp}, tier: {tier}]")

if __name__ == "__main__":
    inspect_web_dev_skills()

