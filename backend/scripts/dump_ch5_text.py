import docx

doc_path = r"C:\Users\PC\OneDrive\Desktop\Nota Bene\career-mentor\management\Doc Refs\Macklee_Nderitu_Gitonga_168000 (8).docx"
doc = docx.Document(doc_path)

output_path = "backend/data/ch5_extracted_raw.txt"
with open(output_path, "w", encoding="utf-8") as out:
    for i in range(309, min(len(doc.paragraphs), 585)):
        p = doc.paragraphs[i]
        txt = p.text.strip()
        if txt:
            out.write(f"[{p.style.name}] {txt}\n")

print("Saved raw Chapter 5 text to backend/data/ch5_extracted_raw.txt")
