"""
Backfill Dual Vectors (title_vector and skills_vector) for Canonical Careers.

Usage:
  python backend/scripts/backfill_dual_career_vectors.py          # Dry run report
  python backend/scripts/backfill_dual_career_vectors.py --apply  # Execute updates
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService

CANONICAL_SOURCES = ("onet", "esco", "dual_sourced", "curated_list")
PAGE_SIZE = 100


async def fetch_careers_to_embed():
    """Fetch canonical curated careers that need dual vectors."""
    rows = []
    offset = 0
    while True:
        res = (
            supabase_client.table("careers")
            .select("id, title, description, source_origin")
            .in_("source_origin", list(CANONICAL_SOURCES))
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        page = res.data or []
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += len(page)
    return rows


async def fetch_skills_for_career(career_id: str):
    """Fetch top essential skills for a career."""
    skills_res = (
        supabase_client.table("career_skills")
        .select("importance, importance_score, skills(name)")
        .eq("career_id", career_id)
        .order("importance_score", desc=True)
        .limit(10)
        .execute()
    )
    names = []
    for r in skills_res.data or []:
        sk = r.get("skills")
        if sk and sk.get("name"):
            names.append(sk["name"])
    return names


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit vectors to Supabase")
    args = parser.parse_args()

    embedding_service = EmbeddingService()

    print("Fetching canonical careers...")
    careers = await fetch_careers_to_embed()
    print(f"Total canonical careers found: {len(careers)}")

    missing_dual = [c for c in careers if not c.get("title_vector") or not c.get("skills_vector")]
    print(f"Careers needing dual vector backfill: {len(missing_dual)}")

    if not args.apply:
        print("\n[Dry Run] Re-run with --apply to compute embeddings and commit to Supabase.")
        return

    print("\nStarting dual vector backfill...")
    updated_count = 0
    for idx, career in enumerate(missing_dual, start=1):
        c_id = career["id"]
        title = career.get("title") or "Unknown"
        desc = career.get("description") or ""

        # 1. Title embedding (compact, role-focused)
        title_text = f"{title}. Role: {desc}".strip()
        title_vec = await embedding_service.get_embedding(title_text)

        # 2. Skills embedding (stack-focused)
        top_skills = await fetch_skills_for_career(c_id)
        if top_skills:
            skills_text = f"Key technical competencies: {', '.join(top_skills)}."
        else:
            skills_text = f"Key technical competencies for {title}."
        skills_vec = await embedding_service.get_embedding(skills_text)

        # 3. Update DB
        supabase_client.table("careers").update({
            "title_vector": title_vec,
            "skills_vector": skills_vec,
        }).eq("id", c_id).execute()

        updated_count += 1
        if idx % 10 == 0 or idx == len(missing_dual):
            print(f"  [{idx}/{len(missing_dual)}] Backfilled: {title}")

    print(f"\nSuccessfully backfilled dual vectors for {updated_count} careers!")


if __name__ == "__main__":
    asyncio.run(main())
