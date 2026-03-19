"""
Интеграция с Chess.com для ПМЭФ-2026
Использует публичные игры Chess.com
"""

import requests
import logging
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChessComIntegration:
    def __init__(self):
        self.base_url = "https://api.chess.com/pub"
        self.headers = {"User-Agent": "OmskChessBroadcast/1.0"}
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
        except:
            return False
    
    def set_game_id(self, game_id: str) -> Dict:
        """Установка существующего ID игры"""
        self.game_id = game_id
        self.game_url = f"https://www.chess.com/game/live/{self.game_id}"
        self.embed_url = f"https://www.chess.com/game/embed/live/{self.game_id}"
        
        return {
            "success": True,
            "game_id": self.game_id,
            "url": self.game_url,
            "embed_url": self.embed_url
        }
    
    def get_embed_code(self, game_id: Optional[str] = None, width: int = 600, height: int = 500) -> Optional[str]:
        """HTML код для встраивания"""
        game_id = game_id or self.game_id
        if not game_id:
            return None
        return f'<iframe src="https://www.chess.com/game/embed/live/{game_id}" width="{width}" height="{height}" frameborder="0" allowfullscreen></iframe>'


# Тест
if __name__ == "__main__":
    chess = ChessComIntegration()
    if chess.test_connection():
        print("✅ Chess.com API доступен")
        # Используем демо-игру
        result = chess.set_game_id("123456789")
        print(f"✅ Игра: {result['url']}")
    else:
        print("❌ Chess.com API недоступен")
