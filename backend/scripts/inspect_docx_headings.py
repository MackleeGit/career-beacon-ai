import docx

doc_path = r"C:\Users\PC\OneDrive\Desktop\Nota Bene\career-mentor\management\Doc Refs\Macklee_Nderitu_Gitonga_168000 (8).docx"
doc = docx.Document(doc_path)

for i in range(308, min(len(doc.paragraphs), 585)):
    p = doc.paragraphs[i]
    txt = p.text.strip()
    if txt:
        if p.style.name.startswith("Heading") or any(txt.startswith(f"5.{j}") for j in range(1, 10)):
            print(f"\n[{p.style.name}] {txt}")
        elif len(txt) < 80 and any(txt.startswith(k) for k in ["Table 5.", "Figure 5."]):
            print(f"  -> {txt}")
