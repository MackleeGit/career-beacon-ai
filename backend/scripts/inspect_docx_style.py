import docx

doc_path = r"C:\Users\PC\OneDrive\Desktop\Nota Bene\career-mentor\management\Doc Refs\Macklee_Nderitu_Gitonga_168000 (8).docx"
doc = docx.Document(doc_path)

for p in doc.paragraphs[309:325]:
    if p.text.strip():
        runs_info = [(r.text, r.font.name, r.font.size.pt if r.font.size else None, r.font.bold) for r in p.runs[:3]]
        print(f"Style: {p.style.name} | Text: {p.text[:60]} | Runs: {runs_info}")
