import docx

doc_path = r"C:\Users\PC\OneDrive\Desktop\Nota Bene\career-mentor\management\Doc Refs\Macklee_Nderitu_Gitonga_168000 (8).docx"
doc = docx.Document(doc_path)

print(f"Total tables in doc: {len(doc.tables)}")
for i, t in enumerate(doc.tables):
    rows = len(t.rows)
    cols = len(t.columns)
    first_cell = t.cell(0, 0).text.strip() if rows > 0 and cols > 0 else ""
    print(f"Table {i}: {rows}x{cols} | First cell: {first_cell[:40]}")
