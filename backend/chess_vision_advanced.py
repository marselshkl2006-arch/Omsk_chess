import tensorflow as tf
import numpy as np
import cv2
import chess
from typing import Optional, List, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChessVisionAdvanced:
    def __init__(self, pieces_model_path: str = "models/pieces_model_saved"):
        self.pieces_model = None
        self.load_pieces_model(pieces_model_path)
        
    def load_pieces_model(self, model_path: str):
        """Загрузка модели для детекции фигур"""
        try:
            self.pieces_model = tf.keras.models.load_model(model_path)
            logger.info(f"✅ Модель загружена из {model_path}")
            logger.info(f"Вход: {self.pieces_model.input_shape}")
            logger.info(f"Выход: {self.pieces_model.output_shape}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки модели: {e}")
            self.pieces_model = None
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Предобработка изображения для модели"""
        # Модель ожидает размер 288x480
        resized = cv2.resize(image, (480, 288))
        
        # Нормализация
        normalized = resized.astype(np.float32) / 255.0
        
        # Добавляем batch dimension
        batched = np.expand_dims(normalized, axis=0)
        
        return batched
    
    def postprocess_prediction(self, prediction):
        """Постобработка выхода модели"""
        # Здесь нужно адаптировать под формат выхода вашей модели
        # По умолчанию возвращаем как есть
        return prediction
    
    def detect_pieces(self, image: np.ndarray) -> List[Dict]:
        """Детекция фигур на изображении"""
        if self.pieces_model is None:
            logger.warning("Модель не загружена, возвращаем заглушку")
            return self._dummy_detection()
        
        # Предобработка
        input_tensor = self.preprocess_image(image)
        
        # Инференс
        predictions = self.pieces_model.predict(input_tensor, verbose=0)
        
        # Постобработка
        results = self.postprocess_prediction(predictions)
        
        # Преобразуем в список детекций
        detections = self._parse_predictions(results)
        
        return detections
    
    def _parse_predictions(self, predictions):
        """Парсинг выходов модели в список детекций"""
        # Здесь нужно реализовать парсинг в зависимости от формата выхода
        # Пока возвращаем заглушку
        return []
    
    def _dummy_detection(self):
        """Заглушка для демо"""
        # Возвращаем случайные детекции
        import random
        detections = []
        for _ in range(10):
            detections.append({
                'bbox': [random.randint(0, 480), random.randint(0, 288), 
                        random.randint(10, 50), random.randint(10, 50)],
                'class': random.randint(0, 11),
                'score': random.random()
            })
        return detections
    
    def detect_move_from_image(self, image_bytes: bytes) -> Optional[str]:
        """Определение хода из изображения"""
        # Конвертируем байты в изображение
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return None
        
        # Детекция фигур
        detections = self.detect_pieces(image)
        
        # Здесь логика определения хода
        # Пока возвращаем тестовый ход
        if len(detections) > 0:
            return "e2e4"
        
        return None

# Для тестирования
if __name__ == "__main__":
    vision = ChessVisionAdvanced()
    
    # Тест с веб-камерой
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        detections = vision.detect_pieces(frame)
        print(f"Найдено детекций: {len(detections)}")
    cap.release()
