"""
backend/app/core/career_fields.py
---------------------------------
Canonical 6-Field Cognitive Occupational Scope & Modality Specification for Career Beacon:
  1. tech           — Software, Data & Cybersecurity (Core Mastery)
  2. engineering    — Engineering & Applied Physical Systems (Core Mastery)
  3. healthcare     — Healthcare, Biomedical & Clinical Practice (Core Mastery)
  4. science        — Life, Physical & Analytical Sciences (Core Mastery)
  5. finance        — Finance, Accounting & Quantitative Business (Core Mastery)
  6. business_ops   — Business Operations, Management, Legal & Digital Media (Core Mastery)

Physical, athletic, and purely manual trades (Tier 7) are strictly suppressed:
Kinesthetic and motor occupations are intercepted via SOC prefix and keyword rules
and redirected to analytical, clinical, or supervisory counterparts served by
cognitive micro-learning.
"""

from typing import Dict, Any, List, Optional


CAREER_FIELDS: Dict[str, Dict[str, Any]] = {
    "tech": {
        "field_id": "tech",
        "label": "Software, Data & Cybersecurity",
        "track_type": "core_mastery",
        "legacy_domain": "tech",
        "youtube_modifier": "programming software architecture tutorial lecture",
        "extraction_directive": (
            "Focus strictly on software engineering, programming languages/querying (SQL, Python, TypeScript), "
            "distributed system architecture, APIs, database indexing, cloud/container tooling (Docker, Kubernetes), "
            "machine learning/data pipelines, and cybersecurity/OWASP protocols."
        ),
    },
    "engineering": {
        "field_id": "engineering",
        "label": "Engineering & Applied Physical Systems",
        "track_type": "core_mastery",
        "legacy_domain": "engineering",
        "youtube_modifier": "engineering lecture mechanics design calculation",
        "extraction_directive": (
            "Focus strictly on analytical engineering mechanics, structural/thermal/fluid calculations, "
            "circuit & control systems analysis, CAD/BIM/FEA simulation tools, IEEE/ASME/building design codes, "
            "and failure mode / quality assurance methodologies."
        ),
    },
    "healthcare": {
        "field_id": "healthcare",
        "label": "Healthcare, Biomedical & Clinical Practice",
        "track_type": "core_mastery",
        "legacy_domain": "healthcare",
        "youtube_modifier": "clinical medicine nursing pharmacology lecture",
        "extraction_directive": (
            "Focus strictly on clinical assessment & differential diagnosis, patient triage protocols, "
            "pharmacology & medication dosage calculations, diagnostic lab/imaging interpretation, "
            "evidence-based procedural protocols, and infection control / HIPAA compliance."
        ),
    },
    "science": {
        "field_id": "science",
        "label": "Life, Physical & Analytical Sciences",
        "track_type": "core_mastery",
        "legacy_domain": "science",
        "youtube_modifier": "scientific research laboratory methodology lecture",
        "extraction_directive": (
            "Focus strictly on analytical & experimental instrumentation (PCR, HPLC, spectroscopy, assays), "
            "research study design, biostatistics & quantitative hypothesis testing, scientific computing, "
            "and Good Laboratory Practice (GLP) / biosafety governance."
        ),
    },
    "finance": {
        "field_id": "finance",
        "label": "Finance, Accounting & Quantitative Business",
        "track_type": "core_mastery",
        "legacy_domain": "business_finance",
        "youtube_modifier": "corporate finance accounting GAAP valuation lecture",
        "extraction_directive": (
            "Focus strictly on 3-statement financial modeling, Discounted Cash Flow (DCF) & valuation, "
            "GAAP/IFRS accounting standards, internal audit controls (SOX), variance & capital budgeting analysis, "
            "and quantitative risk / regulatory compliance (AML/KYC, Basel, SEC)."
        ),
    },
    "business_ops": {
        "field_id": "business_ops",
        "label": "Business Operations, Management, Legal & Digital Media",
        "track_type": "core_mastery",
        "legacy_domain": "business_admin",
        "youtube_modifier": "operations management framework case study lecture",
        "extraction_directive": (
            "Focus strictly on operational & project management frameworks (Agile/Scrum, critical path, supply chain EOQ/JIT), "
            "business process modeling (BPMN), legal/contract analysis & regulatory compliance, UX/product design systems, "
            "and CRM/ERP/marketing analytics workflows."
        ),
    },
    "trades_safety": {
        "field_id": "trades_safety",
        "label": "Technical Licensing, Code Compliance & Operational Safety",
        "track_type": "companion_licensing",
        "legacy_domain": "protective_service",
        "youtube_modifier": "code compliance regulatory standard inspection lecture",
        "extraction_directive": (
            "Focus strictly on regulatory standards and codes (FAA, NEC, OSHA, EPA, NFPA, HACCP), "
            "diagnostic procedures, schematic analysis, equipment safety protocols, written licensing exams, "
            "and operational risk management (never physical muscle-memory or kinesthetic motor skills)."
        ),
    },
}


