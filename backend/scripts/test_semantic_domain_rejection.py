import sys
import asyncio
sys.path.insert(0, "backend")

from app.services.content_service import ContentService

async def main():
    cs = ContentService()
    
    # 1. Test learner career domain
    learner_domain = await cs.resolve_career_domain("Secretary and Administrative Assistant", "Processing Incoming Mail")
    print(f"Learner Domain: {learner_domain}")
    
    # 2. Test candidate textbook domain
    unix_domain = await cs.resolve_career_domain("Guide to Unix/Explanations/Mail Server Overview", "A mail transfer agent transfers electronic mail using SMTP, sendmail, postfix.")
    print(f"Unix Mail Server Domain: {unix_domain}")
    
    office_domain = await cs.resolve_career_domain("Business correspondence and office mail handling", "Sorting incoming postal letters, routing packages, distributing departmental memos.")
    print(f"Office Mail Domain: {office_domain}")
    
    match_unix = (learner_domain == unix_domain)
    match_office = (learner_domain == office_domain)
    print(f"Unix matches Learner? {match_unix}")
    print(f"Office matches Learner? {match_office}")

if __name__ == "__main__":
    asyncio.run(main())

