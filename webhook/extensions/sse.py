"""
Description:
Author: 侯文君
Date: 2025-05-12 15:20:50
LastEditors: 侯文君
LastEditTime: 2025-05-15 18:26:46
"""

import json
import logging
import time
from queue import Queue, Empty
from threading import Lock, Event
from typing import Dict, Set

from starlette.responses import StreamingResponse


class ServerSentEvents:
    def __init__(self):
        self.clients: Dict[str, Queue] = {}
        self.active_clients: Set[str] = set()
        self._lock = Lock()
        self._client_id_counter = 0
        self._stop_event = Event()
        self._heartbeat_interval = 15  # 秒

    def _get_next_client_id(self) -> str:
        with self._lock:
            self._client_id_counter += 1
            return f"client_{self._client_id_counter}"

    def publish(self, event_type: str, data: dict):
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        logging.info(
            f"Publishing: \n---------------------------{message.strip()}\n---------------------------"
        )
        with self._lock:
            to_remove = set()
            for client_id in self.active_clients.copy():
                q = self.clients.get(client_id)
                if not q:
                    continue
                try:
                    q.put_nowait(message)
                except:
                    to_remove.add(client_id)
            for cid in to_remove:
                self.clients.pop(cid, None)
                self.active_clients.discard(cid)

    def stream(self) -> StreamingResponse:
        client_id = self._get_next_client_id()
        q = Queue(maxsize=10)

        with self._lock:
            self.clients[client_id] = q
            self.active_clients.add(client_id)

        def event_stream():
            last_heartbeat = time.time()
            try:
                yield ":\n\n"  # 初始心跳
                while not self._stop_event.is_set():
                    try:
                        msg = q.get(timeout=1)
                        last_heartbeat = time.time()
                        yield msg
                    except Empty:
                        if time.time() - last_heartbeat >= self._heartbeat_interval:
                            yield ":\n\n"
                            last_heartbeat = time.time()
            finally:
                with self._lock:
                    self.clients.pop(client_id, None)
                    self.active_clients.discard(client_id)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    def shutdown(self):
        self._stop_event.set()
        with self._lock:
            self.clients.clear()
            self.active_clients.clear()


sse = ServerSentEvents()
