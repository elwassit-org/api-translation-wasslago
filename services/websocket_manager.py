
from fastapi import WebSocket
import logging
import time
import asyncio
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class PendingMessage:
    """Represents a message waiting to be delivered"""
    user_id: str
    message: dict
    timestamp: float
    attempts: int = 0
    max_attempts: int = 3

class ConnectionManager:
    """Enhanced WebSocket connection manager with persistence and reliability"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_messages: Dict[str, List[PendingMessage]] = {}
        self.connection_heartbeats: Dict[str, float] = {}
        self.heartbeat_interval = 30  # seconds
        self._cleanup_task = None
        
    async def start_background_tasks(self):
        """Start background tasks for heartbeat and cleanup"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of stale connections and old messages"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_stale_connections()
                await self._cleanup_old_messages()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_stale_connections(self):
        """Remove connections that haven't had heartbeat in too long"""
        current_time = time.time()
        stale_users = []
        
        for user_id, last_heartbeat in self.connection_heartbeats.items():
            if current_time - last_heartbeat > self.heartbeat_interval * 3:
                stale_users.append(user_id)
        
        for user_id in stale_users:
            logger.warning(f"🧹 Cleaning up stale connection for {user_id}")
            self.disconnect(user_id)
    
    async def _cleanup_old_messages(self):
        """Remove pending messages older than 5 minutes"""
        current_time = time.time()
        for user_id, messages in list(self.pending_messages.items()):
            # Keep only messages younger than 5 minutes
            self.pending_messages[user_id] = [
                msg for msg in messages 
                if current_time - msg.timestamp < 300
            ]
            # Remove empty lists
            if not self.pending_messages[user_id]:
                del self.pending_messages[user_id]

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket and deliver any pending messages"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.connection_heartbeats[user_id] = time.time()
        logger.info(f"🔌 WebSocket connected for user {user_id}")
        
        # Start background tasks if not already running
        await self.start_background_tasks()
        
        # Deliver any pending messages
        await self._deliver_pending_messages(user_id)

    def connect_existing(self, websocket: WebSocket, user_id: str):
        """Connect using an already accepted WebSocket"""
        self.active_connections[user_id] = websocket
        self.connection_heartbeats[user_id] = time.time()
        logger.info(f"🔌 WebSocket registered for user {user_id}")

    def disconnect(self, user_id: str):
        """Disconnect a WebSocket and clean up resources"""
        if user_id in self.active_connections:
            self.active_connections.pop(user_id, None)
            self.connection_heartbeats.pop(user_id, None)
            logger.info(f"❌ WebSocket disconnected for user {user_id}")

    async def _deliver_pending_messages(self, user_id: str):
        """Deliver all pending messages for a user"""
        if user_id not in self.pending_messages:
            return
            
        messages = self.pending_messages[user_id]
        delivered = []
        
        for msg in messages:
            success = await self._send_direct_message(msg.message, user_id)
            if success:
                delivered.append(msg)
                logger.info(f"📫 Delivered pending message to {user_id}: {msg.message.get('type', 'unknown')}")
            else:
                msg.attempts += 1
                if msg.attempts >= msg.max_attempts:
                    delivered.append(msg)  # Remove after max attempts
                    logger.warning(f"🚫 Dropping message after {msg.attempts} attempts for {user_id}")
        
        # Remove delivered messages
        for msg in delivered:
            messages.remove(msg)
            
        if not messages:
            del self.pending_messages[user_id]

    async def _send_direct_message(self, message: dict, user_id: str) -> bool:
        """Send message directly without persistence"""
        websocket = self.active_connections.get(user_id)
        if not websocket:
            return False
            
        try:
            # Add timestamp to all messages
            message["timestamp"] = time.time()
            
            # Check WebSocket state before sending
            if hasattr(websocket, 'client_state'):
                state_name = getattr(websocket.client_state, 'name', str(websocket.client_state))
                if state_name == 'DISCONNECTED':
                    logger.warning(f"WebSocket already disconnected for {user_id}")
                    self.disconnect(user_id)
                    return False
            
            await websocket.send_json(message)
            self.connection_heartbeats[user_id] = time.time()  # Update heartbeat
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending message to {user_id}: {str(e)}")
            self.disconnect(user_id)
            return False

    async def send_message(self, message: dict, user_id: str) -> bool:
        """Send message with persistence - primary interface for message sending"""
        # Try to send directly first
        success = await self._send_direct_message(message, user_id)
        
        if not success:
            # Store for later delivery if connection is not available
            self._store_pending_message(user_id, message)
            logger.info(f"📦 Message stored for later delivery to {user_id}: {message.get('type', 'unknown')}")
            return False
        
        return True
    
    def _store_pending_message(self, user_id: str, message: dict):
        """Store a message for later delivery"""
        if user_id not in self.pending_messages:
            self.pending_messages[user_id] = []
        
        pending_msg = PendingMessage(
            user_id=user_id,
            message=message.copy(),
            timestamp=time.time()
        )
        
        self.pending_messages[user_id].append(pending_msg)
        
        # Limit pending messages per user to prevent memory issues
        if len(self.pending_messages[user_id]) > 50:
            self.pending_messages[user_id] = self.pending_messages[user_id][-50:]
    
    def get_pending_messages(self, user_id: str) -> List[dict]:
        """Get all pending messages for a user"""
        if user_id not in self.pending_messages:
            return []
        
        return [asdict(msg) for msg in self.pending_messages[user_id]]
    
    def clear_pending_messages(self, user_id: str):
        """Clear all pending messages for a user"""
        if user_id in self.pending_messages:
            del self.pending_messages[user_id]
            logger.info(f"🧹 Cleared pending messages for {user_id}")

    def get_connection_count(self):
        return len(self.active_connections)

    def list_active_connections(self):
        return list(self.active_connections.keys())