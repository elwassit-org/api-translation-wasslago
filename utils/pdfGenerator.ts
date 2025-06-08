import jsPDF from 'jspdf';
import { PAGINATION_CONSTANTS, getLinesPerPage, getUsablePageHeight } from '../components/translation/paginationUtils';

// Arabic text detection function
function containsArabic(text: string): boolean {
  // Arabic Unicode range: 0600-06FF, 0750-077F, 08A0-08FF, FB50-FDFF, FE70-FEFF
  const arabicPattern = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
  return arabicPattern.test(text);
}

// Function to process Arabic text for better display
function processArabicText(text: string): string {
  // Ensure proper UTF-8 encoding and handle common Arabic display issues
  try {
    // Remove any problematic characters that might cause encoding issues
    let processedText = text
      .replace(/[\u200C-\u200F]/g, '') // Remove zero-width characters
      .replace(/[\uFEFF]/g, ''); // Remove byte order mark
    
    // Try to import and use Arabic reshaping if available
    try {
      // Dynamic import for optional dependency
      const arabicReshaper = require('arabic-reshaper');
      if (arabicReshaper && typeof arabicReshaper.reshape === 'function') {
        processedText = arabicReshaper.reshape(processedText);
      }
    } catch (e) {
      // Arabic reshaper not available, continue with basic processing
    }
    
    // Try to import and use bidirectional text support if available
    try {
      const bidi = require('bidi-js');
      if (bidi && typeof bidi.bidi === 'function') {
        processedText = bidi.bidi(processedText, { dir: 'rtl' });
      }
    } catch (e) {
      // Bidi-js not available, continue with basic processing
    }
    
    // Ensure the text is properly encoded
    return processedText;
  } catch (error) {
    console.warn('Error processing Arabic text:', error);
    return text;
  }
}

// Function to check if jsPDF can render the text properly
function canRenderText(pdf: jsPDF, text: string): boolean {
  try {
    // Try to measure the text - if it fails, the font doesn't support it
    pdf.getTextWidth(text);
    return true;
  } catch (error) {
    return false;
  }
}

interface TextSegment {
  text: string;
  bold?: boolean;
  italic?: boolean;
  fontSize?: number;
  color?: string;
}

interface FormattedContent {
  segments: TextSegment[];
  isNewLine?: boolean;
  isHeading?: boolean;
  headingLevel?: number;
}

/**
 * Extracts formatted content from ProseMirror JSON content
 * Using consistent text measurement for exact pagination matching
 */
function extractFormattedContent(content: any): FormattedContent[] {
  console.log('Extract Formatted Content Debug - Input content:', content);
  console.log('Extract Formatted Content Debug - Content type:', typeof content);
  
  if (!content) {
    console.log('Extract Formatted Content Debug - No content provided, returning empty array');
    return [];
  }
  
  const formattedContent: FormattedContent[] = [];
  
  function traverseNode(node: any): TextSegment[] {
    if (node.type === 'text') {
      const segment: TextSegment = {
        text: node.text || '',
        bold: false,
        italic: false,
        fontSize: 12, // default font size
      };
      
      // Check for marks (formatting)
      if (node.marks && Array.isArray(node.marks)) {
        node.marks.forEach((mark: any) => {
          switch (mark.type) {
            case 'bold':
              segment.bold = true;
              break;
            case 'italic':
              segment.italic = true;
              break;
            case 'textStyle':
              // Handle custom text styles like font size
              if (mark.attrs && mark.attrs.fontSize) {
                segment.fontSize = parseInt(mark.attrs.fontSize) || 12;
              }
              if (mark.attrs && mark.attrs.color) {
                segment.color = mark.attrs.color;
              }
              break;
          }
        });
      }
      
      return [segment];
    }
    
    if (node.content && Array.isArray(node.content)) {
      return node.content.flatMap(traverseNode);
    }
    
    return [];
  }
  
  function processNode(node: any) {
    if (node.type === 'paragraph') {
      const segments = traverseNode(node);
      if (segments.length > 0) {
        formattedContent.push({
          segments,
          isNewLine: true,
        });
      } else {
        // Empty paragraph still takes space
        formattedContent.push({
          segments: [{ text: '', fontSize: 12 }],
          isNewLine: true,
        });
      }
    } else if (node.type === 'heading') {
      const segments = traverseNode(node);
      if (segments.length > 0) {
        // Make headings bold and larger by default
        segments.forEach(segment => {
          segment.bold = true;
          segment.fontSize = Math.max(segment.fontSize || 12, 14 + (6 - (node.attrs?.level || 1)) * 2);
        });
        
        formattedContent.push({
          segments,
          isNewLine: true,
          isHeading: true,
          headingLevel: node.attrs?.level || 1,
        });
      }
    } else if (node.content && Array.isArray(node.content)) {
      node.content.forEach(processNode);
    }
  }
    if (content.content) {
    console.log('Extract Formatted Content Debug - Processing content.content:', content.content);
    content.content.forEach(processNode);
  } else {
    console.log('Extract Formatted Content Debug - No content.content found, checking if content is already an array');
    if (Array.isArray(content)) {
      console.log('Extract Formatted Content Debug - Content is array, processing directly');
      content.forEach(processNode);
    }
  }
  
  console.log('Extract Formatted Content Debug - Final formatted content:', formattedContent);
  console.log('Extract Formatted Content Debug - Final formatted content length:', formattedContent.length);
  
  return formattedContent;
}

