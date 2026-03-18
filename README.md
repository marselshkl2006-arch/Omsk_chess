# Шахматная трансляция Омской области для ПМЭФ-2026

## 🏆 О проекте
Система для публичной трансляции шахматных партий с автоматическим брендированием Омской области. Разработано для участия Губернатора Омской области в блицтурнире ПМЭФ-2026.

## ✨ Возможности
- ✅ Трансляция партии в реальном времени через WebSocket
- ✅ Отдельные интерфейсы для оператора и зрителей
- ✅ Автоматическое брендирование #ОмскШахматнаяСтолица
- ✅ Генерация PGN с тегами региона
- ✅ QR-код со ссылкой на туристический портал
- ✅ Удобный ввод ходов (перетаскивание или текстовое поле)

## 🛠 Технологии
- **Backend:** Python, FastAPI, WebSocket, python-chess
- **Frontend:** HTML5, CSS3, JavaScript, chessboard.js, chess.js
- **Интеграции:** Lichess API (в разработке), OpenCV (планируется)

## 🚀 Быстрый старт

### Требования
- Python 3.8+
- Браузер с поддержкой JavaScript

### Установка и запуск
```bash
# Клонировать репозиторий
git clone https://github.com/ВАШ_ЛОГИН/omsk-chess-broadcast.git
cd omsk-chess-broadcast

# Запуск бэкенда
cd backend
python -m venv venv
source venv/bin/activate  # для Linux/Mac
pip install -r requirements.txt
python main.py --port 8001

# Запуск фронтенда (в отдельном терминале)
cd frontend
python -m http.server 8082
