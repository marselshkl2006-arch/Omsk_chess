import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import chess
import chess.pgn
from dotenv import load_dotenv
from typing import List
import uvicorn
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

# Импортируем интеграцию с Chess.com
try:
    from chesscom_integration import ChessComIntegration
    CHESSCOM_AVAILABLE = True
    chesscom = ChessComIntegration()
    if chesscom.test_connection():
        print("✅ Chess.com интеграция загружена и работает")
    else:
        print("⚠️ Chess.com API недоступен, будет использована локальная трансляция")
        CHESSCOM_AVAILABLE = False
except ImportError as e:
    CHESSCOM_AVAILABLE = False
    print(f"⚠️ Chess.com интеграция не загружена: {e}")

app = FastAPI(
    title="Omsk Chess Broadcast",
    description="Система трансляции шахматных партий с брендированием Омской области",
    version="1.0.0"
)

# CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище активных подключений и состояния
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.current_game = chess.Board()
        self.moves_history: List[str] = []
        self.moves_uci: List[str] = []
        self.game_started = False
        self.broadcast_id = None
        self.broadcast_url = None
        self.white_player = "Губернатор Омской области"
        self.black_player = "Соперник"
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_json({
            "type": "init",
            "fen": self.current_game.fen(),
            "moves": self.moves_history,
            "moves_uci": self.moves_uci,
            "game_started": self.game_started,
            "broadcast_url": self.broadcast_url
        })
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
    async def broadcast_move(self, move_san: str, move_uci: str, fen: str):
        """Отправка хода всем подключенным клиентам"""
        message = {
            "type": "move",
            "move": move_san,
            "move_uci": move_uci,
            "fen": fen,
            "timestamp": datetime.now().isoformat()
        }
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    def reset_game(self):
        """Сброс игры к начальному состоянию"""
        self.current_game = chess.Board()
        self.moves_history = []
        self.moves_uci = []
        self.game_started = True
        self.broadcast_url = None
        self.broadcast_id = None

manager = ConnectionManager()

@app.get("/")
async def root():
    """Корневой эндпоинт для проверки работы сервера"""
    return {
        "message": "Omsk Chess Broadcast API",
        "status": "running",
        "version": "1.0.0",
        "chesscom_integration": CHESSCOM_AVAILABLE
    }

@app.post("/start-game")
async def start_game(data: dict = None):
    """
    Начать новую партию
    """
    manager.reset_game()
    
    if data:
        if "white" in data:
            manager.white_player = data["white"]
        if "black" in data:
            manager.black_player = data["black"]
    
    # СОЗДАНИЕ ИГРЫ НА CHESS.COM
    if CHESSCOM_AVAILABLE:
        broadcast_name = data.get("broadcast_name") if data else None
        if not broadcast_name:
            broadcast_name = f"ПМЭФ-2026: {manager.white_player} vs {manager.black_player}"
        
        game_result = chesscom.create_challenge(
            name=broadcast_name,
            white=manager.white_player.replace(" ", "_"),
            black=manager.black_player.replace(" ", "_")
        )
        
        if game_result["success"]:
            manager.broadcast_url = game_result["url"]
            manager.broadcast_id = game_result["game_id"]
            print(f"✅ Игра создана на Chess.com: {manager.broadcast_url}")
    
    # Рассылаем всем клиентам о новой игре
    for connection in manager.active_connections:
        try:
            await connection.send_json({
                "type": "new_game",
                "fen": manager.current_game.fen(),
                "broadcast_url": manager.broadcast_url,
                "white": manager.white_player,
                "black": manager.black_player
            })
        except:
            pass
    
    return {
        "status": "success", 
        "message": "Новая партия начата", 
        "fen": manager.current_game.fen(),
        "chesscom_url": manager.broadcast_url,
        "white": manager.white_player,
        "black": manager.black_player
    }

