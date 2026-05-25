"""
Модуль классов судов и их состояний
Определяет типы судов, их статус и основные параметры
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Tuple
import math


class VesselType(Enum):
    """Типы судов по МППСС-72"""
    POWER_DRIVEN = "power_driven"  # Судно с механическим двигателем
    SAILING = "sailing"  # Парусное судно
    FISHING = "fishing"  # Судно, занятое ловом рыбы
    NUC = "nuc"  # Судно, лишенное возможности управляться (Not Under Command)
    RAM = "ram"  # Судно, ограниченное в возможности маневрировать (Restricted Ability to Maneuver)
    CBD = "cbd"  # Судно, стесненное своей осадкой (Constrained By Draft)
    TOWING = "towing"  # Буксирующее судно
    SEAPLANE = "seaplane"  # Гидросамолет


class VesselStatus(Enum):
    """Статус судна"""
    UNDERWAY = "underway"  # На ходу
    ANCHORED = "anchored"  # На якоре
    MOORED = "moored"  # Ошвартовано
    AGROUND = "aground"  # На мели


@dataclass
class Position:
    """Географическая позиция"""
    lat: float  # Широта в градусах
    lon: float  # Долгота в градусах
    
    def distance_to(self, other: 'Position') -> float:
        """
        Расчет расстояния до другой позиции в морских милях
        Использует формулу гаверсинусов
        """
        R = 3440.065  # Радиус Земли в морских милях
        
        lat1_rad = math.radians(self.lat)
        lat2_rad = math.radians(other.lat)
        delta_lat = math.radians(other.lat - self.lat)
        delta_lon = math.radians(other.lon - self.lon)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def bearing_to(self, other: 'Position') -> float:
        """
        Расчет пеленга на другую позицию в градусах (0-360)
        """
        lat1_rad = math.radians(self.lat)
        lat2_rad = math.radians(other.lat)
        delta_lon = math.radians(other.lon - self.lon)
        
        x = math.sin(delta_lon) * math.cos(lat2_rad)
        y = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360


@dataclass
class Vessel:
    """
    Класс судна с основными параметрами
    
    Атрибуты:
        id: Уникальный идентификатор судна
        position: Текущая позиция (широта, долгота)
        speed: Скорость в узлах
        course: Курс в градусах (0-360)
        vessel_type: Тип судна по классификации МППСС-72
        status: Статус судна
        length: Длина судна в метрах
        name: Название судна (опционально)
    """
    id: str
    position: Position
    speed: float  # узлы
    course: float  # градусы 0-360
    vessel_type: VesselType = VesselType.POWER_DRIVEN
    status: VesselStatus = VesselStatus.UNDERWAY
    length: float = 0.0
    name: Optional[str] = None
    heading: Optional[float] = None  # Фактический курс (может отличаться от course)
    
    def __post_init__(self):
        """Нормализация курса после инициализации"""
        if self.course < 0 or self.course >= 360:
            self.course = self.course % 360
        if self.heading is not None and (self.heading < 0 or self.heading >= 360):
            self.heading = self.heading % 360
    
    def get_relative_bearing(self, other: 'Vessel') -> float:
        """
        Расчет относительного пеленга на другое судно
        Возвращает угол от 0 до 360 градусов относительно курса текущего судна
        0° - прямо по носу, 90° - правый траверз, 180° - по корме, 270° - левый траверз
        """
        true_bearing = self.position.bearing_to(other.position)
        relative = (true_bearing - self.course + 360) % 360
        return relative
    
    def is_overtaking(self, other: 'Vessel') -> bool:
        """
        Проверка, является ли текущее судно обгоняющим по отношению к другому
        Правило 13: угол более 22.5° позади траверза (т.е. > 112.5° от носа)
        """
        relative_bearing = self.get_relative_bearing(other)
        # Обгон - когда судно находится в секторе от 112.5° до 247.5°
        return 112.5 < relative_bearing < 247.5
    
    def is_head_on(self, other: 'Vessel') -> bool:
        """
        Проверка ситуации сближения лоб в лоб
        Правило 14: суда видят друг друга прямо или почти прямо по курсу
        """
        relative_bearing = self.get_relative_bearing(other)
        other_relative = other.get_relative_bearing(self)
        # Лоб в лоб - когда оба судна видят друг друга в пределах ±22.5° от носа
        return (relative_bearing <= 22.5 or relative_bearing >= 337.5) and \
               (other_relative <= 22.5 or other_relative >= 337.5)
    
    def is_crossing_from_right(self, other: 'Vessel') -> bool:
        """
        Проверка, пересекает ли другое судно курс справа
        Правило 15: другое судно на правой стороне должно уступить дорогу
        """
        relative_bearing = self.get_relative_bearing(other)
        # Другое судно справа - в секторе от 0° до 112.5° (исключая лоб в лоб)
        return 22.5 < relative_bearing <= 112.5
    
    def get_priority_level(self) -> int:
        """
        Возвращает уровень приоритета судна по МППСС-72
        Чем выше число, тем выше приоритет (судно имеет преимущество)
        
        Приоритеты (от высшего к низшему):
        7. NUC (лишенное возможности управляться)
        6. RAM (ограниченное в возможности маневрировать)
        5. CBD (стесненное осадкой) - только в узкостях
        4. Fishing (занятое ловом рыбы)
        3. Sailing (парусное)
        2. Power-driven (с механическим двигателем)
        1. Seaplane (гидросамолет)
        """
        priority_map = {
            VesselType.NUC: 7,
            VesselType.RAM: 6,
            VesselType.CBD: 5,
            VesselType.FISHING: 4,
            VesselType.SAILING: 3,
            VesselType.POWER_DRIVEN: 2,
            VesselType.TOWING: 2,
            VesselType.SEAPLANE: 1
        }
        return priority_map.get(self.vessel_type, 2)
    
    def to_dict(self) -> dict:
        """Сериализация судна в словарь"""
        return {
            'id': self.id,
            'lat': self.position.lat,
            'lon': self.position.lon,
            'speed': self.speed,
            'course': self.course,
            'vessel_type': self.vessel_type.value,
            'status': self.status.value,
            'length': self.length,
            'name': self.name,
            'heading': self.heading
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Vessel':
        """Создание судна из словаря"""
        return cls(
            id=data['id'],
            position=Position(lat=data['lat'], lon=data['lon']),
            speed=data['speed'],
            course=data['course'],
            vessel_type=VesselType(data.get('vessel_type', 'power_driven')),
            status=VesselStatus(data.get('status', 'underway')),
            length=data.get('length', 0.0),
            name=data.get('name'),
            heading=data.get('heading')
        )
