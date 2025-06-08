
import fitz
from pdf2image import convert_from_path
from config import settings

def is_digital_pdf(pdf_path: str, text_threshold: float = 0.9, min_text_length: int = 50) -> bool:

    doc = fitz.open(pdf_path)
    text_pages = 0
    
    for page in doc:
        text = page.get_text("text").strip()
        
        # Only count as text page if substantial content exists
        if len(text) >= min_text_length:
            text_pages += 1
    
    # Consider digital only if most pages contain real text
    digital_ratio = text_pages / len(doc)
    return digital_ratio >= text_threshold


def pdf_to_imgs(pdf_path):

    # Convert PDF to images (one image per page)
    images = convert_from_path(pdf_path, dpi=200, poppler_path=settings.poppler_path)

    # Save images as PNG
    img_list = []
    for i, image in enumerate(images):
        img_path = f"{settings.temp_folder}/page_{i+1}.png"
        image.save(img_path, "PNG")
        img_list.append(img_path)

    return img_list

