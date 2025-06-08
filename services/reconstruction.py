import re
import json
import base64
from typing import Dict, List, Optional
from utils.postprocessing_utils import markdown_table_to_tiptap
import logging

logger = logging.getLogger(__name__)

class DigitalPDFReconstructor:
    def __init__(self):
        self.default_font = "Times-Roman"
        self.default_size = 12
        self.header_threshold = 100  # Y-position threshold for headers
        self.footer_threshold = 700  # Y-position threshold for footers
        self.title_size = 16
        self.section_size = 14

    def reconstruct_document(self, translated_text: List[Dict], token_map: Dict[str, str], content_metadata: List[Dict]) -> str:
        """
        Reconstructs a digital PDF into TipTap JSON format with proper semantic structure.
        
        Args:
            mapped_data: List of content blocks with metadata from PDF extraction
            
        Returns:
            JSON string representing the TipTap document structure
        """
        if not translated_text:
            return self._empty_document()
        
        mapped_data = self.map_translated_content(translated_text, token_map, content_metadata)   
        # print('mapped_data', mapped_data)
        tiptap_content = {
            "type": "doc",
            "content": []
        }

        for block in mapped_data:
            block_type = block.get("type")
            
            if block_type == "image":
                self._process_image_block(block, tiptap_content)
            elif block_type == "table":
                self._process_table_block(block, tiptap_content)
            else:
                self._process_text_block(block, tiptap_content)

        return json.dumps(tiptap_content, ensure_ascii=False, indent=2)

    def _empty_document(self) -> str:
        """Return an empty TipTap document structure"""
        return json.dumps({
            "type": "doc",
            "content": [{
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": ""
                }]
            }]
        })

    def map_translated_content( 
    self,
    translated_text: str,
    token_map: Dict[str, str],
    extracted_content: List[Dict]
) -> List[Dict]:
        """
        Maps translated text back to structured content using delimiters like [BLOCK_0001],
        [TABLE_0_1], etc., and replaces the original values with translated ones.
        """

        # Step 1: Restore token placeholders
        for token_key, original_value in token_map.items():
            translated_text = translated_text.replace(token_key, original_value)

        # Step 2: Split using delimiter pattern
        pattern = r"(\[(?:BLOCK_\d{4}|IMAGE_\d+|TABLE_\d+_\d+)\])"
        parts = re.split(pattern, translated_text)

        # Step 3: Build lookup table
        content_lookup = {item["id"]: item for item in extracted_content if "id" in item}

        # Step 4: Iterate through parts and reassign
        current_id = None
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if re.match(r"^\[(BLOCK_\d{4}|IMAGE_\d+|TABLE_\d+_\d+)\]$", part):
                current_id = part.strip("[]")
            elif current_id:
                item = content_lookup.get(current_id)
                if item:
                    if current_id.startswith("BLOCK_"):
                        item["text"] = part
                    elif current_id.startswith("TABLE_"):
                        item["table_data"] = part
                current_id = None  # only reset if content was found

        # Step 5: Return in original order
        return [content_lookup[item["id"]] for item in extracted_content if "id" in item]


    def _process_image_block(self, block: Dict, document: Dict):
        """Process image blocks into TipTap image nodes"""
        try:
            image_data = block.get("content", "")
            if not image_data:
                return

            document["content"].append({
                "type": "image",
                "attrs": {
                    "src": f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8')}",
                    "alt": block.get("alt", ""),
                    "title": block.get("title", ""),
                    "width": block.get("width"),
                    "height": block.get("height")
                }
            })
        except Exception as e:
            print(f"Failed to process image block: {e}")

    def _process_table_block(self, block: Dict, document: Dict):
        """Process table blocks into TipTap table nodes"""
        table_data = block.get("table_data", "")
        if not table_data:
            return

        table_node = markdown_table_to_tiptap(
            table_data,
            default_font=self.default_font,
            default_size=self.default_size
        )
        
        if table_node:
            document["content"].append(table_node)

    def _process_text_block(self, block: Dict, document: Dict):
        """Process text blocks with semantic formatting"""
        text = block.get("text", "").strip()
        if not text:
            return

        font = block.get("font", self.default_font)
        size = block.get("size", self.default_size)
        bbox = block.get("bbox", (0, 0, 0, 0))

        # Determine text styling
        text_marks = self._get_text_marks(font, size)
        text_node = {"type": "text", "text": text, "marks": text_marks}

        # Determine block type based on heuristics
        block_type = self._determine_block_type(text, font, size, bbox)
        
        if block_type == "title":
            document["content"].append({
                "type": "heading",
                "attrs": {"level": 1},
                "content": [text_node]  
            })
        elif block_type == "section":
            document["content"].append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [text_node] 
            })
        elif block_type == "header":
            document["content"].append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [text_node]
            })
        elif block_type == "footer":
            document["content"].append({
                "type": "paragraph",
                "attrs": {"class": "footer"},
                "content": [text_node]
            })
        elif block_type == "list":
            self._add_list_item(text_node, document)
        else:
            document["content"].append({
                "type": "paragraph",
                "content": [text_node] 
            })

    def _get_text_marks(self, font: str, size: int) -> List[Dict]:
        """Generate text styling marks based on font attributes"""
        marks = []
        
        if "bold" in font.lower():
            marks.append({"type": "bold"})
        if "italic" in font.lower():
            marks.append({"type": "italic"})
        if "underline" in font.lower():
            marks.append({"type": "underline"})
            
        marks.append({
            "type": "textStyle",
            "attrs": {
                "fontFamily": font,
                "fontSize": f"{size}px"
            }
        })
        
        return marks

    def _determine_block_type(self, text: str, font: str, size: int, bbox: tuple) -> str:
        """Determine the semantic type of a text block"""
        is_bold = "bold" in font.lower()
        is_large = size >= self.title_size
        is_medium = size >= self.section_size
        is_header = bbox[1] < self.header_threshold
        is_footer = bbox[1] > self.footer_threshold
        is_list = bool(re.match(r"^(\-|\•|\d+\.)\s+", text))

        if is_large and is_bold:
            return "title"
        elif is_medium and is_bold:
            return "section"
        elif is_header:
            return "header"
        elif is_footer:
            return "footer"
        elif is_list:
            return "list"
        return "paragraph"

    def _add_list_item(self, text_node: Dict, document: Dict):
        """Add a list item to the document, creating list structure if needed"""
        list_item = {
            "type": "listItem",
            "content": [{
                "type": "paragraph",
                "content": [text_node]
            }]
        }
        
        # Check if we should append to existing list
        if document["content"] and document["content"][-1]["type"] in ["bulletList", "orderedList"]:
            document["content"][-1]["content"].append(list_item)
        else:
            list_type = "bulletList" if re.match(r"^(\-|\•)\s+", text_node["text"]) else "orderedList"
            document["content"].append({
                "type": list_type,
                "content": [list_item]
            })

