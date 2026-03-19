"""
Полноценная интеграция с Chess.com API для ПМЭФ-2026
Использует публичное API Chess.com
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChessComIntegration:
    """
    Клиент для Chess.com API
    Документация: https://www.chess.com/clubs/forum/view/api
    """
    
    def __init__(self):
        self.base_url = "https://api.chess.com/pub"
        self.headers = {
            "User-Agent": "OmskChessBroadcast/1.0 (ПМЭФ-2026; omsk@example.com)"
        }
        self.game_url = None
        self.game_id = None
        self.embed_url = None
        
    def test_connection(self) -> bool:
        """Проверка доступа к API"""
        try:
            response = requests.get(
                f"{self.base_url}/player/hikaru",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False
    
    def create_challenge(self, 
                        name: str = "ПМЭФ-2026: Омская область",
                        white: str = "Губернатор_Омской_области",
                        black: str = "Соперник") -> Dict:
        """
        СОЗДАНИЕ ВЫЗОВА НА ИГРУ
        Использует публичный challenge API
        """
        
        # Chess.com позволяет создавать открытые вызовы
        url = "https://api.chess.com/pub/challenge/open"
        
        # Формируем описание с брендированием
        description = f"""#ОмскШахматнаяСтолица

Прямая трансляция партии Губернатора Омской области на ПМЭФ-2026.

Турнир: Блицтурнир глав регионов
Дата: {datetime.now().strftime('%d.%m.%Y')}

Ссылка на турпортал: https://omsk.travel"""
        
        data = {
            "name": name,
            "rated": False,
            "time_control": "180+2",  # 3 минуты + 2 секунды
            "days": 1,
            "color": "random",
            "variant": "standard",
            "message": description
        }
        
        try:
            logger.info(f"📡 Создание игры на Chess.com: {name}")
            response = requests.post(url, headers=self.headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                self.game_id = result.get("id")
                self.game_url = f"https://www.chess.com/game/live/{self.game_id}"
                self.embed_url = f"https://www.chess.com/game/embed/live/{self.game_id}"
                
                logger.info(f"✅ Игра создана: {self.game_url}")
                return {
                    "success": True,
                    "game_id": self.game_id,
                    "url": self.game_url,
                    "embed_url": self.embed_url
                }
            else:
                logger.error(f"❌ Ошибка: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут при создании игры")
            return {"success": False, "error": "Connection timeout"}
        except requests.exceptions.ConnectionError:
            logger.error("❌ Ошибка подключения")
            return {"success": False, "error": "Connection error"}
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return {"success": False, "error": str(e)}
    
    def get_game_status(self, game_id: Optional[str] = None) -> Dict:
        """Получение статуса игры"""
        game_id = game_id or self.game_id
        if not game_id:
            return {"success": False, "error": "Нет ID игры"}
        
        url = f"{self.base_url}/game/live/{game_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_embed_code(self, game_id: Optional[str] = None, width: int = 600, height: int = 500) -> Optional[str]:
        """HTML код для встраивания"""
        game_id = game_id or self.game_id
        if not game_id:
            return None
        
        return f'<iframe src="https://www.chess.com/game/embed/live/{game_id}" width="{width}" height="{height}" frameborder="0" allowfullscreen></iframe>'
    
    def get_game_pgn(self, game_id: Optional[str] = None) -> Optional[str]:
        """Получение PGN игры"""
        game_id = game_id or self.game_id
        if not game_id:
            return None
        
        url = f"{self.base_url}/game/live/{game_id}/pgn"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except:
            return None


# Тестовая функция
def test_chesscom_integration():
    """Тестирование полного цикла"""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ CHESS.COM ИНТЕГРАЦИИ")
    print("=" * 60)
    
    chess = ChessComIntegration()
    
    # Проверка соединения
    print("\n📌 Проверка соединения...")
    if chess.test_connection():
        print("✅ API Chess.com доступен")
    else:
        print("❌ Ошибка подключения к API")
        return
    
    # Создание игры
    print("\n📌 Создание тестовой игры...")
    result = chess.create_challenge(
        name="ПМЭФ-2026: Тестовая трансляция",
        white="Губернатор_Омской_области",
        black="Соперник"
    )
    
    if result["success"]:
        print(f"\n✅ ИГРА СОЗДАНА!")
        print(f"🔗 Ссылка: {result['url']}")
        print(f"🖼️ Embed URL: {result['embed_url']}")
        print(f"\n📋 Код для встраивания:")
        print(chess.get_embed_code())
    else:
        print(f"\n❌ Ошибка: {result.get('error')}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_chesscom_integration()
