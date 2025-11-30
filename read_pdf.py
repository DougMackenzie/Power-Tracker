from pypdf import PdfReader

reader = PdfReader("Power Research Framework.pdf")
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"

print(text)
