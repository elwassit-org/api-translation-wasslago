from fastapi import APIRouter, WebSocket, WebSocketDisconnect, File, Form, UploadFile, BackgroundTasks, HTTPException
from pathlib import Path
import shutil
import uuid
import os
import time
import asyncio
from config import settings
import logging
from services.websocket_manager import ConnectionManager
from services.pipeline import process_pdf_pipeline

router = APIRouter()

manager = ConnectionManager()
logger = logging.getLogger(__name__) 

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Accept the WebSocket connection first
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for user {user_id}")
    
    # Check if user already has an active connection
    if user_id in manager.active_connections:
        # Close the old connection before setting up the new one
        old_websocket = manager.active_connections[user_id]
        try:
            await old_websocket.close(code=1000)  # Normal closure
            logger.info(f"Closed old connection for user {user_id}")
        except Exception as e:
            logger.warning(f"Error closing old connection for user {user_id}: {str(e)}")
        manager.disconnect(user_id)

    # Add new connection using existing websocket (already accepted)
    manager.connect_existing(websocket, user_id)
    logger.info(f"User {user_id} connected successfully")
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received message from {user_id}: {data}")
                
                # Echo back to confirm connection is alive
                await websocket.send_json({
                    "type": "pong", 
                    "message": "connection_alive",
                    "user_id": user_id,
                    "timestamp": str(time.time())
                })
                
            except WebSocketDisconnect:
                logger.info(f"Client {user_id} disconnected normally")
                break
            except Exception as msg_error:
                logger.error(f"Message handling error for {user_id}: {str(msg_error)}")
                # Don't break on message errors, keep connection alive for background processing
                continue
                
    except WebSocketDisconnect:
        logger.info(f"Client {user_id} disconnected")
    except Exception as e:
        logger.error(f"Unexpected error with client {user_id}: {str(e)}")
    finally:
        # Add a small delay to allow any pending messages to be sent
        try:
            await asyncio.sleep(0.1)  # 100ms delay
        except:
            pass
            
        manager.disconnect(user_id)
        try:
            # Check if websocket is still connected before attempting to close
            if hasattr(websocket, 'client_state'):
                # Check state name instead of disconnected attribute
                state_name = getattr(websocket.client_state, 'name', str(websocket.client_state))
                if state_name not in ['DISCONNECTED', 'CLOSED']:
                    await websocket.close(code=1000, reason="Connection completed")
                    logger.info(f"✅ WebSocket closed gracefully for user {user_id}")
            else:
                # Fallback: try to close anyway
                await websocket.close(code=1000, reason="Connection completed")
                logger.info(f"✅ WebSocket closed (fallback) for user {user_id}")
        except Exception as close_error:
            logger.warning(f"Error closing websocket for {user_id}: {str(close_error)}")

    
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


@router.get("/messages/{user_id}")
async def get_pending_messages(user_id: str):
    """
    Retrieve any pending messages for a user that couldn't be delivered via WebSocket
    """
    try:
        pending_messages = manager.get_pending_messages(user_id)
        
        # Clear the messages after retrieval
        if pending_messages:
            manager.clear_pending_messages(user_id)
            logger.info(f"📬 Retrieved {len(pending_messages)} pending messages for {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "messages": pending_messages,
            "count": len(pending_messages)
        }
    
    except Exception as e:
        logger.error(f"Error retrieving messages for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve messages: {str(e)}")


@router.get("/connection-status/{user_id}")
async def get_connection_status(user_id: str):
    """
    Check the WebSocket connection status for a user
    """
    try:
        is_connected = user_id in manager.active_connections
        pending_count = len(manager.get_pending_messages(user_id))
        
        return {
            "status": "success",
            "user_id": user_id,
            "connected": is_connected,
            "pending_messages": pending_count,
            "total_connections": manager.get_connection_count()
        }
    
    except Exception as e:
        logger.error(f"Error checking status for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")


@router.post("/clear-messages/{user_id}")
async def clear_pending_messages(user_id: str):
    """
    Clear all pending messages for a user
    """
    try:
        manager.clear_pending_messages(user_id)
        
        return {
            "status": "success",
            "user_id": user_id,
            "message": "Pending messages cleared"
        }
    
    except Exception as e:
        logger.error(f"Error clearing messages for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear messages: {str(e)}")
