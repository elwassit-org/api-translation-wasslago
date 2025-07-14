
from typing import List, Tuple, Dict, Union
from pathlib import Path
import fitz
import pdfplumber

# Optional imports for data processing
try:
    import pandas as pd
    import numpy as np
    HAS_DATA_PROCESSING = True
except ImportError:
    # Create dummy objects if packages not available
    pd = None
    np = None
    HAS_DATA_PROCESSING = False
    print("Warning: pandas/numpy not available - some features may be limited")

from utils.ocr_utils import convert_to_images, format_ocr_results, box_inclusion, insert_tags
from config import settings

import fitz
import pdfplumber
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Union
import logging

logger = logging.getLogger(__name__)

class DigitalPDFExtractor:
    def __init__(self):
        self.image_counter = 1  # Tracks image IDs across pages
        self.block_counter = 1  # Unique block counter across pages

    def extract_text_and_images(self, pdf_path: Union[str, Path]) -> Tuple[str, List[Dict]]:
        """
        Main method to extract structured content from a digital PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple containing:
            - Plain text with content markers
            - List of structured content items with metadata
        """
        extracted_content = []
        plain_text_parts = []
        self.block_counter = 1  # Reset at the start of a new document
        
        try:
            with fitz.open(str(pdf_path)) as doc:
                for page_index, page in enumerate(doc):
                    logger.info(f"Processing page {page_index + 1}/{len(doc)}")
                    
                    # Extract text blocks and images
                    text_blocks = self._extract_text_blocks(page)
                    image_blocks = self._extract_images_from_page(doc, page)
                    
                    # Combine and sort page items
                    page_items = text_blocks + image_blocks
                    page_items.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
                    extracted_content.extend(page_items)
                    
                    # Build plain text representation
                    text_parts = []
                    for item in page_items:
                        text_parts.append(f"[{item['id']}] {item['text']}" if item["type"] == "text" else f"[{item['id']}]")
                    plain_text_parts.extend(text_parts)
                    
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            return "", []
            
        return " ".join(plain_text_parts).strip(), extracted_content

    def extract_tables(self, pdf_path: Union[str, Path]) -> Tuple[str, List[Dict]]:
        """
        Extract tables from PDF using pdfplumber.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple containing:
            - Plain text representation of tables
            - List of table items with metadata
        """
        extracted_tables = []
        table_texts = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        tables = page.extract_tables()
                        for table_idx, table in enumerate(tables):
                            if not table:
                                continue

                            try:
                                df = pd.DataFrame(table)
                                table_str = df.to_markdown(index=False)
                            except Exception as e:
                                print(f"Failed to parse table {table_idx} on page {page_num + 1}: {e}")
                                continue

                            table_id = f"TABLE_{page_num}_{table_idx}"
                            extracted_tables.append({
                                "id": table_id,
                                "type": "table",
                                "table_data": table_str
                            })
                            table_texts.append(f"[{table_id}] {table_str}")
                    except Exception as e:
                        print(f"Error processing tables on page {page_num + 1}: {e}")
                        continue

        except Exception as e:
            print(f"Failed to open PDF with pdfplumber: {e}")
            return "", []

        # ✅ Add this return to ensure proper result
        return "\n\n".join(table_texts), extracted_tables

        

    def extract_text_digital_pdf(self, file_path: Path, from_lang: str) -> Tuple[str, List[Dict]]:
        """
        Complete digital PDF extraction including text, images and tables.
        """
        logger.info("Starting digital PDF extraction process")
        
        try:
            # Extract text and images
            plain_text, extracted_content = self.extract_text_and_images(file_path)
            
            # Extract tables
            tables_text, extracted_tables = self.extract_tables(file_path)
            
            # Combine results
            full_text = f"{plain_text} {tables_text}".strip()
            extracted_content += extracted_tables
            
            return full_text, extracted_content
            
        except Exception as e:
            logger.error(f"Critical error during digital PDF extraction: {e}")
            return "", []

    # -------------------- Helper Methods --------------------

    def _extract_text_blocks(self, page) -> List[Dict]:
        """Extract structured text blocks from a PDF page."""
        page_items = []

        try:
            blocks = page.get_text("dict").get("blocks", [])
        except Exception as e:
            logger.warning(f"Error extracting text blocks: {e}")
            return []

        for block in blocks:
            try:
                if "lines" not in block or not block["lines"]:
                    continue

                block_text = " ".join(span["text"] for line in block["lines"] for span in line["spans"]).strip()
                if not block_text:
                    continue

                # Use global counter
                page_items.append(self._create_text_block(block, self.block_counter, block_text))
                self.block_counter += 1  # Increment globally

            except Exception as e:
                logger.warning(f"Error processing text block: {e}")
                continue

        return page_items

    def _create_text_block(self, block: Dict, counter: int, text: str) -> Dict:
        """Create structured text block dictionary."""
        first_span = block["lines"][0]["spans"][0]
        return {
            "id": f"BLOCK_{counter:04d}",
            "type": "text",
            "text": text,
            "font": first_span.get("font"),
            "size": first_span.get("size"),
            "bbox": block["bbox"]
        }

    def _extract_images_from_page(self, doc, page) -> List[Dict]:
        """Extract images from a PDF page."""
        image_items = []
        
        try:
            images = page.get_images(full=True)
        except Exception as e:
            self.logger.warning(f"Error retrieving images: {e}")
            return []
            
        for img in images:
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue
                    
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                    
                image_items.append({
                    "id": f"IMAGE_{self.image_counter}",
                    "type": "image",
                    "content": base_image["image"],
                    "bbox": rects[0]
                })
                self.image_counter += 1
                
            except Exception as e:
                logger.warning(f"Error extracting image: {e}")
                continue
                
        return image_items

