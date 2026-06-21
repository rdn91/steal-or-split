from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio
import uuid
import json

app= FastAPI()

class ConnectionManager:
    def __init__(self):
        self.waiting_queue: WebSocket = None
        self.waiting_username: str = None
        self.active_rooms: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        return await self.handle_matchmaking(websocket, username)
    
    async def handle_matchmaking(self, websocket: WebSocket, username: str):
        if self.waiting_queue is None:
            self.waiting_queue = websocket
            self.waiting_username = username
            await websocket.send_text(json.dumps({"type": "waiting", "message": "waiting for an opponent.."}))
            return None, None
        else:
            room_id = str(uuid.uuid4())
            player1_ws = self.waiting_queue
            player1_name = self.waiting_username

            self.waiting_queue = None
            self.waiting_username = None

            self.active_rooms[room_id] = {
                "players" : [
                    {"ws": player1_ws, "username": player1_name, "choice": None},
                    {"ws": websocket, "username": username, "choice": None}
                            ]
            }
            match_payload = json.dumps({
                "type": "match_found",
                "objective": " Cooperate to survive."
            })

            await player1_ws.send_text(match_payload)
            await websocket.send_text(match_payload)

            return room_id, username

manager= ConnectionManager()

@app.websocket("/ws/matchmaking/{username}")
async def websocket_endpoint(websocket: WebSocket, username : str):
    room_id, current_user = await manager.connect(websocket, username)
    if room_id is None:
        try:
            while True:
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            manager.waiting_queue = None
            manager.waiting_username = None
            return
    try:
        asyncio.create_task(run_timer(room_id))

        while True:
            data = await websocket.receive_text()
            parsed_data = json.loads(data)
            await handle_game_action(room_id, username, parsed_data)
    except WebSocketDisconnect:
        if room_id in manager.active_rooms:
            del manager.active_rooms[room_id]
async def run_timer(room_id: str):
    for i in range(60, -1, -1):
        if room_id not in manager.active_rooms:
            break
            
        for player in manager.active_rooms[room_id]["players"]:
            await player["ws"].send_text(json.dumps({"type": "timer_update", "seconds" : i }))
        
        await asyncio.sleep(1)
    if room_id in manager.active_rooms:
        for player in manager.active_rooms[room_id]["players"]:
            await player["ws"].send_text(json.dumps({"type": "phase_lockin"}))
async def handle_game_action(room_id: str, sender_name: str, data: dict):
    room = manager.active_rooms.get(room_id)
    if not room: return

    # if data["type"] == "chat_send":
    #     for player in room["players"]:
    #         if player["username"] != sender_name:
    #             await player["ws"].send_text(json.dumps({
    #                 "type": "chat_receive",
    #                 "sender": sender_name,
    #                 "message": data["message"]
    #             }))
    if data["type"] == "decision_submit":
        for player in room["players"]:
            if player["username"] == sender_name:
                player["choice"] = data["choice"]
        player1 = room["players"][0]
        player2 = room["players"][1]

        if player1["choice"] is not None and player2["choice"] is not None:
            if player1["choice"] == "split" and player2["choice"] == "split":
                p1_outcome = p2_outcome = "Mutual Win!"
            elif player1["choice"] == "steal" and player2["choice"] == "steal":
                p1_outcome = p2_outcome = "Mutual Desctruction. Nobody Wins!"
            elif player1["choice"] == "steal" and player2["choice"] == "split":
                p1_outcome = "You Won You stole everything."
                p2_outcome = "You Lost, You were BETRAYED"
            elif player1["choice"] == "split" and player2["choice"] == "steal":
                p2_outcome = "You Won You stole everything."
                p1_outcome = "You Lost, You were BETRAYED"

            await player1["ws"].send_text(json.dumps({
                'type': "game_over",
                'your_choice' : player1["choice"],
                'opponent_choice' : player2["choice"],
                'outcome' : p1_outcome
            }))

            await player2["ws"].send_text(json.dumps({
                'type' : 'game_over',
                'your_choice' : player2["choice"],
                'opponent_choice' : player1["choice"],
                'outcome' : p2_outcome
            }))

