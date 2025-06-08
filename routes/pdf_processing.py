from fastapi import APIRouter, WebSocket, WebSocketDisconnect, File, Form, UploadFile, BackgroundTasks, HTTPException
from pathlib import Path
import shutil
import uuid
import os
from config import settings
import logging
from services.websocket_manager import ConnectionManager
from services.pipeline import process_pdf_pipeline

router = APIRouter()

manager = ConnectionManager()
logger = logging.getLogger(__name__) 

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Only allow one connection per user_id
    if user_id in manager.active_connections:
        await websocket.close(code=1008)  # Policy violation
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Just wait for connection close without processing messages
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        print(f"Client {user_id} disconnected")
    except Exception as e:
        print(f"Error with client {user_id}: {str(e)}")
    finally:
        manager.disconnect(user_id)
        try:
            await websocket.close()
        except:
            pass

    
from fastapi import HTTPException

@router.post("/process-pdf/")
async def process_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    doc_id: str = Form(...),
    user_id: str = Form(...),
):
    """
    Endpoint for PDF processing pipeline with real-time progress updates.
    """
    filename = f"{uuid.uuid4()}.pdf"
    temp_path = Path(settings.temp_folder) / filename 

    try:
        # Save uploaded file
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # Notify frontend that processing has started
        await manager.send_message({
            "status": "processing",
            "message": "Starting PDF processing..."
        }, user_id)

        # Launch background processing
        background_tasks.add_task(
            process_pdf_pipeline,
            file_path=temp_path,
            source_lang=source_lang,
            target_lang=target_lang,
            doc_id=doc_id,
            user_id=user_id,
            manager=manager,
        )
        
        return {
            "status": "processing",
            "message": "PDF is being processed in background.",
            "document_id": doc_id
        }

    except Exception as e:
        logger.exception(f"[{doc_id}] Error during upload or setup: {str(e)}")

        # Notify frontend about error (WebSocket)
        await manager.send_message({
            "status": "error",
            "message": f"Processing failed: {str(e)}"
        }, user_id)

        # Cleanup any partially saved file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_error:
                logger.error(f"[{doc_id}] Cleanup failed: {str(cleanup_error)}")

        # Raise HTTPException to propagate to frontend via API
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
