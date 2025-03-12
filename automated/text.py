import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return doc[0].get_text("text")  # Extract text from the first page

pdf_path = "2008_QS_M.pdf"  
extracted_text = extract_text_from_pdf(pdf_path)
print(extracted_text)
