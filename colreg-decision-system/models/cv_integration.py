"""
Интеграция с cv-core для распознавания типов судов
Использует модели YOLO из cv-core-main для детекции и классификации
"""

import os
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import sys

# Добавляем путь к cv-core-main для импорта
CV_CORE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'cv-core-main')


@dataclass
class VesselDetectionResult:
    """
    Результат детекции судна с камеры
    
    Атрибуты:
        target_id: Уникальный идентификатор обнаруженного судна
        vessel_type: Тип судна (power_driven, sailing, fishing, nuc, ram, cbd)
        confidence: Уверенность классификации (0-1)
        bbox: Bounding box [x1, y1, x2, y2] в пикселях
        timestamp: Время обнаружения (ISO формат)
    """
    target_id: int
    vessel_type: str
    confidence: float
    bbox: List[int]
    timestamp: str


class CVCoreIntegration:
    """
    Интеграция с cv-core для определения типов судов по изображению
    
    Использует каскадную систему:
    1. YOLO11n для детекции судов
    2. EfficientNet-B0 для классификации (sailing vs power-driven)
    3. YOLO custom для детекции дневных фигур
    """
    
    def __init__(self, cv_core_path: str = None):
        """
        Инициализация интеграции с cv-core
        
        Args:
            cv_core_path: Путь к директории cv-core-main
        """
        self.cv_core_path = cv_core_path or CV_CORE_PATH
        self.pipeline = None
        self._initialized = False
    
    def initialize(self, binary_model_path: str = None, shapes_model_path: str = None) -> bool:
        """
        Инициализация ML пайплайна
        
        Args:
            binary_model_path: Путь к модели бинарной классификации
            shapes_model_path: Путь к модели детекции фигур
            
        Returns:
            True если инициализация успешна
        """
        if self._initialized:
            return True
        
        try:
            # Поиск путей к моделям по умолчанию
            if not binary_model_path:
                binary_model_path = os.path.join(
                    self.cv_core_path, 'models', 'best_model.pth'
                )
            if not shapes_model_path:
                shapes_model_path = os.path.join(
                    self.cv_core_path, 'models', 'best.pt'
                )
            
            # Проверка существования файлов моделей
            if not os.path.exists(binary_model_path):
                print(f"Предупреждение: Модель не найдена: {binary_model_path}")
                print("Работа без ML классификации - используется тип по умолчанию")
                return False
            
            if not os.path.exists(shapes_model_path):
                print(f"Предупреждение: Модель не найдена: {shapes_model_path}")
                print("Работа без ML классификации - используется тип по умолчанию")
                return False
            
            # Импорт MaritimeDetector из cv-core
            sys.path.insert(0, self.cv_core_path)
            from inference_pipeline import MaritimeDetector
            
            self.pipeline = MaritimeDetector(
                binary_model_path=binary_model_path,
                shapes_model_path=shapes_model_path
            )
            self._initialized = True
            print("CV-Core успешно инициализирован")
            return True
            
        except Exception as e:
            print(f"Ошибка инициализации CV-Core: {e}")
            print("Работа без ML классификации - используется тип по умолчанию")
            return False
    
    def process_image(self, image_path: str) -> List[VesselDetectionResult]:
        """
        Обработка изображения для обнаружения и классификации судов
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            Список результатов детекции
        """
        if not self._initialized:
            # Возвращаем пустой результат если ML не инициализирован
            print("CV-Core не инициализирован - возвращаем пустой результат")
            return []
        
        try:
            # Вызов пайплайна обработки
            json_result = self.pipeline.process_image(image_path)
            detections = json.loads(json_result)
            
            results = []
            for det in detections:
                results.append(VesselDetectionResult(
                    target_id=det['target_id'],
                    vessel_type=self._map_vessel_type(det['type']),
                    confidence=det['confidence'],
                    bbox=det['bbox'],
                    timestamp=det['timestamp']
                ))
            
            return results
            
        except Exception as e:
            print(f"Ошибка обработки изображения: {e}")
            return []
    
    def _map_vessel_type(self, cv_type: str) -> str:
        """
        Маппинг типов из cv-core в типы системы
        
        Args:
            cv_type: Тип судна от cv-core
            
        Returns:
            Тип судна в формате системы
        """
        type_mapping = {
            'Power-driven': 'power_driven',
            'Sailing': 'sailing',
            'Fishing': 'fishing',
            'NUC': 'nuc',
            'RAM': 'ram',
            'CBD': 'cbd'
        }
        return type_mapping.get(cv_type, 'power_driven')
    
    def detect_from_camera_stream(
        self, 
        camera_source: int = 0,
        callback: callable = None
    ) -> None:
        """
        Непрерывная обработка видеопотока с камеры
        
        Args:
            camera_source: Источник видео (0 для веб-камеры, или путь к файлу)
            callback: Функция обратного вызова для обработки результатов
        """
        import cv2
        
        if not self._initialized:
            print("CV-Core не инициализирован - невозможно обрабатывать видеопоток")
            return
        
        cap = cv2.VideoCapture(camera_source)
        
        if not cap.isOpened():
            print(f"Не удалось открыть камеру/видео: {camera_source}")
            return
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Обработка каждого N-го кадра для производительности
                if frame_count % 30 == 0:  # Каждый 30-й кадр (~1 раз в секунду при 30fps)
                    # Сохраняем временный файл для обработки
                    temp_path = "/tmp/frame.jpg"
                    cv2.imwrite(temp_path, frame)
                    
                    results = self.process_image(temp_path)
                    
                    if callback and results:
                        callback(results)
                
                frame_count += 1
                
                # Выход по клавише 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            cap.release()
            cv2.destroyAllWindows()
    
    def get_vessel_type_from_bbox(
        self, 
        image_path: str, 
        bbox: List[int]
    ) -> Optional[str]:
        """
        Определение типа судна для конкретного bounding box
        
        Args:
            image_path: Путь к изображению
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            Тип судна или None если не определено
        """
        detections = self.process_image(image_path)
        
        for det in detections:
            # Проверка перекрытия bbox
            if self._bbox_overlap(det.bbox, bbox) > 0.5:
                return det.vessel_type
        
        return None
    
    def _bbox_overlap(self, bbox1: List[int], bbox2: List[int]) -> float:
        """
        Расчет IoU (Intersection over Union) для двух bbox
        """
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    @staticmethod
    def create_mock_detection(
        lat: float, 
        lon: float, 
        speed: float, 
        course: float
    ) -> Dict[str, Any]:
        """
        Создание тестовых данных детекции для демонстрации без реальной ML модели
        
        Args:
            lat: Широта судна
            lon: Долгота судна
            speed: Скорость судна
            course: Курс судна
            
        Returns:
            Словарь с данными для создания объекта Vessel
        """
        import random
        from datetime import datetime, timezone
        
        vessel_types = ['power_driven', 'sailing', 'fishing', 'nuc', 'ram', 'cbd']
        
        return {
            'id': f"vessel_{random.randint(1000, 9999)}",
            'lat': lat + random.uniform(-0.01, 0.01),
            'lon': lon + random.uniform(-0.01, 0.01),
            'speed': speed + random.uniform(-2, 2),
            'course': (course + random.uniform(-45, 45)) % 360,
            'vessel_type': random.choice(vessel_types),
            'status': 'underway',
            'length': random.uniform(20, 200),
            'name': f"Vessel-{random.randint(1, 99)}",
            'detection_confidence': random.uniform(0.7, 0.99),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
