"""
Модуль анализа столкновений
Расчет TCPA (Time to Closest Point of Approach) и DCPA (Distance at CPA)
Определение опасности столкновения
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import math
from .vessel import Vessel, Position


@dataclass
class CollisionRisk:
    """
    Результат анализа риска столкновения
    
    Атрибуты:
        tcpa: Время до точки максимального сближения (минуты), отрицательное если уже прошли
        dcpa: Дистанция в точке максимального сближения (морские мили)
        distance: Текущая дистанция между судами (морские мили)
        is_risk: Флаг наличия опасности столкновения
        risk_level: Уровень риска (low, medium, high, critical)
    """
    tcpa: float  # минуты
    dcpa: float  # морские мили
    distance: float  # морские мили
    is_risk: bool
    risk_level: str  # 'none', 'low', 'medium', 'high', 'critical'


@dataclass
class EncounterSituation:
    """
    Классификация ситуации встречи судов
    
    Атрибуты:
        situation_type: Тип ситуации (head_on, crossing, overtaking, none)
        give_way_vessel_id: ID судна, которое должно уступить дорогу
        stand_on_vessel_id: ID судна, которому должны уступить дорогу
        applicable_rule: Номер применимого правила МППСС-72
        description: Текстовое описание ситуации
    """
    situation_type: str
    give_way_vessel_id: Optional[str]
    stand_on_vessel_id: Optional[str]
    applicable_rule: int
    description: str


class CollisionAnalyzer:
    """
    Анализатор столкновений
    
    Рассчитывает TCPA/DCPA и определяет опасность столкновения
    на основе относительного движения судов
    """
    
    # Пороговые значения для определения опасности
    DEFAULT_DCPA_THRESHOLD = 0.5  # морские мили
    DEFAULT_TCPA_THRESHOLD = 12.0  # минуты
    
    def __init__(self, dcpa_threshold: float = None, tcpa_threshold: float = None):
        """
        Инициализация анализатора
        
        Args:
            dcpa_threshold: Порог DCPA для определения опасности (морские мили)
            tcpa_threshold: Порог TCPA для определения опасности (минуты)
        """
        self.dcpa_threshold = dcpa_threshold or self.DEFAULT_DCPA_THRESHOLD
        self.tcpa_threshold = tcpa_threshold or self.DEFAULT_TCPA_THRESHOLD
    
    def calculate_relative_motion(self, own_ship: Vessel, target_ship: Vessel) -> Tuple[float, float]:
        """
        Расчет относительной скорости и курса целевого судна
        
        Возвращает:
            (relative_speed, relative_course) - скорость и курс относительно своего судна
        """
        # Преобразование полярных координат в декартовы
        # Скорость в узлах, курс в градусах
        own_vx = own_ship.speed * math.sin(math.radians(own_ship.course))
        own_vy = own_ship.speed * math.cos(math.radians(own_ship.course))
        
        target_vx = target_ship.speed * math.sin(math.radians(target_ship.course))
        target_vy = target_ship.speed * math.cos(math.radians(target_ship.course))
        
        # Относительная скорость
        rel_vx = target_vx - own_vx
        rel_vy = target_vy - own_vy
        
        relative_speed = math.sqrt(rel_vx ** 2 + rel_vy ** 2)
        
        if relative_speed < 0.001:
            relative_course = 0.0
        else:
            relative_course = math.degrees(math.atan2(rel_vx, rel_vy))
            relative_course = (relative_course + 360) % 360
        
        return relative_speed, relative_course
    
    def calculate_tcpa_dcpa(self, own_ship: Vessel, target_ship: Vessel) -> CollisionRisk:
        """
        Расчет TCPA и DCPA между двумя судами
        
        Использует метод относительного движения для расчета
        времени и расстояния до точки максимального сближения
        """
        # Текущая дистанция
        distance = own_ship.position.distance_to(target_ship.position)
        
        # Пеленг на целевое судно
        bearing = own_ship.position.bearing_to(target_ship.position)
        
        # Относительное движение
        rel_speed, rel_course = self.calculate_relative_motion(own_ship, target_ship)
        
        # Угол между пеленгом и относительным курсом
        angle_diff = math.radians((rel_course - bearing + 360) % 360)
        
        # DCPA = distance * sin(angle_diff)
        dcpa = abs(distance * math.sin(angle_diff))
        
        # Расстояние до точки CPA
        range_to_cpa = distance * math.cos(angle_diff)
        
        # TCPA = range_to_cpa / relative_speed
        if rel_speed > 0.001:
            tcpa_minutes = (range_to_cpa / rel_speed) * 60  # конверсия часов в минуты
        else:
            tcpa_minutes = float('inf') if range_to_cpa > 0 else float('-inf')
        
        # Определение уровня риска
        is_risk = (dcpa < self.dcpa_threshold and 
                   tcpa_minutes > 0 and 
                   tcpa_minutes < self.tcpa_threshold)
        
        if not is_risk:
            if dcpa >= self.dcpa_threshold * 2:
                risk_level = 'none'
            elif tcpa_minutes <= 0:
                risk_level = 'none'  # Уже прошли точку сближения
            else:
                risk_level = 'low'
        else:
            # Оценка уровня риска на основе DCPA и TCPA
            dcpa_factor = dcpa / self.dcpa_threshold
            tcpa_factor = tcpa_minutes / self.tcpa_threshold
            
            if dcpa_factor < 0.25 and tcpa_factor < 0.25:
                risk_level = 'critical'
            elif dcpa_factor < 0.5 and tcpa_factor < 0.5:
                risk_level = 'high'
            else:
                risk_level = 'medium'
        
        return CollisionRisk(
            tcpa=tcpa_minutes,
            dcpa=dcpa,
            distance=distance,
            is_risk=is_risk,
            risk_level=risk_level
        )
    
    def classify_encounter(self, own_ship: Vessel, target_ship: Vessel) -> EncounterSituation:
        """
        Классификация ситуации встречи двух судов по МППСС-72
        
        Определяет тип ситуации и какое судно должно уступить дорогу
        """
        # Проверка приоритетов по типу судна (Правило 18)
        own_priority = own_ship.get_priority_level()
        target_priority = target_ship.get_priority_level()
        
        # Если одно судно имеет явный приоритет по типу
        if own_priority > target_priority:
            return EncounterSituation(
                situation_type='priority',
                give_way_vessel_id=target_ship.id,
                stand_on_vessel_id=own_ship.id,
                applicable_rule=18,
                description=f"Ваше судно ({own_ship.vessel_type.value}) имеет приоритет над {target_ship.vessel_type.value}"
            )
        elif target_priority > own_priority:
            return EncounterSituation(
                situation_type='priority',
                give_way_vessel_id=own_ship.id,
                stand_on_vessel_id=target_ship.id,
                applicable_rule=18,
                description=f"Судно {target_ship.vessel_type.value} имеет приоритет над вашим ({own_ship.vessel_type.value})"
            )
        
        # Оба судна одного типа - проверяем геометрическую ситуацию
        # Проверка на обгон (Правило 13)
        if own_ship.is_overtaking(target_ship):
            return EncounterSituation(
                situation_type='overtaking',
                give_way_vessel_id=own_ship.id,
                stand_on_vessel_id=target_ship.id,
                applicable_rule=13,
                description="Обгон - вы обгоняете другое судно и должны уступить дорогу"
            )
        elif target_ship.is_overtaking(own_ship):
            return EncounterSituation(
                situation_type='overtaking',
                give_way_vessel_id=target_ship.id,
                stand_on_vessel_id=own_ship.id,
                applicable_rule=13,
                description="Обгон - другое судно обгоняет вас, вы сохраняете курс и скорость"
            )
        
        # Проверка лоб в лоб (Правило 14)
        if own_ship.is_head_on(target_ship):
            return EncounterSituation(
                situation_type='head_on',
                give_way_vessel_id='both',
                stand_on_vessel_id='both',
                applicable_rule=14,
                description="Лоб в лоб - оба судна изменяют курс вправо"
            )
        
        # Проверка пересечения курсов (Правило 15)
        if own_ship.is_crossing_from_right(target_ship):
            return EncounterSituation(
                situation_type='crossing',
                give_way_vessel_id=target_ship.id,
                stand_on_vessel_id=own_ship.id,
                applicable_rule=15,
                description="Пересечение - другое судно справа, оно уступает дорогу"
            )
        elif target_ship.is_crossing_from_right(own_ship):
            return EncounterSituation(
                situation_type='crossing',
                give_way_vessel_id=own_ship.id,
                stand_on_vessel_id=target_ship.id,
                applicable_rule=15,
                description="Пересечение - другое судно слева, вы уступаете дорогу"
            )
        
        # Нет опасности или ситуация не определена
        return EncounterSituation(
            situation_type='none',
            give_way_vessel_id=None,
            stand_on_vessel_id=None,
            applicable_rule=0,
            description="Ситуация не требует действий по расхождению"
        )
    
    def analyze_all_targets(self, own_ship: Vessel, target_ships: list[Vessel]) -> dict:
        """
        Комплексный анализ всех целевых судов
        
        Возвращает словарь с результатами анализа для каждого судна
        """
        results = {}
        
        for target in target_ships:
            risk = self.calculate_tcpa_dcpa(own_ship, target)
            encounter = self.classify_encounter(own_ship, target)
            
            results[target.id] = {
                'vessel': target,
                'collision_risk': risk,
                'encounter_situation': encounter
            }
        
        return results
