from pypdf import PdfReader
import re

reader = PdfReader("Power Research Framework.pdf")
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"

# Search for Supply related keywords
matches = re.findall(r"Supply.*GW", text, re.IGNORECASE)
print("--- Matches for 'Supply.*GW' ---")
for m in matches:
    print(m)

# Print text around "Supply" to find scenarios
print("\n--- Context around 'Supply' ---")
indices = [m.start() for m in re.finditer(r"Supply", text, re.IGNORECASE)]
for i in indices:
    start = max(0, i - 100)
    end = min(len(text), i + 300)
    print(f"...{text[start:end].replace(chr(10), ' ')}...")
