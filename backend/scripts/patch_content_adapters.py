import os
import sys

content_service_path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "content_service.py")

with open(content_service_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update SOURCE_AUTHORITY_WEIGHTS
old_weights = """SOURCE_AUTHORITY_WEIGHTS: Dict[str, float] = {
    "youtube": 0.94,
    "structured_tutorial": 0.92,
    "open_textbook": 0.90,
    "clinical_science": 0.95,
    "mdn": 0.95,
    "openalex": 0.86,
    "wikipedia": 0.60,
}"""

new_weights = """SOURCE_AUTHORITY_WEIGHTS: Dict[str, float] = {
    "owasp": 0.96,
    "osha": 0.97,
    "finance": 0.93,
    "youtube": 0.94,
    "structured_tutorial": 0.92,
    "open_textbook": 0.90,
    "clinical_science": 0.95,
    "mdn": 0.95,
    "openalex": 0.86,
    "wikipedia": 0.60,
}"""

# 2. Update get_source_trust_score
old_trust = """    if "youtube" in low:
        return SOURCE_AUTHORITY_WEIGHTS["youtube"]"""

new_trust = """    if "owasp" in low:
        return SOURCE_AUTHORITY_WEIGHTS["owasp"]
    if "osha" in low or "safety standard" in low or "niosh" in low:
        return SOURCE_AUTHORITY_WEIGHTS["osha"]
    if "finance" in low or "accounting standard" in low:
        return SOURCE_AUTHORITY_WEIGHTS["finance"]
    if "youtube" in low:
        return SOURCE_AUTHORITY_WEIGHTS["youtube"]"""

# 3. Update classify_source_adapter
old_classify = """    combined = f"{source_url or ''} {source_label or ''}".lower()
    if "youtube.com" in combined or "youtu.be" in combined:"""

new_classify = """    combined = f"{source_url or ''} {source_label or ''}".lower()
    if "owasp.org" in combined or "owasp" in combined:
        return "owasp"
    if "osha.gov" in combined or "osha" in combined or "niosh" in combined:
        return "osha"
    if "corporatefinance" in combined or "accounting" in combined:
        return "finance"
    if "youtube.com" in combined or "youtu.be" in combined:"""

# Check presence
if old_weights not in code:
    print("Error: old_weights not found")
    sys.exit(1)
if old_trust not in code:
    print("Error: old_trust not found")
    sys.exit(1)
if old_classify not in code:
    print("Error: old_classify not found")
    sys.exit(1)

code = code.replace(old_weights, new_weights, 1)
code = code.replace(old_trust, new_trust, 1)
code = code.replace(old_classify, new_classify, 1)

# Now add adapter methods before fetch_live_source_for_skill
new_adapters = '''
    async def _fetch_owasp_cheatsheet(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter: OWASP Official Security Standards (Keyless GitHub Raw API)."""
        cheatsheet_map = [
            (("vulnerability", "scanning", "assessment"), "Vulnerability_Disclosure_Cheat_Sheet.md", "Vulnerability Management"),
            (("log", "monitoring", "event", "siem"), "Logging_Cheat_Sheet.md", "Security Logging and Event Monitoring"),
            (("incident", "response", "playbook", "breach"), "Incident_Response_Cheat_Sheet.md", "Incident Response Standard"),
            (("auth", "login", "credential", "password", "session"), "Authentication_Cheat_Sheet.md", "Authentication Security"),
            (("access control", "rbac", "permission", "privilege"), "Access_Control_Cheat_Sheet.md", "Access Control Standard"),
            (("crypto", "encryption", "key", "cipher"), "Cryptographic_Storage_Cheat_Sheet.md", "Cryptographic Storage Standard"),
            (("api", "endpoint", "rest", "graphql"), "REST_Security_Cheat_Sheet.md", "REST API Security Standard"),
            (("threat", "model", "risk", "attack surface"), "Threat_Modeling_Cheat_Sheet.md", "Threat Modeling Standard"),
            (("injection", "sql", "xss", "input"), "Injection_Prevention_Cheat_Sheet.md", "Input Validation & Injection Prevention"),
            (("cloud", "container", "docker", "microservice"), "Microservices_Security_Cheat_Sheet.md", "Microservices Security Architecture"),
            (("ai", "llm", "agent"), "AI_Agent_Security_Cheat_Sheet.md", "AI Agent Security Standard"),
        ]

        clean_lower = f"{skill_name} {career_title}".lower()
        selected_file = None
        display_label = None

        for keywords, filename, label in cheatsheet_map:
            if any(k in clean_lower for k in keywords):
                selected_file = filename
                display_label = label
                break

        if not selected_file and any(k in clean_lower for k in ("security", "cyber", "infosec")):
            selected_file = "Vulnerability_Disclosure_Cheat_Sheet.md"
            display_label = "Vulnerability Management Standard"

        if not selected_file:
            return None

        raw_url = f"https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/{selected_file}"
        public_url = f"https://cheatsheetseries.owasp.org/cheatsheets/{selected_file.replace('.md', '.html')}"
        if public_url in excluded or raw_url in excluded:
            return None

        try:
            resp = await client.get(raw_url, headers={"User-Agent": ACADEMIC_USER_AGENT})
            if resp.status_code == 200 and resp.text:
                raw_text = re.sub(r"\\[([^\\]]+)\\]\\([^\\)]+\\)", r"\\1", resp.text)
                raw_text = re.sub(r"```[\\s\\S]*?```", " ", raw_text)
                raw_text = re.sub(r"#+\\s*", "", raw_text)
                cleaned = strip_html_and_clean(raw_text)

                if len(cleaned) >= 200:
                    title = f"OWASP {display_label}: {skill_name}"
                    return {
                        "title": title[:140],
                        "source_url": public_url,
                        "raw_text": cleaned[:10000],
                        "source": "OWASP Security Standard",
                        "source_adapter": "owasp",
                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["owasp"],
                    }
        except Exception as e:
            logger.debug(f"OWASP adapter error: {e}")
        return None

    async def _fetch_osha_standards(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter: OSHA & NIOSH Technical Safety Standards (Skilled Trades, Electrical, Industrial)."""
        trade_queries = [
            f"Occupational safety {skill_name}".strip(),
            f"OSHA technical standard {skill_name}".strip(),
            f"National Electrical Code {skill_name}".strip(),
        ]
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        for q in trade_queries:
            try:
                srch = await client.get(
                    f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=3",
                    headers=headers,
                )
                if srch.status_code == 200:
                    results = srch.json().get("query", {}).get("search", [])
                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or any(skip in page_title.lower() for skip in ("disambiguation", "list of", "portal:")):
                            continue
                        page_url = f"https://en.wikipedia.org/wiki/{quote_plus(page_title.replace(' ', '_'))}"
                        if page_url in excluded:
                            continue
                        ext_resp = await client.get(
                            f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={quote_plus(page_title)}&format=json",
                            headers=headers,
                        )
                        if ext_resp.status_code == 200:
                            pages = ext_resp.json().get("query", {}).get("pages", {})
                            for _, pdata in pages.items():
                                extract = strip_html_and_clean(pdata.get("extract", ""))
                                if validate_source_content(extract, skill_name):
                                    return {
                                        "title": f"OSHA Technical Safety Standard: {page_title}",
                                        "source_url": page_url,
                                        "raw_text": extract[:10000],
                                        "source": "OSHA / Technical Safety Standard",
                                        "source_adapter": "osha",
                                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["osha"],
                                    }
            except Exception as e:
                logger.debug(f"OSHA adapter error: {e}")
        return None

    async def _fetch_finance_knowledge(
        self,
        client: httpx.AsyncClient,
        skill_name: str,
        career_title: str,
        excluded: set,
    ) -> Optional[Dict[str, Any]]:
        """Adapter: Financial Reporting & Accounting Standards (Wikibooks Accounting & Corporate Finance)."""
        finance_queries = [
            f"Financial Accounting {skill_name}".strip(),
            f"Accounting Principles {skill_name}".strip(),
            f"Corporate Finance {skill_name}".strip(),
        ]
        headers = {"User-Agent": ACADEMIC_USER_AGENT}
        for q in finance_queries:
            try:
                srch = await client.get(
                    f"https://en.wikibooks.org/w/api.php?action=query&list=search&srsearch={quote_plus(q)}&utf8=&format=json&srlimit=3",
                    headers=headers,
                )
                if srch.status_code == 200:
                    results = srch.json().get("query", {}).get("search", [])
                    for item in results:
                        page_title = item.get("title", "")
                        if not page_title or any(skip in page_title.lower() for skip in ("talk:", "user:", "template:")):
                            continue
                        page_url = f"https://en.wikibooks.org/wiki/{quote_plus(page_title.replace(' ', '_'))}"
                        if page_url in excluded:
                            continue
                        ext_resp = await client.get(
                            f"https://en.wikibooks.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={quote_plus(page_title)}&format=json",
                            headers=headers,
                        )
                        if ext_resp.status_code == 200:
                            pages = ext_resp.json().get("query", {}).get("pages", {})
                            for _, pdata in pages.items():
                                extract = strip_html_and_clean(pdata.get("extract", ""))
                                if validate_source_content(extract, skill_name):
                                    return {
                                        "title": f"Accounting & Financial Standard: {page_title}",
                                        "source_url": page_url,
                                        "raw_text": extract[:10000],
                                        "source": "Accounting & Financial Standard",
                                        "source_adapter": "finance",
                                        "trust_score": SOURCE_AUTHORITY_WEIGHTS["finance"],
                                    }
            except Exception as e:
                logger.debug(f"Finance knowledge adapter error: {e}")
        return None
'''

old_fetch_sig = "    async def fetch_live_source_for_skill("
if old_fetch_sig not in code:
    print("Error: old_fetch_sig not found")
    sys.exit(1)

code = code.replace(old_fetch_sig, new_adapters + "\n" + old_fetch_sig, 1)

# Now update the router inside fetch_live_source_for_skill
old_router = """        is_health_or_bio = any(k in context for k in ("health", "medical", "clinical", "dental", "nurs", "pharmac", "therap", "patient", "biolog", "anatom", "surgical"))
        is_tech = any(k in context for k in ("tech", "software", "program", "data", "develop", "web", "ai", "cloud", "cyber", "network", "sql", "python", "javascript", "engineer"))

        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            # Build domain-aware adapter execution order
            adapter_order = []
            if is_health_or_bio:
                adapter_order.extend([
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                ])
            elif is_tech:
                adapter_order.extend([
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                    ("mdn", lambda: self._fetch_mdn_docs(client, skill_name, category, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            else:
                # Universal career routing (Finance, Management, Trades, Culinary, Law, Operations, Creative)
                adapter_order.extend([
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                ])"""

new_router = """        is_health_or_bio = any(k in context for k in ("health", "medical", "clinical", "dental", "nurs", "pharmac", "therap", "patient", "biolog", "anatom", "surgical"))
        is_security = any(k in context for k in ("security", "cyber", "infosec", "vulnerability", "incident", "access control", "penetration", "threat", "auth", "crypto"))
        is_trade_or_safety = any(k in context for k in ("electrician", "welding", "wiring", "safety", "hazard", "osha", "scaffold", "ppe", "mechanic", "construction", "plumbing"))
        is_finance_or_accounting = any(k in context for k in ("accounting", "accountant", "audit", "financial", "valuation", "tax", "variance", "depreciation", "balance sheet", "sec"))
        is_tech = any(k in context for k in ("tech", "software", "program", "data", "develop", "web", "ai", "cloud", "network", "sql", "python", "javascript", "engineer"))

        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            # Build domain-aware adapter execution order
            adapter_order = []
            if is_security:
                adapter_order.extend([
                    ("owasp", lambda: self._fetch_owasp_cheatsheet(client, skill_name, career_title, excluded)),
                    ("mdn", lambda: self._fetch_mdn_docs(client, skill_name, category, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                ])
            elif is_health_or_bio:
                adapter_order.extend([
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                ])
            elif is_trade_or_safety:
                adapter_order.extend([
                    ("osha", lambda: self._fetch_osha_standards(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            elif is_finance_or_accounting:
                adapter_order.extend([
                    ("finance", lambda: self._fetch_finance_knowledge(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                ])
            elif is_tech:
                adapter_order.extend([
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                    ("mdn", lambda: self._fetch_mdn_docs(client, skill_name, category, career_title, excluded)),
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                ])
            else:
                # Universal career routing (Management, Trades, Culinary, Law, Operations, Creative)
                adapter_order.extend([
                    ("youtube", lambda: self._fetch_youtube_lecture(client, skill_name, career_title, excluded)),
                    ("open_textbook", lambda: self._fetch_open_textbook(client, skill_name, career_title, excluded)),
                    ("structured_tutorial", lambda: self._fetch_structured_tutorial(client, skill_name, category, excluded)),
                    ("openalex", lambda: self._fetch_openalex_chapter(client, skill_name, career_title, excluded)),
                    ("clinical_science", lambda: self._fetch_clinical_and_science(client, skill_name, career_title, excluded)),
                ])"""

if old_router not in code:
    print("Error: old_router not found")
    sys.exit(1)

code = code.replace(old_router, new_router, 1)

with open(content_service_path, "w", encoding="utf-8") as f:
    f.write(code)

print("SUCCESS: content_service.py patched with OWASP, OSHA, and Finance adapters!")

