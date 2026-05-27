"""
Модуль работы с геопространственными данными для морской навигации.
Содержит классы для представления координат, расчетов дистанций и пеленгов.
"""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class GeoPosition:
    """Представляет географическую позицию (широта, долгота)."""
    lat: float  # Широта в градусах (-90 до 90)
    lon: float  # Долгота в градусах (-180 до 180)
    
    def distance_to(self, other: 'GeoPosition') -> float:
        """
        Вычисляет расстояние до другой позиции в метрах.
        Использует формулу гаверсинусов.
        """
        R = 6371000  # Радиус Земли в метрах
        
        lat1_rad = math.radians(self.lat)
        lat2_rad = math.radians(other.lat)
        delta_lat = math.radians(other.lat - self.lat)
        delta_lon = math.radians(other.lon - self.lon)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def bearing_to(self, other: 'GeoPosition') -> float:
        """
        Вычисляет начальный пеленг (курс) до другой позиции в градусах (0-360).
        """
        lat1_rad = math.radians(self.lat)
        lat2_rad = math.radians(other.lat)
        delta_lon = math.radians(other.lon - self.lon)
        
        x = math.sin(delta_lon) * math.cos(lat2_rad)
        y = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360
    
    def offset_by(self, distance_meters: float, bearing_degrees: float) -> 'GeoPosition':
        """
        Возвращает новую позицию, смещенную на заданное расстояние по заданному пеленгу.
        """
        R = 6371000  # Радиус Земли в метрах
        
        lat1_rad = math.radians(self.lat)
        bearing_rad = math.radians(bearing_degrees)
        angular_distance = distance_meters / R
        
        lat2_rad = math.asin(
            math.sin(lat1_rad) * math.cos(angular_distance) +
            math.cos(lat1_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
        )
        
        lon2_rad = math.radians(self.lon) + math.atan2(
            math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat1_rad),
            math.cos(angular_distance) - math.sin(lat1_rad) * math.sin(lat2_rad)
        )
        
        return GeoPosition(
            lat=math.degrees(lat2_rad),
            lon=math.degrees(lon2_rad)
        )
    
    def to_dict(self) -> dict:
        """Преобразует позицию в словарь."""
        return {"lat": self.lat, "lon": self.lon}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GeoPosition':
        """Создает позицию из словаря."""
        return cls(lat=data["lat"], lon=data["lon"])


def calculate_relative_bearing(my_course: float, target_bearing: float) -> float:
    """
    Вычисляет относительный пеленг цели относительно курса своего судна.
    
    :param my_course: Курс своего судна в градусах (0-360)
    :param target_bearing: Истинный пеленг на цель в градусах (0-360)
    :return: Относительный пеленг в градусах (-180 до 180, где + по правому борту)
    """
    relative = (target_bearing - my_course + 180) % 360 - 180
    return relative


def normalize_angle(angle: float) -> float:
    """Нормализует угол к диапазону [0, 360)."""
    return angle % 360


def angle_difference(angle1: float, angle2: float) -> float:
    """
    Вычисляет минимальную разницу между двумя углами.
    Результат в диапазоне [-180, 180].
    """
    diff = (angle2 - angle1 + 180) % 360 - 180
    return diff
