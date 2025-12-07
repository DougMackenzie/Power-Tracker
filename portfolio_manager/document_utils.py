"""
Document extraction utilities for Critical Path AI agents.
Extracts text from various file formats for milestone update detection.
"""

import PyPDF2
import docx
from pathlib import Path
from typing import Optional
import email


def extract_text_from_file(file_path: str) -> Optional[str]:
    """
    Extract text content from various file formats.
    
    Args:
        file_path: Path to file to extract text from
        
    Returns:
        Extracted text or None if extraction failed
        
    Supported formats:
        - PDF (.pdf)
        - Word (.docx)
        - Text (.txt, .md)
        - Email (.eml, .msg)
    """
    try:
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == '.pdf':
            return _extract_from_pdf(path)
        elif ext == '.docx':
            return _extract_from_docx(path)
        elif ext in ['.txt', '.md', '.text']:
            return _extract_from_text(path)
        elif ext in ['.eml', '.msg']:
            return _extract_from_email(path)
        else:
            print(f"Unsupported file type: {ext}")
            return None
            
    except Exception as e:
        print(f"Error extracting from {file_path}: {e}")
        return None


def _extract_from_pdf(path: Path) -> str:
    """Extract text from PDF file."""
    text = ''
    with open(path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + '\n'
    return text


def _extract_from_docx(path: Path) -> str:
    """Extract text from Word document."""
    doc = docx.Document(path)
    return '\n'.join([para.text for para in doc.paragraphs])


def _extract_from_text(path: Path) -> str:
    """Extract text from plain text file."""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def _extract_from_email(path: Path) -> str:
    """Extract text from email file (.eml)."""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        msg = email.message_from_file(f)
        
        # Extract subject and body
        subject = msg.get('Subject', '')
        body = ''
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return f"Subject: {subject}\n\n{body}"