# Purely kinesthetic, athletic, or manual-motor SOC sub-prefixes that cannot be taught
# via cognitive micro-lessons, mapped to their analytical/supervisory catalog counterparts.
KINESTHETIC_SOC_REDIRECTS: List[Dict[str, Any]] = [
    {
        "prefixes": ("27-2021", "27-2022", "27-2023"),
        "keywords": ("athlete", "footballer", "soccer player", "basketball player", "sprinter", "boxer", "marathon runner"),
        "reason": (
            "Physical athletic competition relies on kinesthetic motor training rather than digital micro-lessons. "
            "Showing analytical, clinical, and performance-science careers in sports & human performance:"
        ),
        "target_soc_codes": [
            "29-1128.00",
            "29-9091.00",
            "15-2051.00",
            "15-2041.00",
            "15-2031.00",
            "29-1123.00",
        ],
        "target_titles": [
            "Exercise Physiologist",
            "Exercise Physiologists",
            "Athletic Trainer",
            "Athletic Trainers",
            "Data Scientist",
            "Data Scientists",
            "Statistician",
            "Statisticians",
            "Operations Research Analyst",
            "Operations Research Analysts",
            "Physical Therapist",
            "Physical Therapists",
        ],
    },
    {
        "prefixes": ("53-30", "53-70", "53-60"),
        "keywords": ("bus driver", "truck driver", "delivery driver", "chauffeur", "tractor-trailer", "forklift operator"),
        "reason": (
            "Motor vehicle handling requires physical behind-the-wheel hours. "
            "Showing logistics, fleet operations, and transportation management careers served by Career Beacon:"
        ),
        "target_soc_codes": [
            "11-3071.00",
            "13-1081.00",
            "11-3071.04",
            "11-3051.00",
            "15-2031.00",
            "43-5011.00",
        ],
        "target_titles": [
            "Transportation, Storage, and Distribution Manager",
            "Transportation, Storage, and Distribution Managers",
            "Logistician",
            "Logisticians",
            "Supply Chain Manager",
            "Supply Chain Managers",
            "Industrial Production Manager",
            "Industrial Production Managers",
            "Operations Research Analyst",
            "Operations Research Analysts",
            "Cargo and Freight Agent",
            "Cargo and Freight Agents",
        ],
    },
    {
        "prefixes": ("37-20", "37-30", "45-20", "45-40", "47-30"),
        "keywords": ("janitor", "groundskeep", "bricklayer", "hod carrier", "logger", "farmworker"),
        "reason": (
            "Manual field labor relies on physical execution. "
            "Showing supervisory, engineering, safety compliance, and project management counterparts:"
        ),
        "target_soc_codes": [
            "11-9021.00",
            "19-5011.00",
            "29-9011.00",
            "13-1051.00",
            "11-3013.00",
            "17-2051.00",
            "19-2041.00",
        ],
        "target_titles": [
            "Construction Manager",
            "Construction Managers",
            "Occupational Health and Safety Specialist",
            "Occupational Health and Safety Specialists",
            "Cost Estimator",
            "Cost Estimators",
            "Facilities Manager",
            "Facilities Managers",
            "Civil Engineer",
            "Civil Engineers",
            "Environmental Scientist and Specialist, Including Health",
            "Environmental Scientists and Specialists, Including Health",
        ],
    },
]


def check_kinesthetic_redirect(
    query_or_title: str,
    onet_soc_code: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Checks whether an occupation or search query belongs to a purely kinesthetic/motor
    category that should be redirected to analytical, clinical, or supervisory tracks.
    """
    soc_clean = str(onet_soc_code or "").strip()
    q_low = (query_or_title or "").strip().lower()

    for rule in KINESTHETIC_SOC_REDIRECTS:
        if soc_clean and any(soc_clean.startswith(pref) for pref in rule["prefixes"]):
            return rule
        if q_low and any(kw in q_low for kw in rule["keywords"]):
            return rule
    return None


def classify_career_field(
    career_title: str = "",
    onet_soc_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministically maps an O*NET SOC code (or career title) to one of the 7 Served Career Fields.
    Returns the field metadata dictionary from CAREER_FIELDS.
    """
    if check_kinesthetic_redirect(career_title, onet_soc_code):
        return CAREER_FIELDS["trades_safety"]

    soc = str(onet_soc_code or "").strip()
    prefix2 = soc[:2]
    prefix4 = soc[:5]  # e.g. '13-20', '41-30', '53-20'

    if prefix4 in {"13-20", "41-30"} or soc.startswith(("13-1111", "15-2011")):
        return CAREER_FIELDS["finance"]
    if prefix2 == "15":
        return CAREER_FIELDS["tech"]
    if prefix2 == "17":
        return CAREER_FIELDS["engineering"]
    if prefix2 in {"29", "31"}:
        return CAREER_FIELDS["healthcare"]
    if prefix2 == "19":
        return CAREER_FIELDS["science"]
    if prefix2 in {"11", "13", "21", "23", "25", "27", "41", "43"}:
        return CAREER_FIELDS["business_ops"]
    if prefix2 in {"33", "35", "37", "39", "45", "47", "49", "51", "53", "55"}:
        return CAREER_FIELDS["trades_safety"]

    # Fallback when no O*NET code is present: map via legacy domain resolver
    try:
        from app.services.recommendation_service import resolve_career_domain_standard
        dom = resolve_career_domain_standard(career_title, onet_soc_code)
        domain_to_field = {
            "tech": "tech",
            "protective_service": "trades_safety",
            "engineering": "engineering",
            "healthcare": "healthcare",
            "science": "science",
            "business_finance": "finance",
            "business_admin": "business_ops",
            "trades_industrial": "trades_safety",
            "transportation": "trades_safety",
        }
        mapped = domain_to_field.get(dom, "business_ops")
        return CAREER_FIELDS[mapped]
    except Exception:
        return CAREER_FIELDS["business_ops"]

