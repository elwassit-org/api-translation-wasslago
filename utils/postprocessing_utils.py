
import re
import json
import os
from config import settings
from typing import Dict, Optional

def markdown_table_to_tiptap(
    markdown_table: str,
    default_font: str = "Times-Roman",
    default_size: int = 12,
    header_bold: bool = True,
    min_columns: int = 1
) -> Optional[Dict]:
    """
    Convert a markdown table to TipTap table structure with configurable styling.
    
    Args:
        markdown_table: Markdown-formatted table string
        default_font: Default font family for table cells
        default_size: Default font size in pixels
        header_bold: Whether to bold header text
        min_columns: Minimum number of columns required to process table
        
    Returns:
        TipTap JSON structure or None if input is invalid
    """
    # Validate input and pre-process lines
    if not markdown_table or not isinstance(markdown_table, str):
        return None
        
    lines = [
        line.strip() 
        for line in markdown_table.split('\n') 
        if line.strip() and not re.fullmatch(r'^[\|\:\-\s]+$', line)
    ]
    
    if len(lines) < 2:  # Need at least header and one data row
        return None

    # Parse headers
    try:
        headers = [h.strip() for h in lines[0].strip('|').split('|')]
        if len(headers) < min_columns:
            return None
    except (AttributeError, IndexError):
        return None

    # Initialize table structure
    table_structure = {
        "type": "table",
        "content": []
    }

    # Helper function to create cell content
    def create_cell_content(text: str, is_header: bool = False) -> Dict:
        """Generate standardized cell content with styling"""
        marks = [{
            "type": "textStyle", 
            "attrs": {
                "fontFamily": default_font,
                "fontSize": f"{default_size}px"
            }
        }]
        
        if is_header and header_bold:
            marks.append({"type": "bold"})
            
        return {
            "type": "paragraph",
            "content": [{
                "type": "text",
                "text": text,
                "marks": marks
            }]
        }

    # Process header row
    header_row = {
        "type": "tableRow",
        "content": []
    }
    
    for header in headers:
        header_row["content"].append({
            "type": "tableHeader",
            "content": [create_cell_content(header, is_header=True)]
        })
    
    table_structure["content"].append(header_row)

    # Process data rows
    for line in lines[1:]:
        try:
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) != len(headers):
                continue
                
            row = {
                "type": "tableRow",
                "content": []
            }
            
            for cell in cells:
                row["content"].append({
                    "type": "tableCell",
                    "content": [create_cell_content(cell)]
                })
            
            table_structure["content"].append(row)
            
        except (AttributeError, IndexError):
            continue  # Skip malformed rows

    return table_structure if len(table_structure["content"]) > 1 else None