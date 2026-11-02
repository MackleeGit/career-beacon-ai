import re

# 1. Update recommendation_service.py
rec_path = "backend/app/services/recommendation_service.py"
with open(rec_path, "r", encoding="utf-8") as f:
    rec_text = f.read()

replacement_code = '''SOC_MAJOR_GROUP_DOMAINS: Dict[str, str] = {
    "11": "business_admin",     # Management Occupations
    "13": "business_finance",   # Business and Financial Operations
    "15": "tech",               # Computer and Mathematical
    "17": "engineering",        # Architecture and Engineering
    "19": "science",            # Life, Physical, and Social Science
    "21": "social_services",    # Community and Social Service
    "23": "legal",              # Legal Occupations
    "25": "education",          # Educational Instruction and Library
    "27": "creative_media",     # Arts, Design, Entertainment, Sports, and Media
    "29": "healthcare",         # Healthcare Practitioners and Technical
    "31": "healthcare",         # Healthcare Support
    "33": "protective_service", # Protective Service Occupations
    "35": "hospitality_food",   # Food Preparation and Serving
    "37": "facility_maintenance", # Building and Grounds Cleaning/Maintenance
    "39": "personal_care",      # Personal Care and Service
    "41": "business_finance",   # Sales and Related
    "43": "business_admin",     # Office and Administrative Support
    "45": "trades_industrial",  # Farming, Fishing, and Forestry
    "47": "trades_industrial",  # Construction and Extraction
    "49": "trades_industrial",  # Installation, Maintenance, and Repair
    "51": "trades_industrial",  # Production Occupations
    "53": "transportation",     # Transportation and Material Moving
    "55": "military",           # Military Specific Occupations
}

RESTRICTED_ADAPTER_DOMAINS: Dict[str, set] = {
    "clinical_science": {"healthcare", "science"},
    "mdn": {"tech"},
    "owasp": {"tech", "protective_service"},
    "osha": {"trades_industrial", "engineering", "healthcare", "transportation"},
    "finance": {"business_finance", "business_admin"},
}


def resolve_career_domain_standard(career_title: str, onet_soc_code: Optional[str] = None) -> str:
    """
    Standard BLS SOC taxonomy domain resolution.
    1. Checks the 2-digit Major Group prefix if onet_soc_code is present.
    2. Fallback for the ~15 non-standard or custom AI occupations.
    """
    if onet_soc_code:
        prefix = str(onet_soc_code).strip()[:2]
        if prefix in SOC_MAJOR_GROUP_DOMAINS:
            return SOC_MAJOR_GROUP_DOMAINS[prefix]

    title_low = (career_title or "").lower()
    if any(k in title_low for k in ("health", "medic", "dent", "doctor", "nurs", "physic", "pharm", "therap", "surg", "clinical")):
        return "healthcare"
    if any(k in title_low for k in ("software", "develop", "program", "data", "web", "computer", "cloud", "devops", "cyber", "ai")):
        return "tech"
    if any(k in title_low for k in ("engineer", "aerospace", "mechanical", "electrical", "civil", "architect")):
        return "engineering"
    if any(k in title_low for k in ("secretar", "administrat", "office", "clerk", "reception", "assistant", "coordinator")):
        return "business_admin"
    if any(k in title_low for k in ("finance", "account", "bank", "invest", "audit", "tax", "budget")):
        return "business_finance"
    if any(k in title_low for k in ("pilot", "flight", "driver", "transport", "aviation", "maritime", "cargo")):
        return "transportation"
    if any(k in title_low for k in ("welder", "plumb", "electrician", "carpent", "mechanic", "machin", "construct")):
        return "trades_industrial"
    return "general"


def _is_adapter_compatible_with_career(item: Dict[str, Any], career_title: str, onet_soc_code: Optional[str] = None) -> bool:
    """Taxonomy-driven adapter capability gate across all 855 careers."""
    adapter = (item.get("source_adapter") or "").lower()
    url = (item.get("source_url") or "").lower()
    if not adapter:
        if "developer.mozilla.org" in url or "w3schools.com" in url or "geeksforgeeks.org" in url:
            adapter = "mdn"
        elif "europepmc.org" in url or "ncbi.nlm.nih.gov" in url or "pubmed" in url:
            adapter = "clinical_science"
        elif "owasp.org" in url:
            adapter = "owasp"
        elif "osha.gov" in url:
            adapter = "osha"

    domain = resolve_career_domain_standard(career_title, onet_soc_code)
    allowed_domains = RESTRICTED_ADAPTER_DOMAINS.get(adapter)
    if allowed_domains is not None and domain not in allowed_domains:
        return False
    return True'''

old_func_pattern = r"def _is_adapter_compatible_with_career\(item: Dict\[str, Any\], career_title: str\) -> bool:[\s\S]+?return True"
new_rec_text = re.sub(old_func_pattern, replacement_code, rec_text, count=1)
if new_rec_text != rec_text:
    with open(rec_path, "w", encoding="utf-8") as f:
        f.write(new_rec_text)
    print("Successfully updated recommendation_service.py")
else:
    print("Warning: Pattern not found in recommendation_service.py")

# 2. Update content_service.py: remove title suffix spoofing
cs_path = "backend/app/services/content_service.py"
with open(cs_path, "r", encoding="utf-8") as f:
    cs_text = f.read()

# Replace: title = f"{source_title} — {career_title}" if ... else source_title
cs_text_new = re.sub(
    r'title = f"\{source_title\} — \{career_title\}" if career_title and career_title\.lower\(\) not in source_title\.lower\(\) else source_title',
    'title = source_title',
    cs_text
)

if cs_text_new != cs_text:
    with open(cs_path, "w", encoding="utf-8") as f:
        f.write(cs_text_new)
    print("Successfully removed title spoofing in content_service.py")
else:
    print("Warning: title pattern not found in content_service.py")

