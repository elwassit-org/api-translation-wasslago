from services.pdf_extractor import DigitalPDFExtractor, ScannedPDFOCRExtractor
from services.anonymization import TextAnonymizer
from services.translation import TextTranslator
from services.reconstruction import DigitalPDFReconstructor, ScannedPDFReconstructor
from services.websocket_manager import ConnectionManager
from utils.file_utils import is_digital_pdf
import os
import shutil
import asyncio
from pathlib import Path
from config import settings
import logging
import time

logger = logging.getLogger(__name__)

async def process_pdf_pipeline(
    file_path: Path,
    source_lang: str,
    target_lang: str,
    doc_id: str,
    user_id: str,
    manager: ConnectionManager, 
) -> None:
    """
    Complete PDF processing pipeline from extraction to reconstruction.
    """
    pipeline_start_time = time.time()
    step_times = {}
    
    try:
        # Debug logging: Log received parameters
        logger.info(f"=== PIPELINE START ===")
        logger.info(f"Document ID: {doc_id}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Source Language: {source_lang}")
        logger.info(f"Target Language: {target_lang}")
        logger.info(f"File Path: {file_path}")
        print(f"🔍 PIPELINE DEBUG - Received languages: SOURCE={source_lang}, TARGET={target_lang}")
        
        # Step 1: Detect PDF type
        step_start = time.time()
        is_digital = is_digital_pdf(file_path)
        step_times['pdf_type_detection'] = time.time() - step_start
        logger.info(f"PDF Type Detection: {'Digital' if is_digital else 'Scanned'} (took {step_times['pdf_type_detection']:.3f}s)")
        print(f"📄 PDF Type: {'Digital' if is_digital else 'Scanned'} ⏱️ {step_times['pdf_type_detection']:.3f}s")        
        # Step 2: Extract content
        step_start = time.time()
        if is_digital:
            extractor = DigitalPDFExtractor()
            content, metadata = extractor.extract_text_digital_pdf(file_path, source_lang)
            step_times['content_extraction'] = time.time() - step_start
            logger.info(f"Digital PDF content extracted, length: {len(content)} characters (took {step_times['content_extraction']:.3f}s)")
            print(f"📝 Extracted content preview: {content[:200]}... ⏱️ {step_times['content_extraction']:.3f}s" if len(content) > 200 else f"📝 Extracted content: {content} ⏱️ {step_times['content_extraction']:.3f}s")
        else:
            extractor = ScannedPDFOCRExtractor(source_lang)
            content = extractor.extract_text(file_path)
            step_times['content_extraction'] = time.time() - step_start
            logger.info(f"Scanned PDF OCR content extracted, length: {len(content)} characters (took {step_times['content_extraction']:.3f}s)")
            print(f"📝 OCR content preview: {content[:200]}... ⏱️ {step_times['content_extraction']:.3f}s" if len(content) > 200 else f"📝 OCR content: {content} ⏱️ {step_times['content_extraction']:.3f}s")
            
        # Step 3: Tokenize
        step_start = time.time()
        anonymizer = TextAnonymizer()
        masked_text, token_map = anonymizer.anonymize_text(content)
        step_times['anonymization'] = time.time() - step_start
        logger.info(f"Text anonymized, tokens found: {len(token_map)} (took {step_times['anonymization']:.3f}s)")
        print(f"🎭 Masked text preview: {masked_text[:200]}... ⏱️ {step_times['anonymization']:.3f}s" if len(masked_text) > 200 else f"🎭 Masked text: {masked_text} ⏱️ {step_times['anonymization']:.3f}s")
        
        # Step 4: Chunk and translate
        step_start = time.time()
        translator = TextTranslator()
        text_chunks = translator.chunk_text(masked_text)
        chunking_time = time.time() - step_start
        step_times['chunking'] = chunking_time
        logger.info(f"Text chunked into {len(text_chunks)} chunks (took {step_times['chunking']:.3f}s)")
        print(f"✂️ Text chunks count: {len(text_chunks)} ⏱️ {step_times['chunking']:.3f}s")
        print(f"✂️ First chunk preview: {text_chunks[0][:100]}..." if text_chunks and len(text_chunks[0]) > 100 else f"✂️ First chunk: {text_chunks[0] if text_chunks else 'No chunks'}")
        
        # Translation step with detailed timing
        translation_start = time.time()
        print(f"🌍 TRANSLATION START - Using SOURCE={source_lang}, TARGET={target_lang} - Chunks: {len(text_chunks)}")
        translated_text = await translator.translate_text(text_chunks, source_lang, target_lang)
        step_times['translation'] = time.time() - translation_start
        logger.info(f"Translation completed, result length: {len(translated_text)} characters (took {step_times['translation']:.3f}s)")
        print(f"🌐 TRANSLATION COMPLETED ⏱️ {step_times['translation']:.3f}s")
        print(f"🌐 Translated text preview: {translated_text[:200]}..." if len(translated_text) > 200 else f"🌐 Translated text: {translated_text}")
        
        # Step 5: Reconstruct document
        step_start = time.time()
        if is_digital:
            reconstructor = DigitalPDFReconstructor()
            tiptap_json = reconstructor.reconstruct_document(translated_text, token_map, metadata)
            step_times['reconstruction'] = time.time() - step_start
            logger.info(f"Digital PDF reconstruction completed (took {step_times['reconstruction']:.3f}s)")
            print(f"🔧 Digital PDF reconstruction completed ⏱️ {step_times['reconstruction']:.3f}s")
        else:
            reconstructor = ScannedPDFReconstructor()
            tiptap_json = reconstructor.reconstruct_document(translated_text, token_map)
            step_times['reconstruction'] = time.time() - step_start
            logger.info(f"Scanned PDF reconstruction completed (took {step_times['reconstruction']:.3f}s)")
            print(f"🔧 Scanned PDF reconstruction completed ⏱️ {step_times['reconstruction']:.3f}s")
        
        # Calculate total time and log performance summary
        total_time = time.time() - pipeline_start_time
        
        print(f"\n⏱️  PERFORMANCE SUMMARY:")
        print(f"   📄 PDF Detection: {step_times['pdf_type_detection']:.3f}s")
        print(f"   📝 Content Extraction: {step_times['content_extraction']:.3f}s")
        print(f"   🎭 Anonymization: {step_times['anonymization']:.3f}s")
        print(f"   ✂️  Chunking: {step_times['chunking']:.3f}s")
        print(f"   🌍 Translation: {step_times['translation']:.3f}s ({len(text_chunks)} chunks)")
        print(f"   🔧 Reconstruction: {step_times['reconstruction']:.3f}s")
        print(f"   🏁 TOTAL TIME: {total_time:.3f}s")
        
        # Safe division check for performance percentage
        if total_time > 0:
            translation_percentage = (step_times['translation']/total_time)*100
            print(f"   💡 Translation was {translation_percentage:.1f}% of total time")
            logger.info(f"PERFORMANCE: Total={total_time:.3f}s, Translation={step_times['translation']:.3f}s ({translation_percentage:.1f}%)")
        else:
            print(f"   💡 Translation performance: {step_times['translation']:.3f}s (total time: {total_time:.3f}s)")
            logger.info(f"PERFORMANCE: Total={total_time:.3f}s, Translation={step_times['translation']:.3f}s")
        logger.info(f"Final JSON structure length: {len(str(tiptap_json))} characters")
        print(f"📋 Final JSON preview: {str(tiptap_json)[:300]}..." if len(str(tiptap_json)) > 300 else f"📋 Final JSON: {tiptap_json}")
        print(f"✅ PIPELINE COMPLETED SUCCESSFULLY - SOURCE={source_lang} → TARGET={target_lang}")
        logger.info(f"=== PIPELINE SUCCESS ===")
        
        # Send completion message with retry logic
        completion_message = {
            "status": "completed",
            "translated_content": tiptap_json,
            "processing_time": total_time,
            "performance": {
                "total_time": total_time,
                "translation_time": step_times['translation'],
                "translation_percentage": (step_times['translation']/total_time)*100 if total_time > 0 else 0
            }
        }
        
        # Try sending the completion message with retries
        for attempt in range(3):
            try:
                success = await manager.send_message(completion_message, user_id)
                if success:
                    logger.info(f"✅ Completion message sent successfully to {user_id} on attempt {attempt + 1}")
                    break
                else:
                    logger.warning(f"❌ Failed to send completion message to {user_id} on attempt {attempt + 1}")
                    if attempt < 2:  # Don't sleep on last attempt
                        await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
            except Exception as send_error:
                logger.error(f"❌ Error sending completion message to {user_id} on attempt {attempt + 1}: {send_error}")
                if attempt < 2:
                    await asyncio.sleep(0.1 * (attempt + 1))
        
    except Exception as e:
        logger.error(f"Pipeline failed for {doc_id}: {str(e)}")
        logger.error(f"Failed with languages: SOURCE={source_lang}, TARGET={target_lang}")
        print(f"❌ PIPELINE ERROR - SOURCE={source_lang}, TARGET={target_lang}")
        print(f"❌ Error details: {str(e)}")

        # Send error back to frontend
        await manager.send_message({
            "status": "error",
            "message": f"Processing failed: {str(e)}"
        }, user_id)

    finally:
        # Cleanup temporary files if they exist
        if not is_digital_pdf and os.path.exists(settings.temp_folder):
            shutil.rmtree(settings.temp_folder, ignore_errors=True)