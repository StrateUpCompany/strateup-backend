from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio
from backend.core.event_bus import EventBus
from backend.utils.logger import logger

class ConnectionManager:
    def __init__(self):
        # Pooling: client_id -> list of websockets (max 3)
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.max_connections_per_client = 3
        self._setup_listeners()
        
    def _setup_listeners(self):
        EventBus.subscribe("update", self.broadcast_update)
        EventBus.subscribe("finished", self.broadcast_finished)
        EventBus.subscribe("error", self.broadcast_error)
        EventBus.subscribe("cloning_success", self.broadcast_success)

    async def connect(self, websocket: WebSocket, client_id: str = "default"):
        await websocket.accept()
        
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
            
        # Enforce pool limit: remove oldest if full
        if len(self.active_connections[client_id]) >= self.max_connections_per_client:
            oldest_ws = self.active_connections[client_id].pop(0)
            try:
                await oldest_ws.close(code=1000, reason="Connection limit reached")
            except Exception:
                pass
                
        self.active_connections[client_id].append(websocket)
        logger.info(f"WS Connect: {client_id}. Active: {len(self.active_connections[client_id])}")

    def disconnect(self, websocket: WebSocket, client_id: str = "default"):
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
                logger.info(f"WS Disconnect: {client_id}")
            
            # Clean up empty keys
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def broadcast(self, message: str):
        """Broadcasts to ALL connected clients across all pools"""
        # Snapshot keys to avoid runtime error during iteration
        current_clients = list(self.active_connections.keys())
        
        for client_id in current_clients:
            websockets = self.active_connections.get(client_id, [])
            for ws in list(websockets):
                try:
                    await ws.send_text(message)
                except Exception as e:
                    logger.warning(f"Error sending WS to {client_id}: {e}")
                    self.disconnect(ws, client_id)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Personal message failed: {e}")

    def set_loop(self, loop):
        """Define o event loop principal para dispatch thread-safe"""
        self.loop = loop
        # Start heartbeat
        asyncio.run_coroutine_threadsafe(self._heartbeat(), self.loop)

    async def _heartbeat(self):
        """Keep-alive ping every 30s"""
        while True:
            await asyncio.sleep(30)
            if self.active_connections:
                await self.broadcast(json.dumps({"type": "ping"}))

    # --- Event Bus Handlers ---
    
    def broadcast_update(self, data):
        self._dispatch({"type": "progress", "data": data})

    def broadcast_finished(self, msg):
        self._dispatch({"type": "completed", "message": msg})

    def broadcast_error(self, msg):
        self._dispatch({"type": "error", "message": msg})
        
    def broadcast_success(self, data):
        self._dispatch({"type": "success", "data": data})

    def _dispatch(self, message_dict):
        """Envia mensagem para todos de forma thread-safe"""
        msg_str = json.dumps(message_dict)
        
        if hasattr(self, 'loop') and self.loop:
            asyncio.run_coroutine_threadsafe(self.broadcast(msg_str), self.loop)


manager = ConnectionManager()
