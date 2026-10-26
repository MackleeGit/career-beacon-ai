import pytest
from app.core.database import supabase_client

def test_supabase_tables_and_columns():
    """Verify all migration columns exist in the live database schema."""
    careers = supabase_client.table("careers").select("*").limit(1).execute()
    assert careers.data is not None
    career_cols = set(careers.data[0].keys())
    for col in ["is_curated", "source_origin", "review_status", "onet_soc_code", "esco_occupation_uri"]:
        assert col in career_cols, f"Missing column {col} in careers table"

    career_skills = supabase_client.table("career_skills").select("*").limit(1).execute()
    assert career_skills.data is not None
    cs_cols = set(career_skills.data[0].keys())
    for col in ["source_origin", "review_status", "importance_score", "importance", "tier", "expected_proficiency", "career_level"]:
        assert col in cs_cols, f"Missing column {col} in career_skills table"

    skills = supabase_client.table("skills").select("*").limit(1).execute()
    assert skills.data is not None
    skill_cols = set(skills.data[0].keys())
    for col in ["onet_element_id", "esco_skill_uri"]:
        assert col in skill_cols, f"Missing column {col} in skills table"

    user_skills = supabase_client.table("user_skills").select("*").limit(1).execute()
    assert user_skills.data is not None
    us_cols = set(user_skills.data[0].keys())
    assert "evidence_source" in us_cols, "Missing column evidence_source in user_skills table"

def test_onet_data_integrity_contract():
    """Verify O*NET seeded occupations and mappings adhere to source integrity rules."""
    onet_careers = supabase_client.table("careers").select("id, title, source_origin, review_status, is_curated, onet_soc_code").eq("source_origin", "onet").execute().data
    assert len(onet_careers) == 10, f"Expected 10 O*NET careers, found {len(onet_careers)}"
    
    for c in onet_careers:
        assert c["review_status"] == "unreviewed", f"Career {c['title']} review_status should be unreviewed"
        assert c["is_curated"] is False, f"Career {c['title']} is_curated should be False"
        assert c["onet_soc_code"] is not None, f"Career {c['title']} must have onet_soc_code"

    onet_cs = supabase_client.table("career_skills").select("career_id, skill_id, importance, importance_score, source_origin, review_status, tier").eq("source_origin", "onet").execute().data
    assert len(onet_cs) == 82, f"Expected 82 O*NET career_skill mappings, found {len(onet_cs)}"

    for row in onet_cs:
        assert row["source_origin"] == "onet"
        assert row["review_status"] == "unreviewed"
        assert row["importance"] in ("essential", "optional")
        assert row["importance_score"] is not None
        assert 0.0 <= row["importance_score"] <= 1.0
        # Ingestion rule: tiers must NOT be fabricated during O*NET ingestion
        assert row["tier"] is None, f"O*NET mapping should have tier=None, found {row['tier']}"

def test_no_duplicate_careers():
    """Verify that there are no duplicate career records in the database."""
    all_careers = supabase_client.table("careers").select("title").execute().data
    titles = [c["title"].strip().lower() for c in all_careers]
    dupes = [t for t in set(titles) if titles.count(t) > 1]
    assert len(dupes) == 0, f"Found duplicate career titles: {dupes}"
