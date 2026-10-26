"""Backfill missing vectors for authoritative careers only.

Usage: python backend/scripts/backfill_career_embeddings.py --apply
Without --apply, the script only reports how many records would be updated.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import supabase_client
from app.services.embedding_service import EmbeddingService

CANONICAL_SOURCES = ("onet", "esco", "dual_sourced", "curated_list")
PAGE_SIZE = 500
BATCH_SIZE = 64


def get_missing_careers():
    rows = []
    offset = 0
    while True:
        response = (
            supabase_client.table("careers")
            .select("id, title, description, source_origin")
            .in_("source_origin", list(CANONICAL_SOURCES))
            .is_("career_vector", "null")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        page = response.data or []
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += len(page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the computed vectors to Supabase")
    args = parser.parse_args()

    careers = get_missing_careers()
    print(f"Missing canonical career vectors: {len(careers)}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to backfill these rows.")
        return
    if not careers:
        return

    service = EmbeddingService()
    texts = [f"{row['title']}: {row.get('description') or ''}".strip() for row in careers]
    vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        vectors.extend(service.model.embed(texts[start:start + BATCH_SIZE], batch_size=BATCH_SIZE))

    updated = 0
    for row, vector in zip(careers, vectors):
        result = (
            supabase_client.table("careers")
            .update({"career_vector": vector.tolist()})
            .eq("id", row["id"])
            .is_("career_vector", "null")
            .execute()
        )
        if result.data:
            updated += 1
        if updated and updated % 50 == 0:
            print(f"Updated {updated}/{len(careers)}")

    remaining = get_missing_careers()
    print(f"Backfill complete: updated {updated}; canonical records still missing vectors: {len(remaining)}")


if __name__ == "__main__":
    main()
