import fitz  # PyMuPDF
import pandas as pd

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text.append(page.get_text())
    return text

def save_text_to_csv(text, output_csv):
    df = pd.DataFrame(text, columns=["content"])
    df.to_csv(output_csv, index=False)

if __name__ == "__main__":
    pdf_path = "caminho/para/seu/cosmos.pdf"
    output_csv = "data/extracted_text.csv"
    text = extract_text_from_pdf(pdf_path)
    save_text_to_csv(text, output_csv)
    print("Text extraction and preprocessing completed successfully.")