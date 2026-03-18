import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import chess
import chess.pgn
from dotenv import load_dotenv
import requests
from typing import List, Dict
import uvicorn
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

# Импортируем интеграцию с Lichess
try:
    from lichess_integration import lichess_broadcast
    LICHESS_AVAILABLE = True
    print("✅ Lichess интеграция загружена")
except ImportError as e:
    LICHESS_AVAILABLE = False
    print(f"⚠️ Lichess интеграция не загружена: {e}")

app = FastAPI(
    title="Omsk Chess Broadcast",
    description="Система трансляции шахматных партий с брендированием Омской области",
    version="1.0.0"
)

# CORS для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
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
        self.game_started = False
        self.broadcast_id = None
        self.round_id = None
        self.broadcast_url = None
        self.white_player = "Губернатор Омской области"
        self.black_player = "Соперник"
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Отправляем текущее состояние новому клиенту
        await websocket.send_json({
            "type": "init",
            "fen": self.current_game.fen(),
            "moves": self.moves_history,
            "game_started": self.game_started,
            "broadcast_url": self.broadcast_url
        })
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
    async def broadcast_move(self, move_san: str, fen: str):
        """Отправка хода всем подключенным клиентам"""
        message = {
            "type": "move",
            "move": move_san,
            "fen": fen,
            "timestamp": datetime.now().isoformat()
        }
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Очищаем отключившиеся соединения
        for conn in disconnected:
            self.disconnect(conn)
    
    def reset_game(self):
        """Сброс игры к начальному состоянию"""
        self.current_game = chess.Board()
        self.moves_history = []
        self.game_started = True

manager = ConnectionManager()

@app.get("/")
async def root():
    """Корневой эндпоинт для проверки работы сервера"""
    return {
        "message": "Omsk Chess Broadcast API",
        "status": "running",
        "version": "1.0.0",
        "lichess_integration": LICHESS_AVAILABLE
    }

@app.post("/start-game")
async def start_game(data: dict = None):
    """
    Начать новую партию
    
    Опциональные параметры в data:
    - white: имя белых (по умолчанию "Губернатор Омской области")
    - black: имя черных (по умолчанию "Соперник")
    - broadcast_name: название трансляции
    """
    manager.reset_game()
    
    # Обновляем имена игроков, если переданы
    if data:
        if "white" in data:
            manager.white_player = data["white"]
        if "black" in data:
            manager.black_player = data["black"]
    
    # Создаем трансляцию на Lichess если доступно
    if LICHESS_AVAILABLE:
        broadcast_name = data.get("broadcast_name") if data else None
        if not broadcast_name:
            broadcast_name = f"ПМЭФ-2026: {manager.white_player} vs {manager.black_player}"
        
        result = lichess_broadcast.create_broadcast(
            name=broadcast_name,
            white=manager.white_player,
            black=manager.black_player
        )
        
        if result["success"]:
            manager.broadcast_url = result["url"]
            manager.broadcast_id = result["broadcast_id"]
            manager.round_id = result["round_id"]
            print(f"✅ Трансляция создана: {manager.broadcast_url}")
        else:
            print(f"❌ Ошибка создания трансляции: {result.get('error')}")
            manager.broadcast_url = None
    
    # Рассылаем всем клиентам о новой игре
    for connection in manager.active_connections:
        try:
            await connection.send_json({
                "type": "new_game",
                "fen": manager.current_game.fen(),
                "broadcast_url": manager.broadcast_url
            })
        except:
            pass
    
    return {
        "status": "success", 
        "message": "Новая партия начата", 
        "fen": manager.current_game.fen(),
        "lichess_url": manager.broadcast_url,
        "white": manager.white_player,
        "black": manager.black_player
    }

