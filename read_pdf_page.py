from pypdf import PdfReader

reader = PdfReader("Power Research Framework.pdf")
# Page 27 is index 26
page = reader.pages[26]
print(page.extract_text())
