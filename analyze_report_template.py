from pypdf import PdfReader

reader = PdfReader("diagnostic_report.pdf")
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"

print(text)
