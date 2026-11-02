import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import supabase_client

def inspect_content():
    print("=" * 70)
    print("CAREER BEACON INSTRUCTIONAL CONTENT AUDIT")
    print("=" * 70)

    # 1. Total micro_content count
    mc_count = supabase_client.table("micro_content").select("id", count="exact").limit(1).execute()
    total = mc_count.count
    print(f"Total Lessons in `micro_content`: {total}")

    # Fetch sample of rows to analyze source distribution
    res = supabase_client.table("micro_content").select("id, title, source_url, difficulty_level, associated_skill_id, quizzes").limit(200).execute()
    rows = res.data or []

    sources = {}
    quizzes_count = 0
    skills_with_content = set()

    for r in rows:
        url = r.get("source_url") or ""
        # Classify
        if "youtube.com" in url or "youtu.be" in url:
            src = "YouTube Educational Video"
        elif any(k in url for k in ("geeksforgeeks.org", "tutorialspoint.com", "w3schools.com")):
            src = "Structured Interactive Tutorial"
        elif any(k in url for k in ("wikibooks.org", "wikiversity.org", "openstax.org")):
            src = "Open Textbook (Wikibooks / OpenStax)"
        elif any(k in url for k in ("ncbi.nlm.nih.gov", "europepmc.org")):
            src = "Clinical Science (NCBI StatPearls / Europe PMC)"
        elif "developer.mozilla.org" in url:
            src = "MDN Web Docs"
        elif "openalex.org" in url or "doi.org" in url:
            src = "OpenAlex Peer-Reviewed Review"
        elif "wikipedia.org" in url:
            src = "Wikipedia (Last Resort Fallback)"
        else:
            src = "Other Curated Web Source"

        sources[src] = sources.get(src, 0) + 1
        q = r.get("quizzes")
        if q and isinstance(q, list) and len(q) >= 3:
            quizzes_count += 1
        if r.get("associated_skill_id"):
            skills_with_content.add(r.get("associated_skill_id"))

    print(f"\nSample Source Distribution ({len(rows)} inspected):")
    for s, cnt in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  * {s}: {cnt} ({cnt/len(rows)*100:.1f}%)")

    print(f"\nLessons with valid >=3 question quizzes: {quizzes_count} / {len(rows)} ({quizzes_count/len(rows)*100:.1f}%)")
    print(f"Unique skills linked in sample: {len(skills_with_content)}")

    print("\nSample Lesson Titles in Database:")
    for r in rows[:8]:
        qlen = len(r.get('quizzes') or [])
        print(f"  - [{r.get('difficulty_level', 'N/A')}] {r.get('title')} ({qlen} Qs) -> {r.get('source_url')[:60]}...")

if __name__ == "__main__":
    inspect_content()

