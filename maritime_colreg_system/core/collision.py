"""
Модуль расчета параметров сближения судов (TCPA, DCPA, CPA).
"""

import math
from dataclasses import dataclass
from typing import Optional
from .geo import GeoPosition


@dataclass
class CollisionRisk:
    """
    Представляет параметры риска столкновения.
    
    :ivar tcpa: Время до точки ближайшего сближения (минуты), может быть отрицательным
    :ivar dcpa: Дистанция до точки ближайшего сближения (метры)
    :ivar cpd: Дистанция ближайшего сближения (метры) - то же что и dcpa
    :ivar is_risk: Флаг наличия риска столкновения
    """
    tcpa: float  # минуты
    dcpa: float  # метры
    is_risk: bool
    
    @property
    def cpd(self) -> float:
        """Дистанция ближайшего сближения (синоним dcpa)."""
        return self.dcpa


def calculate_tcpa_dcpa(
    my_pos: GeoPosition,
    my_speed_knots: float,
    my_course_deg: float,
    target_pos: GeoPosition,
    target_speed_knots: float,
    target_course_deg: float
) -> CollisionRisk:
    """
    Рассчитывает TCPA (Time to Closest Point of Approach) и DCPA 
    (Distance at Closest Point of Approach).
    
    :param my_pos: Позиция своего судна
    :param my_speed_knots: Скорость своего судна в узлах
    :param my_course_deg: Курс своего судна в градусах (0-360)
    :param target_pos: Позиция целевого судна
    :param target_speed_knots: Скорость целевого судна в узлах
    :param target_course_deg: Курс целевого судна в градусах (0-360)
    :return: Объект CollisionRisk с параметрами сближения
    """
    # Преобразуем узлы в м/с (1 узел = 0.514444 м/с)
    kts_to_ms = 0.514444
    my_speed = my_speed_knots * kts_to_ms
    target_speed = target_speed_knots * kts_to_ms
    
    # Вычисляем векторы скоростей
    my_course_rad = math.radians(my_course_deg)
    target_course_rad = math.radians(target_course_deg)
    
    # Вектор скорости своего судна (x - восток, y - север)
    my_vx = my_speed * math.sin(my_course_rad)
    my_vy = my_speed * math.cos(my_course_rad)
    
    # Вектор скорости целевого судна
    target_vx = target_speed * math.sin(target_course_rad)
    target_vy = target_speed * math.cos(target_course_rad)
    
    # Относительный вектор скорости (целевое судно относительно нашего)
    rel_vx = target_vx - my_vx
    rel_vy = target_vy - my_vy
    
    # Начальная относительная позиция (в метрах)
    # Используем локальную систему координат с началом в нашем судне
    dx = (target_pos.lon - my_pos.lon) * 111320 * math.cos(math.radians(my_pos.lat))
    dy = (target_pos.lat - my_pos.lat) * 111320
    
    # Расстояние до цели
    distance = math.sqrt(dx * dx + dy * dy)
    
    if distance < 1:  # Судна слишком близко
        return CollisionRisk(tcpa=0.0, dcpa=0.0, is_risk=True)
    
    # Скалярное произведение относительной позиции и относительной скорости
    dot_product = dx * rel_vx + dy * rel_vy
    
    # Квадрат относительной скорости
    rel_speed_sq = rel_vx * rel_vx + rel_vy * rel_vy
    
    if rel_speed_sq < 0.001:  # Относительное движение почти нулевое
        return CollisionRisk(tcpa=float('inf'), dcpa=distance, is_risk=False)
    
    # Время до CPA (в секундах)
    tcpa_seconds = -dot_product / rel_speed_sq
    
    # Позиция CPA относительно нашего судна
    cpa_x = dx + rel_vx * tcpa_seconds
    cpa_y = dy + rel_vy * tcpa_seconds
    
    # DCPA (расстояние в точке CPA)
    dcpa = math.sqrt(cpa_x * cpa_x + cpa_y * cpa_y)
    
    # TCPA в минутах
    tcpa_minutes = tcpa_seconds / 60.0
    
    # Определяем наличие риска
    # Риск есть если TCPA положительный (судна сближаются) и DCPA меньше безопасной дистанции
    is_risk = tcpa_minutes > 0 and dcpa < 500  # 500м - порог риска
    
    return CollisionRisk(
        tcpa=tcpa_minutes,
        dcpa=dcpa,
        is_risk=is_risk
    )


def calculate_bearing_and_range(
    my_pos: GeoPosition,
    target_pos: GeoPosition
) -> tuple:
    """
    Вычисляет пеленг и дистанцию до цели.
    
    :return: (пеленг в градусах, дистанция в метрах)
    """
    bearing = my_pos.bearing_to(target_pos)
    range_m = my_pos.distance_to(target_pos)
    return bearing, range_m


def predict_position(
    start_pos: GeoPosition,
    speed_knots: float,
    course_deg: float,
    time_minutes: float
) -> GeoPosition:
    """
    Предсказывает позицию судна через заданное время.
    
    :param start_pos: Начальная позиция
    :param speed_knots: Скорость в узлах
    :param course_deg: Курс в градусах
    :param time_minutes: Время в минутах
    :return: Предсказанная позиция
    """
    # Конвертируем скорость в м/мин
    speed_m_per_min = speed_knots * 1852 / 60  # 1 узел = 1852 м/час
    distance_m = speed_m_per_min * time_minutes
    
    return start_pos.offset_by(distance_m, course_deg)
