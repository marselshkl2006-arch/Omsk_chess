import os
import requests
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class LichessIntegration:
    def __init__(self):
        self.api_token = os.getenv("LICHESS_API_TOKEN")
        if not self.api_token:
            logger.warning("⚠️ LICHESS_API_TOKEN не найден в .env файле")
        else:
            logger.info(f"✅ Токен загружен: {self.api_token[:10]}...")

        self.base_url = "https://lichess.org"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}"
        }
        self.game_url = None
        self.game_id = None

    def test_token(self):
        """Проверка, что токен работает"""
        try:
            response = requests.get(
                f"{self.base_url}/api/account",
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Токен работает. Аккаунт: {data.get('username')}")
                return {"success": True, "username": data.get('username')}
            else:
                return {"success": False, "error": f"Ошибка: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_game(self, name="ПМЭФ-2026: Омская область"):
        """
        Создание открытой игры (челленджа) на Lichess.
        Это самый надежный способ для демонстрации.
        """
        if not self.api_token:
            return {"success": False, "error": "API токен не настроен"}

        # Эндпоинт для создания открытого челленджа
        url = f"{self.base_url}/api/challenge/open"

        # Настройки игры (блиц, как в задании)
        payload = {
            "rated": "false",  # Не рейтинговая
            "clock.limit": "180",  # 3 минуты
            "clock.increment": "2",  # +2 секунды
            "name": name,
            "variant": "standard",  # Классические шахматы
            "color": "random"  # Случайный цвет
        }

        try:
            logger.info(f"📡 Создание игры на Lichess: {name}")
            response = requests.post(url, headers=self.headers, data=payload)

            if response.status_code == 200:
                game_data = response.json()
                self.game_id = game_data.get("id")
                self.game_url = f"{self.base_url}/{self.game_id}"

                logger.info(f"✅ Игра создана: {self.game_url}")
                return {
                    "success": True,
                    "game_id": self.game_id,
                    "url": self.game_url,
                    "type": "game"  # Отмечаем, что это игра, а не трансляция
                }
            else:
                error_msg = f"Ошибка Lichess API: {response.status_code} - {response.text[:200]}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"❌ Ошибка: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

# Создаем глобальный экземпляр
lichess = LichessIntegration()

# Для тестирования
if __name__ == "__main__":
    print("🧪 Тестирование Lichess интеграции (создание игры)...")
    token_test = lichess.test_token()
    if token_test["success"]:
        print(f"✅ Аккаунт: {token_test['username']}")
        result = lichess.create_game("Тестовая игра Омской области")
        print("Результат:", result)
    else:
        print("❌ Ошибка токена:", token_test.get("error"))