@app.post("/move")
async def make_move(move_data: dict):
    """
    Добавить ход
    """
    move_uci = move_data.get("move")
    from_camera = move_data.get("from_camera", False)
    
    if not move_uci:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Не указан ход"}
        )
    
    try:
        move = chess.Move.from_uci(move_uci)
        legal_moves = list(manager.current_game.legal_moves)
        
        if move in manager.current_game.legal_moves:
            manager.current_game.push(move)
            
            try:
                move_san = manager.current_game.san(move)
            except:
                move_san = move_uci
            
            manager.moves_history.append(move_san)
            manager.moves_uci.append(move_uci)
            
            await manager.broadcast_move(move_san, move_uci, manager.current_game.fen())
            
            game_over = manager.current_game.is_game_over()
            result = None
            if game_over:
                if manager.current_game.is_checkmate():
                    winner = "white" if manager.current_game.turn == chess.BLACK else "black"
                    result = f"Мат. Победили {'белые' if winner == 'white' else 'черные'}"
                elif manager.current_game.is_stalemate():
                    result = "Пат"
                elif manager.current_game.is_insufficient_material():
                    result = "Ничья (недостаточно материала)"
                else:
                    result = "Ничья"
            
            return {
                "status": "success", 
                "move_san": move_san,
                "move_uci": move_uci,
                "fen": manager.current_game.fen(),
                "move_number": len(manager.moves_history),
                "is_game_over": game_over,
                "result": result,
                "chesscom_url": manager.broadcast_url
            }
        else:
            turn = "белых" if manager.current_game.turn == chess.WHITE else "черных"
            legal_uci = [m.uci() for m in legal_moves[:5]]
            hint = f"Недопустимый ход {move_uci}. Сейчас ход {turn}. Примеры: {', '.join(legal_uci)}"
            
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error", 
                    "message": hint,
                    "fen": manager.current_game.fen()
                }
            )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error", 
                "message": f"Неверный формат хода. Используйте формат UCI (например, 'e2e4')"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error", 
                "message": f"Внутренняя ошибка: {str(e)}"
            }
        )

@app.get("/pgn")
async def get_pgn():
    """Получить PGN текущей партии"""
    game = chess.pgn.Game()
    
    game.headers["Event"] = "ПМЭФ-2026. Блицтурнир глав регионов"
    game.headers["Site"] = "Санкт-Петербург, Россия"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = "1"
    game.headers["White"] = manager.white_player
    game.headers["Black"] = manager.black_player
    game.headers["Result"] = "*"
    game.headers["OmskTag"] = "#ОмскШахматнаяСтолица"
    game.headers["Tourism"] = "https://omsk.travel"
    
    if manager.broadcast_url:
        game.headers["ChessCom"] = manager.broadcast_url
    
    node = game
    temp_board = chess.Board()
    
    for move_uci in manager.moves_uci:
        try:
            move = chess.Move.from_uci(move_uci)
            if move in temp_board.legal_moves:
                node = node.add_variation(move)
                temp_board.push(move)
        except:
            pass
    
    if manager.current_game.is_game_over():
        if manager.current_game.is_checkmate():
            result = "1-0" if manager.current_game.turn == chess.BLACK else "0-1"
        else:
            result = "1/2-1/2"
        game.headers["Result"] = result
    
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_string = game.accept(exporter)
    
    return {"pgn": pgn_string, "headers": dict(game.headers), "moves": manager.moves_history}

@app.get("/game/state")
async def get_game_state():
    """Получить текущее состояние игры"""
    legal_moves = list(manager.current_game.legal_moves)
    
    return {
        "fen": manager.current_game.fen(),
        "moves": manager.moves_history,
        "game_started": manager.game_started,
        "turn": "white" if manager.current_game.turn == chess.WHITE else "black",
        "is_game_over": manager.current_game.is_game_over(),
        "legal_moves_count": len(legal_moves),
        "broadcast_url": manager.broadcast_url,
        "white": manager.white_player,
        "black": manager.black_player
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для реального времени"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import sys
    
    port = 8001
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        try:
            port = int(sys.argv[2])
        except:
            pass
    
    print("🚀 Запуск Omsk Chess Broadcast сервера...")
    print(f"📡 Chess.com интеграция: {'✅' if CHESSCOM_AVAILABLE else '❌'}")
    print(f"🌐 Сервер будет доступен на http://localhost:{port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
