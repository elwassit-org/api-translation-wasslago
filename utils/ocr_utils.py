# Optional numpy import
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False
    print("Warning: numpy not available - some OCR features may be limited")

from typing import List, Tuple
from config import settings
from pdf2image import convert_from_path

def box_inclusion(ocr_box: Tuple, yolo_box: Tuple, inclusion_threshold: float =0.5)-> bool:
    """
    Check if the OCR bounding box is sufficiently contained within the YOLO bounding box.
    """
    x_min1, y_min1, x_max1, y_max1 = ocr_box
    x_min2, y_min2, x_max2, y_max2 = yolo_box

    # Compute intersection
    x_min_inter = max(x_min1, x_min2)
    y_min_inter = max(y_min1, y_min2)
    x_max_inter = min(x_max1, x_max2)
    y_max_inter = min(y_max1, y_max2)

    inter_area = max(0, x_max_inter - x_min_inter) * max(0, y_max_inter - y_min_inter)

    # OCR box area
    ocr_area = (x_max1 - x_min1) * (y_max1 - y_min1)

    # Check if the OCR box is sufficiently inside the YOLO box
    return inter_area / ocr_area >= inclusion_threshold if ocr_area > 0 else False

def format_ocr_results(ocr_results: List) -> List[Tuple]:
        """Convert OCR results to standardized format"""
        formatted = []
        for result in ocr_results:
            box, (text, confidence) = result
            box_array = np.array(box)
            x_min, y_min = box_array.min(axis=0)
            x_max, y_max = box_array.max(axis=0)
            formatted.append(((x_min, y_min, x_max, y_max), text, confidence))
        return formatted

def insert_tags(mapped_text):
    """
    Wraps OCR text in XML-like tags based on their detected layout label.
    """
    try:
        tagged_text = []

        for item in mapped_text:
            text = item["text"]
            label = item["label"]
            if label and text.strip():  # Avoid empty text
                tagged_text.append(f"<{label}>{text}</{label}>")
            else:
                tagged_text.append(text)  # Preserve non-labeled text

        return " ".join(tagged_text)  # Create the full plain text

    except Exception as e:
        print(f"Error during tag insertion: {e}")
        return ""
    
def convert_to_images(pdf_path):
    """
    Convert PDF to images with robust Poppler path handling
    """
    from azure_config import azure_config
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get the appropriate Poppler path
        poppler_path = azure_config.get_poppler_path()
        
        # Log Poppler configuration for debugging
        logger.info(f"Using Poppler path: {poppler_path}")
        logger.info(f"Environment: {'Azure' if azure_config.is_azure else 'Local'}")
        
        # Try to convert with the configured Poppler path
        try:
            images = convert_from_path(pdf_path, dpi=200, poppler_path=poppler_path)
        except Exception as e:
            logger.warning(f"Failed with configured Poppler path {poppler_path}: {e}")
            
            # Fallback: try without poppler_path (let pdf2image find it)
            try:
                logger.info("Attempting conversion without explicit Poppler path")
                images = convert_from_path(pdf_path, dpi=200)
            except Exception as e2:
                logger.error(f"Failed without explicit Poppler path: {e2}")
                
                # Final fallback: try system default paths
                fallback_paths = ["/usr/bin", "/usr/local/bin", None]
                for fallback_path in fallback_paths:
                    try:
                        logger.info(f"Trying fallback path: {fallback_path}")
                        if fallback_path:
                            images = convert_from_path(pdf_path, dpi=200, poppler_path=fallback_path)
                        else:
                            images = convert_from_path(pdf_path, dpi=200)
                        break
                    except Exception as e3:
                        logger.warning(f"Fallback path {fallback_path} failed: {e3}")
                        continue
                else:
                    raise Exception("All Poppler path attempts failed")

        # Save images as PNG
        img_list = []
        for i, image in enumerate(images):
            img_path = f"{settings.temp_folder}/page_{i+1}.png"
            image.save(img_path, "PNG")
            img_list.append(img_path)

        logger.info(f"Successfully converted PDF to {len(img_list)} images")
        return img_list
        
    except Exception as e:
        logger.error(f"PDF to image conversion failed: {e}")
        raise Exception(f"Failed to convert PDF to images: {e}")