# ---------------------------------------
import os
import torch
import paddle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging
from ultralytics import YOLO
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

class ScannedPDFOCRExtractor:
    def __init__(self, source_lang: str):
        """
        Initialize the OCR extractor with YOLO model path and temporary directory.
        
        Args:
            yolo_model_path: Path to YOLO text classification model
            temp_dir: Directory for temporary image files
        """
        
        self.yolo_model_path = settings.yolo_text_classification
        self.temp_dir = settings.temp_folder
        self.device = self._init_device()
        self.ocr_engine = None
        self.yolo_model = None
        self._initialize_engines(source_lang)
        
        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)

    def extract_text(self, file_path: Path) -> str:
        """
        Main method to extract text from scanned PDF using OCR and layout analysis.
        
        Args:
            file_path: Path to PDF file
            source_lang: Source language for OCR
            
        Returns:
            Extracted text with semantic tags
        """
        try:            # Convert PDF to images
            img_list = convert_to_images(file_path)
            if not img_list:
                logger.error("No images generated from PDF")
                return ""
            
            mapped_text = []
            
            for img_path in img_list:
                try:
                    # Process each page image
                    # Run OCR
                    ocr_results = self.ocr_engine.ocr(img_path, cls=True)[0]
                    ocr_boxes = format_ocr_results(ocr_results)
                    
                    # Run layout detection (if YOLO model is available)
                    if self.yolo_model is not None:
                        yolo_results = self.yolo_model(
                            img_path,
                            conf=0.3,
                            iou=0.5,
                            imgsz=640,
                            verbose=False
                        )
                        # Map text to layout labels using YOLO
                        page_text = self._map_text_to_labels(ocr_boxes, yolo_results)
                    else:
                        # Fallback: create simple text structure without YOLO classification
                        page_text = [{"text": box["text"], "label": "text", "bbox": box["bbox"]} 
                                   for box in ocr_boxes if box["text"].strip()]
                    
                    mapped_text.extend(page_text)
                    
                except Exception as e:
                    logger.error(f"Error processing image {img_path}: {str(e)}")
                    continue            # Convert to final tagged text
            return insert_tags(mapped_text)
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return ""
        finally:
            self._cleanup_temp_files(img_list)

    def _initialize_engines(self, source_lang: str) -> None:
        """Initialize OCR and YOLO models if not already initialized"""
        if self.ocr_engine is None:
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang=source_lang,
                show_log=False,
                use_gpu=paddle.get_device() == 'gpu',
                rec_algorithm='SVTR_LCNet'
            )
        
        if self.yolo_model is None:
            if not os.path.exists(self.yolo_model_path):
                logger.warning(f"YOLO model not found at {self.yolo_model_path}. Text classification will be disabled.")
                return
            
            try:
                self.yolo_model = YOLO(self.yolo_model_path)
                self.yolo_model.to(self.device)
                self.yolo_model.fuse()
                logger.info(f"YOLO model loaded successfully from {self.yolo_model_path}")
            except Exception as e:
                logger.error(f"Failed to load YOLO model: {e}")
                self.yolo_model = None
        

    def _init_device(self) -> str:
        """Initialize and return the best available device"""
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if device == 'cuda' and not paddle.is_compiled_with_cuda():
            logger.warning("PaddleOCR not compiled with CUDA support")
        return device

    def _map_text_to_labels(self, ocr_boxes: List, yolo_results) -> List[Dict]:
        """Map OCR text to YOLO-detected layout labels"""
        try:
            yolo_boxes = yolo_results.boxes.xyxy.cpu().numpy()
            yolo_classes = yolo_results.boxes.cls.cpu().numpy()
            yolo_names = yolo_results.names
            
            # Sort YOLO boxes in reading order
            sorted_indices = np.lexsort((yolo_boxes[:, 0], yolo_boxes[:, 1]))
            sorted_yolo = [(yolo_boxes[i], yolo_classes[i]) for i in sorted_indices]
            
            mapped_results = []
            unmatched_ocr = []
            
            for yolo_box, yolo_class in sorted_yolo:
                assigned_texts = []
                yolo_box_tuple = tuple(yolo_box)
                
                for ocr_box, text, _ in ocr_boxes:
                    if box_inclusion(ocr_box, yolo_box_tuple):
                        assigned_texts.append(text)
                
                if assigned_texts:
                    mapped_results.append({
                        "label": yolo_names[int(yolo_class)],
                        "text": " ".join(assigned_texts),
                        "bbox": yolo_box_tuple
                    })
            
            # Find unmatched OCR texts
            for ocr_box, text, _ in ocr_boxes:
                if not any(box_inclusion(ocr_box, yolo_box) 
                          for yolo_box, _ in sorted_yolo):
                    unmatched_ocr.append({
                        "text": text,
                        "bbox": ocr_box,
                        "label": "Unclassified"
                    })
            
            return mapped_results + unmatched_ocr
            
        except Exception as e:
            logger.error(f"Text-to-label mapping failed: {str(e)}")
            return []

    def _cleanup_temp_files(self, file_paths: List[str]) -> None:
        """Clean up temporary image files"""
        if not file_paths:
            return
            
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {path}: {str(e)}")

# def extract_text_ocr(file_path: Path, source_lang: str, yolo_model_path: Path) -> str:
#     """
#     Optimized main OCR extraction function with:
#     - Proper resource management
#     - Error handling
#     - Performance monitoring
#     """
#     logger.info(f"Starting OCR extraction for {file_path}")
    
#     try:
#         processor = OCRProcessor(source_lang, yolo_model_path)
#         return processor.process_pdf(file_path)
        
#     except Exception as e:
#         logger.error(f"OCR extraction failed: {str(e)}")
#         raise OCRProcessingError(f"Failed to extract text: {str(e)}")

# class OCRProcessingError(Exception):
#     pass