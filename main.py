from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from gin_engine import GinGame

app = FastAPI(title="Gin Rummy Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

games = {}
players = {}

async def broadcast(game_id: str, message: dict, exclude: WebSocket = None):
    for ws, p in players.items():
        if p["game_id"] == game_id and ws != exclude:
            try:
                await ws.send_json(message)
            except WebSocketDisconnect:
                pass

async def broadcast_state(game_id: str):
    game = games[game_id]
    data = {
        "event": "state_update",
        "hands": [[str(c) for c in game.sorted_hand(i)] for i in range(2)],
        "melds": [list(game.get_melds(i)) for i in range(2)],
        "discard_top": str(game.discard_pile[-1]) if game.discard_pile else None,
        "turn": game.turn,
        "deadwood": game.deadwood,
        "scores": game.scores
    }
    for ws, p in players.items():
        if p["game_id"] == game_id:
            try:
                await ws.send_json(data)
            except WebSocketDisconnect:
                pass

async def reset_round(game_id: str):
    game = games[game_id]
    game.start_new_round()
    await broadcast_state(game_id)

async def reset_game(game_id: str):
    game = games[game_id]
    game.reset_game()
    await broadcast_state(game_id)
    await broadcast(game_id, {"event": "game_reset"})

@app.websocket("/ws/game/{game_id}/{player_name}")
async def websocket_endpoint(ws: WebSocket, game_id: str, player_name: str):
    await ws.accept()
    print(f"{player_name} connected to {game_id}")

    if game_id not in games:
        games[game_id] = GinGame()

    game = games[game_id]

    existing_players = [p["player_idx"] for p in players.values() if p["game_id"] == game_id]
    if 0 not in existing_players:
        player_idx = 0
    elif 1 not in existing_players:
        player_idx = 1
    else:
        await ws.send_json({"event": "error", "message": "Game already has 2 players"})
        await ws.close()
        return

    players[ws] = {"player_idx": player_idx, "game_id": game_id, "name": player_name}
    await ws.send_json({
        "event": "joined",
        "player_idx": player_idx,
        "hand": [str(c) for c in game.sorted_hand(player_idx)],
        "discard_top": str(game.discard_pile[-1])
    })

    await broadcast(game_id, {"event": "player_joined", "name": player_name, "player_idx": player_idx}, exclude=ws)
    await broadcast_state(game_id)

    try:
        while True:
            data = await ws.receive_json()
            event = data.get("event")

            if event not in ["knock", "reset_game"] and player_idx != game.turn:
                await ws.send_json({"event": "error", "message": "Not your turn"})
                continue

            if event == "draw":
                game.draw(player_idx, data.get("source"))

            elif event == "discard":
                game.discard(player_idx, data.get("card"))
                if game.winner is not None:
                    await broadcast_state(game_id)
                    await broadcast(game_id, {"event": "round_over", "winner": game.winner, "scores": game.scores})
                    await reset_round(game_id)
                    continue

            elif event == "knock":
                if game.can_knock(player_idx):
                    game.knock(player_idx)
                    await broadcast_state(game_id)
                    await broadcast(game_id, {"event": "round_over", "winner": game.winner, "scores": game.scores})
                    await reset_round(game_id)
                    continue
                else:
                    await ws.send_json({"event": "error", "message": "Cannot knock yet"})

            elif event == "reset_game":
                await reset_game(game_id)

            await broadcast_state(game_id)

    except WebSocketDisconnect:
        del players[ws]
        await broadcast(game_id, {"event": "player_left", "name": player_name, "player_idx": player_idx})
