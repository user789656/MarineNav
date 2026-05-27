"""
Модуль интеграции с cv-core для распознавания типов судов.
Использует существующий inference_pipeline для классификации.
"""

import os
from typing import Optional, Dict, Any
from enum import Enum


class CVIntegrationError(Exception):
    """Ошибка интеграции с компьютерным зрением."""
    pass


def get_vessel_type_from_cv(vessel_type_str: str):
    """
    Преобразует строку типа судна из CV-модуля в enum VesselType.
    
    :param vessel_type_str: Строка типа судна от CV-модули
    :return: VesselType или None если не распознано
    """
    # Импортируем здесь чтобы избежать циклических зависимостей
    from ..decision_maker import VesselType
    
    type_mapping = {
        "Power-driven": VesselType.POWER_DRIVEN,
        "Sailing": VesselType.SAILING,
        "Fishing": VesselType.FISHING,
        "NUC": VesselType.NUC,
        "RAM": VesselType.RAM,
        "CBD": VesselType.CBD,
        # Дополнительные варианты написания
        "power-driven": VesselType.POWER_DRIVEN,
        "sailing": VesselType.SAILING,
        "fishing": VesselType.FISHING,
        "nuc": VesselType.NUC,
        "ram": VesselType.RAM,
        "cbd": VesselType.CBD,
    }
    
    return type_mapping.get(vessel_type_str)


def parse_cv_detections(cv_json_output: str):
    """
    Парсит JSON вывод от CV-модуля и преобразует в структурированные данные.
    
    :param cv_json_output: JSON строка от inference_pipeline.process_image()
    :return: Список словарей с данными о судах
    """
    import json
    
    try:
        detections = json.loads(cv_json_output)
    except json.JSONDecodeError as e:
        raise CVIntegrationError(f"Ошибка парсинга JSON от CV-модуля: {e}")
    
    if isinstance(detections, dict) and "error" in detections:
        raise CVIntegrationError(detections["error"])
    
    results = []
    for det in detections:
        vessel_type = get_vessel_type_from_cv(det.get("type", ""))
        
        results.append({
            "id": det.get("target_id", 0),
            "type": vessel_type,
            "type_str": det.get("type", ""),
            "confidence": det.get("confidence", 0.0),
            "bbox": det.get("bbox", []),
            "timestamp": det.get("timestamp", "")
        })
    
    return results


class CVProcessor:
    """
    Процессор для обработки изображений с камеры и определения типов судов.
    
    Интегрируется с existing cv-core inference pipeline.
    """
    
    def __init__(self, binary_model_path: str, shapes_model_path: str):
        """
        Инициализация CV процессора.
        
        :param binary_model_path: Путь к модели бинарной классификации
        :param shapes_model_path: Путь к модели детекции фигур
        """
        self.binary_model_path = binary_model_path
        self.shapes_model_path = shapes_model_path
        self._pipeline = None
    
    def _get_pipeline(self):
        """Ленивая загрузка pipeline."""
        if self._pipeline is None:
            try:
                # Пробуем импортировать из cv-core
                import sys
                cv_core_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "cv-core-main"
                )
                if os.path.exists(cv_core_path):
                    sys.path.insert(0, cv_core_path)
                
                from inference_pipeline import MaritimeDetector
                self._pipeline = MaritimeDetector(
                    self.binary_model_path,
                    self.shapes_model_path
                )
            except ImportError as e:
                raise CVIntegrationError(
                    f"Не удалось загрузить CV-модуль: {e}. "
                    "Убедитесь, что cv-core-main доступен и модели загружены."
                )
        return self._pipeline
    
    def process_image(self, image_path: str) -> list:
        """
        Обрабатывает изображение и возвращает данные о судах.
        
        :param image_path: Путь к изображению
        :return: Список словарей с данными о распознанных судах
        """
        if not os.path.exists(image_path):
            raise CVIntegrationError(f"Изображение не найдено: {image_path}")
        
        pipeline = self._get_pipeline()
        json_output = pipeline.process_image(image_path)
        
        return parse_cv_detections(json_output)
    
    def estimate_position_from_bbox(
        self,
        bbox: list,
        camera_params: Dict[str, float],
        own_pos: Any
    ) -> Optional[Any]:
        """
        Оценивает позицию судна на основе bounding box и параметров камеры.
        
        Это упрощенная оценка - в реальности требуется стереозрение или LiDAR.
        
        :param bbox: Bounding box [x1, y1, x2, y2]
        :param camera_params: Параметры камеры (fov, height, etc.)
        :param own_pos: Позиция своего судна (GeoPosition)
        :return: GeoPosition цели или None
        """
        from ..core import GeoPosition
        
        # Упрощенная эвристика для симуляции
        # В реальной системе здесь будет триангуляция
        x1, y1, x2, y2 = bbox
        
        # Центр объекта в пикселях
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Размер объекта как proxy для дистанции
        obj_size = max(x2 - x1, y2 - y1)
        
        # Эвристика: большие объекты = ближе
        # Это очень грубая оценка для симуляции
        base_distance = 1000  # метров
        estimated_distance = base_distance * (200 / max(obj_size, 10))
        
        # Предполагаем что камера направлена по курсу
        # В реальности нужен компас и гироскоп
        bearing_offset = (center_x - 320) / 640 * 90  # Для камеры 640x480
        
        # Получаем курс своего судна извне (здесь упрощение)
        estimated_bearing = 0  # Будет передано извне
        
        # Создаем примерную позицию
        target_pos = own_pos.offset_by(estimated_distance, estimated_bearing + bearing_offset)
        
        return target_pos
    
    def simulate_detection(
        self,
        target_id: int,
        vessel_type_str: str,
        confidence: float = 0.85
    ) -> Dict[str, Any]:
        """
        Создает симулированное обнаружение для тестирования.
        
        :param target_id: ID цели
        :param vessel_type_str: Тип судна строкой
        :param confidence: Уверенность детекции
        :return: Словарь с данными обнаружения
        """
        from datetime import datetime, timezone
        
        return {
            "id": target_id,
            "type": get_vessel_type_from_cv(vessel_type_str),
            "type_str": vessel_type_str,
            "confidence": confidence,
            "bbox": [100, 150, 300, 400],  # Примерный bbox
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
