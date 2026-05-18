"""
WebSocket handler for live class real-time features:
- Chat
- Whiteboard sync (teacher always has access; students need teacher grant)
- Raise hand
- Polls
- Teacher grants/revokes student whiteboard access
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json

# room_id -> list of connected websockets with metadata
rooms: Dict[str, List[dict]] = {}
# room_id -> set of student user_ids who have whiteboard access
whiteboard_access: Dict[str, Set[str]] = {}


async def connect(room_id: str, websocket: WebSocket, user_id: str, role: str):
    await websocket.accept()
    if room_id not in rooms:
        rooms[room_id] = []
        whiteboard_access[room_id] = set()
    rooms[room_id].append({"ws": websocket, "user_id": user_id, "role": role})


def disconnect(room_id: str, websocket: WebSocket):
    if room_id in rooms:
        rooms[room_id] = [c for c in rooms[room_id] if c["ws"] != websocket]
        if not rooms[room_id]:
            del rooms[room_id]
            whiteboard_access.pop(room_id, None)


async def broadcast(room_id: str, message: dict, exclude: WebSocket = None):
    if room_id not in rooms:
        return
    dead = []
    for conn in rooms[room_id]:
        if conn["ws"] == exclude:
            continue
        try:
            await conn["ws"].send_text(json.dumps(message))
        except Exception:
            dead.append(conn)
    for conn in dead:
        rooms[room_id].remove(conn)


async def send_to_user(room_id: str, target_user_id: str, message: dict):
    """Send a message to a specific user in the room."""
    if room_id not in rooms:
        return
    for conn in rooms[room_id]:
        if conn["user_id"] == target_user_id:
            try:
                await conn["ws"].send_text(json.dumps(message))
            except Exception:
                pass


async def live_class_endpoint(websocket: WebSocket, room_id: str, user_id: str, role: str):
    await connect(room_id, websocket, user_id, role)
    await broadcast(room_id, {"event": "user_joined", "user_id": user_id, "role": role}, exclude=websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event = message.get("event")

            # ── Chat ──────────────────────────────────────────────────────────
            if event == "chat":
                await broadcast(room_id, {
                    "event": "chat",
                    "user_id": user_id,
                    "role": role,
                    "text": message.get("text", ""),
                })

            # ── Whiteboard ────────────────────────────────────────────────────
            elif event == "whiteboard":
                # Teachers always have whiteboard access
                # Students need explicit grant from teacher
                has_access = (
                    role == "teacher"
                    or user_id in whiteboard_access.get(room_id, set())
                )
                if not has_access:
                    await websocket.send_text(json.dumps({
                        "event": "error",
                        "message": "You do not have whiteboard access. Ask your teacher.",
                    }))
                else:
                    await broadcast(room_id, {
                        "event": "whiteboard",
                        "user_id": user_id,
                        "action": message.get("action"),  # draw, erase, shape, formula
                        "data": message.get("data"),
                    }, exclude=websocket)

            # ── Teacher: Grant whiteboard access to a student ─────────────────
            elif event == "grant_whiteboard":
                if role != "teacher":
                    await websocket.send_text(json.dumps({
                        "event": "error",
                        "message": "Only teachers can grant whiteboard access.",
                    }))
                else:
                    target_id = message.get("target_user_id")
                    if target_id:
                        whiteboard_access.setdefault(room_id, set()).add(target_id)
                        # Notify the student they now have access
                        await send_to_user(room_id, target_id, {
                            "event": "whiteboard_access_granted",
                            "message": "Your teacher gave you whiteboard access.",
                        })
                        await broadcast(room_id, {
                            "event": "whiteboard_access_update",
                            "user_id": target_id,
                            "has_access": True,
                        })

            # ── Teacher: Revoke whiteboard access from a student ──────────────
            elif event == "revoke_whiteboard":
                if role != "teacher":
                    await websocket.send_text(json.dumps({
                        "event": "error",
                        "message": "Only teachers can revoke whiteboard access.",
                    }))
                else:
                    target_id = message.get("target_user_id")
                    if target_id:
                        whiteboard_access.get(room_id, set()).discard(target_id)
                        await send_to_user(room_id, target_id, {
                            "event": "whiteboard_access_revoked",
                            "message": "Your whiteboard access has been removed.",
                        })
                        await broadcast(room_id, {
                            "event": "whiteboard_access_update",
                            "user_id": target_id,
                            "has_access": False,
                        })

            # ── Raise Hand ────────────────────────────────────────────────────
            elif event == "raise_hand":
                await broadcast(room_id, {"event": "raise_hand", "user_id": user_id})

            # ── Poll Answer ───────────────────────────────────────────────────
            elif event == "poll_answer":
                await broadcast(room_id, {
                    "event": "poll_answer",
                    "user_id": user_id,
                    "answer": message.get("answer"),
                })

    except WebSocketDisconnect:
        disconnect(room_id, websocket)
        await broadcast(room_id, {"event": "user_left", "user_id": user_id})