# ------------------------------------------------------------
import json
from typing import List, Dict, Optional

class ScannedPDFReconstructor:
    def __init__(self):
        self.default_heading_classes = {
            1: "text-xl font-bold text-center my-4",
            2: "text-xl font-bold text-center my-4",
            3: "text-xl font-bold text-center my-4"
        }
        self.footer_class = "text-sm text-gray-500 text-center border-t border-gray-300 pt-2 mt-4"
        self.supported_tags = {
            "title": self._create_heading,
            "section-header": self._create_heading,
            "list-item": self._create_list_item,
            "page-header": self._create_page_header,
            "page-footer": self._create_page_footer,
            "picture": self._handle_picture
        }

    def reconstruct_document(self, translated_data: List[Dict], token_map: Dict[str, str]) -> Optional[str]:
        """
        Reconstructs scanned PDF content into TipTap JSON format.
        
        Args:
            translated_data: List of dictionaries with 'text' and 'label' keys
            
        Returns:
            JSON string representing the TipTap document or None if input is invalid
        """   
        translated_data = self.map_back_tags(translated_data, token_map)

        tiptap_content = {
            "type": "doc",
            "content": []
        }

        for item in translated_data:
            try:
                text = item.get("text", "").strip()
                tag = item.get("label", "").lower().strip()
                
                if not text:
                    continue

                processor = self.supported_tags.get(tag, self._create_paragraph)
                processor(text, tag, tiptap_content)

            except Exception as e:
                print(f"Error processing item {item}: {str(e)}")
                continue

        return tiptap_content

    def map_back_tags(self, translated_text: str, token_map: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Extracts labeled segments from translated text and restores original tokens.
        
        Args:
            translated_text: Text containing XML-style tagged segments
            token_map: Mapping of tokens to original values
            
        Returns:
            List of dictionaries with 'label' and 'text' for each tagged segment
        """
        # Restore original values first
        for token_key, original_value in token_map.items():
            translated_text = translated_text.replace(token_key, original_value)

        # Find all tagged segments
        tagged_segments = re.finditer(
            r"<([^>]+)>(.*?)</\1>", 
            translated_text, 
            re.DOTALL
        )

        return [
            {
                "label": match.group(1),
                "text": match.group(2).strip()
            }
            for match in tagged_segments
            if match.group(2).strip()  # Skip empty content
        ]
    def _create_heading(self, text: str, tag: str, document: Dict) -> None:
        """Create heading node based on tag type"""
        level = 1 if tag == "title" else 2
        document["content"].append({
            "type": "heading",
            "attrs": {
                "level": level,
                "class": self.default_heading_classes.get(level, "")
            },
            "content": [{"type": "text", "text": text}]
        })

    def _create_list_item(self, text: str, tag: str, document: Dict) -> None:
        """Create or append to a list structure"""
        list_item = {
            "type": "listItem",
            "content": [{
                "type": "paragraph", 
                "content": [{"type": "text", "text": text}]
            }]
        }

        # Append to existing list if available
        if (document["content"] and 
            document["content"][-1]["type"] == "bulletList"):
            document["content"][-1]["content"].append(list_item)
        else:
            document["content"].append({
                "type": "bulletList",
                "content": [list_item]
            })

    def _create_page_header(self, text: str, tag: str, document: Dict) -> None:
        """Create page header with specific styling"""
        document["content"].append({
            "type": "heading",
            "attrs": {
                "level": 3,
                "class": self.default_heading_classes[3]
            },
            "content": [{"type": "text", "text": text}]
        })

    def _create_page_footer(self, text: str, tag: str, document: Dict) -> None:
        """Create styled page footer"""
        document["content"].append({
            "type": "paragraph",
            "attrs": {"class": self.footer_class},
            "content": [{"type": "text", "text": text}]
        })

    def _handle_picture(self, text: str, tag: str, document: Dict) -> None:
        """Placeholder for future image handling"""
        pass

    def _create_paragraph(self, text: str, tag: str, document: Dict) -> None:
        """Default paragraph creation"""
        document["content"].append({
            "type": "paragraph",
            "content": [{"type": "text", "text": text}]
        })