@app.post("/move")
async def make_move(move_data: dict):
    """
    Добавить ход (ручной ввод или от распознавания)
    
    Формат move_data:
    {
        "move": "e2e4",  # Ход в формате UCI
        "from_camera": false  # Опционально: флаг, что ход с камеры
    }
    """
    move_uci = move_data.get("move")
    from_camera = move_data.get("from_camera", False)
    
    if not move_uci:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Не указан ход"}
        )
    
    try:
        # Конвертируем UCI в объект хода
        move = chess.Move.from_uci(move_uci)
        
        # Получаем список легальных ходов
        legal_moves = list(manager.current_game.legal_moves)
        legal_uci = [m.uci() for m in legal_moves]
        
        # Проверяем легальность
        if move in manager.current_game.legal_moves:
            # Делаем ход
            manager.current_game.push(move)
            
            # Получаем SAN нотацию (только для легальных ходов)
            try:
                move_san = manager.current_game.san(move)
            except:
                # Если не получается получить SAN, используем UCI
                move_san = move_uci
            
            manager.moves_history.append(move_san)
            
            # Рассылаем всем клиентам
            await manager.broadcast_move(move_san, manager.current_game.fen())
            
            # Отправляем в Lichess если доступно
            lichess_success = False
            if LICHESS_AVAILABLE and manager.round_id:
                try:
                    # Для Lichess отправляем SAN нотацию
                    lichess_success = lichess_broadcast.push_move(move_san, manager.round_id)
                    if lichess_success:
                        print(f"✅ Ход {move_san} отправлен в Lichess")
                    else:
                        print(f"⚠️ Не удалось отправить ход {move_san} в Lichess")
                except Exception as e:
                    print(f"❌ Ошибка отправки в Lichess: {e}")
            
            # Проверяем окончание игры
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
                "lichess_sent": lichess_success
            }
        else:
            # Формируем понятное сообщение об ошибке с подсказкой
            hint = f"Недопустимый ход {move_uci}. "
            
            if len(legal_moves) == 0:
                hint += "Нет допустимых ходов. Игра окончена?"
            else:
                # Показываем несколько примеров допустимых ходов
                examples = legal_uci[:5]  # Первые 5 ходов
                if len(legal_moves) > 5:
                    hint += f"Примеры допустимых ходов: {', '.join(examples)}..."
                else:
                    hint += f"Допустимые ходы: {', '.join(legal_uci)}"
            
            # Добавляем информацию о текущей позиции
            turn = "белых" if manager.current_game.turn == chess.WHITE else "черных"
            
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error", 
                    "message": hint,
                    "turn": turn,
                    "legal_moves": legal_uci[:10],  # Отправляем первые 10 ходов для подсказки
                    "fen": manager.current_game.fen()
                }
            )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error", 
                "message": f"Неверный формат хода. Используйте формат UCI (например, 'e2e4'). Ошибка: {str(e)}"
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
    
    # Заголовки партии с брендированием
    game.headers["Event"] = "ПМЭФ-2026. Блицтурнир глав регионов"
    game.headers["Site"] = "Санкт-Петербург, Россия"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = "1"
    game.headers["White"] = manager.white_player
    game.headers["Black"] = manager.black_player
    game.headers["Result"] = "*"  # Будет обновлено если партия закончена
    
    # Добавляем теги брендирования Омской области
    game.headers["OmskTag"] = "#ОмскШахматнаяСтолица"
    game.headers["OmskRegion"] = "https://omskregion.gov.ru"
    game.headers["Tourism"] = "https://omsk.travel"
    game.headers["Annotator"] = "Система трансляции Омской области"
    
    # Если есть трансляция, добавляем ссылку
    if manager.broadcast_url:
        game.headers["Broadcast"] = manager.broadcast_url
    
    # Добавляем ходы
    node = game
    temp_board = chess.Board()
    
    for move_san in manager.moves_history:
        try:
            # Пробуем распарсить SAN ход
            move = temp_board.parse_san(move_san)
            node = node.add_variation(move)
            temp_board.push(move)
        except:
            # Если не получается, пробуем как UCI
            try:
                move = chess.Move.from_uci(move_san)
                if move in temp_board.legal_moves:
                    node = node.add_variation(move)
                    temp_board.push(move)
            except:
                pass
    
    # Обновляем результат если игра закончена
    if manager.current_game.is_game_over():
        if manager.current_game.is_checkmate():
            result = "1-0" if manager.current_game.turn == chess.BLACK else "0-1"
        else:
            result = "1/2-1/2"
        game.headers["Result"] = result
    
    # Экспортируем в PGN
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_string = game.accept(exporter)
    
    return {
        "pgn": pgn_string,
        "headers": dict(game.headers),
        "moves": manager.moves_history
    }

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
        "legal_moves_sample": [m.uci() for m in legal_moves[:5]],
        "broadcast_url": manager.broadcast_url,
        "white": manager.white_player,
        "black": manager.black_player
    }

@app.get("/lichess/status")
async def get_lichess_status():
    """Получить статус Lichess трансляции"""
    if not LICHESS_AVAILABLE:
        return {"available": False, "message": "Lichess интеграция не доступна"}
    
    if not manager.round_id:
        return {"available": True, "active": False, "message": "Трансляция не создана"}
    
    try:
        status = lichess_broadcast.get_broadcast_status(manager.round_id)
        return {
            "available": True,
            "active": True,
            "broadcast_id": manager.broadcast_id,
            "round_id": manager.round_id,
            "url": manager.broadcast_url,
            "status": status
        }
    except Exception as e:
        return {
            "available": True,
            "active": True,
            "broadcast_id": manager.broadcast_id,
            "round_id": manager.round_id,
            "url": manager.broadcast_url,
            "error": str(e)
        }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для реального времени"""
    await manager.connect(websocket)
    try:
        while True:
            # Ждем сообщения от клиента (может быть пульс или команды)
            data = await websocket.receive_text()
            # Можно добавить обработку команд, например "ping"
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import sys
    
    # Проверяем, указан ли порт в аргументах командной строки
    port = 8001  # Порт по умолчанию
    
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        try:
            port = int(sys.argv[2])
        except:
            pass
    
    print("🚀 Запуск Omsk Chess Broadcast сервера...")
    print(f"📡 Lichess интеграция: {'✅' if LICHESS_AVAILABLE else '❌'}")
    print(f"🌐 Сервер будет доступен на http://localhost:{port}")
    print(f"📋 Документация API: http://localhost:{port}/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