/**
 * Converts hex color to RGB values for jsPDF
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

/**
 * Generates a PDF from the translation content with rich formatting
 * Uses consistent pagination calculations matching the editor exactly
 */
export function generateTranslationPDF(content: any, documentTitle: string = 'Translation', filename?: string, originalPageCount?: number): void {
  try {
    console.log('PDF Generator Debug - Received content:', content);
    console.log('PDF Generator Debug - Content type:', typeof content);
    console.log('PDF Generator Debug - Content structure:', JSON.stringify(content, null, 2));
    
    // Extract formatted content from ProseMirror content
    const formattedContent = extractFormattedContent(content);
    
    console.log('PDF Generator Debug - Formatted content:', formattedContent);
    console.log('PDF Generator Debug - Formatted content length:', formattedContent.length);
    
    if (!formattedContent.length) {
      console.error('PDF Generator Error: No formatted content extracted');
      throw new Error('No content available to generate PDF - content extraction failed');
    }
    
    // Create new PDF document
    const pdf = new jsPDF();

    // Set document properties
    pdf.setProperties({
      title: documentTitle,
      creator: 'Translation System',
      author: 'Translator',
    });
      // Page setup - EXACTLY consistent with editor calculations from paginationUtils.ts
    const pageWidth = pdf.internal.pageSize.getWidth(); // ~210mm for A4
    const pageHeight = pdf.internal.pageSize.getHeight(); // ~297mm for A4
    const margin = PAGINATION_CONSTANTS.margin;
    const maxLineWidth = pageWidth - (margin * 2);
    const lineHeight = PAGINATION_CONSTANTS.lineHeight;
    const usableHeight = getUsablePageHeight();
    const linesPerPage = getLinesPerPage();
      let yPosition = margin;
    let currentPage = 1;
    let lineCount = 0;
    
    // Calculate content distribution when original page count is provided
    const shouldRespectOriginalPageCount = originalPageCount && originalPageCount > 0;
    const adjustedLinesPerPage = shouldRespectOriginalPageCount 
      ? Math.floor(linesPerPage * (formattedContent.length / Math.max(1, originalPageCount * linesPerPage)))
      : linesPerPage;
    
    // Helper function to check if we need a new page
    const checkNewPage = (additionalLines: number = 1) => {
      const effectiveLinesPerPage = shouldRespectOriginalPageCount && currentPage < originalPageCount
        ? adjustedLinesPerPage
        : linesPerPage;
        
      if (lineCount + additionalLines > effectiveLinesPerPage) {
        // Don't add more pages than the original if we're syncing
        if (!shouldRespectOriginalPageCount || currentPage < originalPageCount) {
          pdf.addPage();
          currentPage++;
          yPosition = margin;
          lineCount = 0;
          return true;
        }
      }
      return false;
    };
    
    // Start content immediately - no header or date to match editor pagination exactly
    yPosition = margin;
    
    // Process formatted content
    formattedContent.forEach((contentBlock, blockIndex) => {
      // Add extra space before headings
      if (contentBlock.isHeading && blockIndex > 0) {
        checkNewPage(2);
        yPosition += lineHeight;
        lineCount++;
      }
      
      // Process each segment in the content block
      let currentX = margin;
      let blockHeight = 0;
      
      contentBlock.segments.forEach((segment) => {
        if (!segment.text.trim()) return;        // Set font properties - handle Arabic text
        const hasArabic = containsArabic(segment.text);
        const fontStyle = segment.bold && segment.italic ? 'bolditalic' :
                         segment.bold ? 'bold' :
                         segment.italic ? 'italic' : 'normal';
        
        // Use fonts that better support Arabic characters
        if (hasArabic) {
          // Try to use fonts in order of Arabic support
          try {
            // Times has better Arabic support than Helvetica
            pdf.setFont('times', fontStyle);
          } catch (e) {
            try {
              pdf.setFont('courier', fontStyle);
            } catch (e2) {
              // Ultimate fallback
              pdf.setFont('helvetica', fontStyle);
            }
          }
        } else {
          pdf.setFont('helvetica', fontStyle);
        }
        
        const fontSize = segment.fontSize || 12;
        pdf.setFontSize(fontSize);
        
        // Set text color
        if (segment.color) {
          const rgb = hexToRgb(segment.color);
          if (rgb) {
            pdf.setTextColor(rgb.r, rgb.g, rgb.b);
          } else {
            pdf.setTextColor(0, 0, 0);
          }
        } else {
          pdf.setTextColor(0, 0, 0);
        }
          // Split text into lines that fit within the page width
        // Use character-based estimation consistent with editor pagination
        const charsPerLine = PAGINATION_CONSTANTS.charsPerLine;
        const textLines: string[] = [];
        
        // For consistency with editor, estimate line breaks based on character count
        if (segment.text.length <= charsPerLine) {
          textLines.push(segment.text);
        } else {
          // Split long text into estimated lines
          const words = segment.text.split(' ');
          let currentLine = '';
          
          for (const word of words) {
            if ((currentLine + word).length <= charsPerLine) {
              currentLine += (currentLine ? ' ' : '') + word;
            } else {
              if (currentLine) {
                textLines.push(currentLine);
                currentLine = word;
              } else {
                // Word is longer than line, split it
                let remainingWord = word;
                while (remainingWord.length > charsPerLine) {
                  textLines.push(remainingWord.substring(0, charsPerLine));
                  remainingWord = remainingWord.substring(charsPerLine);
                }
                currentLine = remainingWord;
              }
            }
          }
          if (currentLine) {
            textLines.push(currentLine);
          }
        }          textLines.forEach((line: string, lineIndex: number) => {
          // Check if we need a new page before adding this line
          if (checkNewPage()) {
            currentX = margin; // Reset X position on new page
          }
          
          // Process the text for better Arabic support
          let processedLine = hasArabic ? processArabicText(line.trim()) : line.trim();
          
          // Try different approaches for Arabic text rendering
          if (hasArabic) {
            try {
              // First, try with the current font to see if it can render
              if (canRenderText(pdf, processedLine)) {
                pdf.text(processedLine, currentX, yPosition);
              } else {
                // If current font can't render, try alternatives
                const originalFont = pdf.getFont();
                const fonts = ['times', 'courier', 'helvetica'];
                let rendered = false;
                
                for (const fontName of fonts) {
                  try {
                    pdf.setFont(fontName, fontStyle);
                    if (canRenderText(pdf, processedLine)) {
                      pdf.text(processedLine, currentX, yPosition);
                      rendered = true;
                      break;
                    }
                  } catch (e) {
                    continue;
                  }
                }
                
                if (!rendered) {
                  // Fallback: try to encode the text differently
                  try {
                    const fallbackText = processedLine
                      .split('')
                      .map(char => {
                        const code = char.charCodeAt(0);
                        // If it's Arabic, try to use a basic representation
                        if (code >= 0x0600 && code <= 0x06FF) {
                          return char; // Keep original for now
                        }
                        return char;
                      })
                      .join('');
                    
                    pdf.text(fallbackText, currentX, yPosition);
                  } catch (finalError) {
                    // Ultimate fallback: show placeholder text
                    pdf.text('[Arabic Text]', currentX, yPosition);
                    console.warn('Could not render Arabic text, using placeholder');
                  }
                }
              }
            } catch (error) {
              console.error('Error rendering Arabic text:', error);
              pdf.text('[Text Rendering Error]', currentX, yPosition);
            }
          } else {
            // Regular text rendering
            pdf.text(processedLine, currentX, yPosition);
          }
          
          // Move to next line if this isn't the last line of the segment
          if (lineIndex < textLines.length - 1) {
            yPosition += lineHeight;
            lineCount++;
            currentX = margin;
          } else {
            // For the last line, update X position for next segment on same line
            try {
              currentX += pdf.getTextWidth(processedLine) + 2;
            } catch (e) {
              // If getTextWidth fails, use estimated width
              currentX += (processedLine.length * fontSize * 0.6) + 2;
            }
          }
        });
      });
        // Move to next line after each content block (paragraph)
      if (contentBlock.isNewLine) {
        // Use consistent line spacing - just move to next line
        yPosition += lineHeight;
        lineCount++;
        
        // Add minimal extra space for headings only
        if (contentBlock.isHeading) {
          yPosition += lineHeight * 0.5;
          lineCount += 0.5;
        }
      }
    });
    
    // Add page numbers to all pages
    const totalPages = pdf.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      pdf.setPage(i);
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(10);
      pdf.setTextColor(100, 100, 100);
      pdf.text(
        `Page ${i} of ${totalPages}`,
        pageWidth - margin - 30,
        pageHeight - 10
      );
    }    // Save the PDF with dynamic filename or default
    const pdfFilename = filename || 'translation.pdf';
    pdf.save(pdfFilename);
    
    console.log(`PDF generated successfully: ${pdfFilename} (${totalPages} pages)`);
    
  } catch (error) {
    console.error('Error generating PDF:', error);
    throw error;
  }
}
