"""
Модуль принятия решений на основе МППСС-72 (COLREGs).
Содержит логику определения ситуации расхождения и выбора маневра.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Tuple
from ..core import GeoPosition, calculate_tcpa_dcpa, calculate_relative_bearing, angle_difference


class VesselType(Enum):
    """Типы судов по МППСС-72."""
    POWER_DRIVEN = "судно с механическим двигателем"
    SAILING = "парусное судно"
    FISHING = "судно, занятое ловом рыбы"
    NUC = "судно, лишенное возможности управляться"
    RAM = "судно, ограниченное в возможности маневрировать"
    CBD = "судно, стесненное своей осадкой"


class EncounterType(Enum):
    """Типы ситуаций сближения."""
    HEAD_ON = "встречный курс"  # Rule 14
    CROSSING_GIVE_WAY = "пересечение (уступаем)"  # Rule 15
    CROSSING_STAND_ON = "пересечение (мы стоим на курсе)"  # Rule 15
    OVERTAKING = "обгон"  # Rule 13
    NOT_APPLICABLE = "не применимо"


class ManeuverType(Enum):
    """Типы маневров."""
    ALTER_COURSE_STARBOARD = "изменить курс вправо"
    ALTER_COURSE_PORT = "изменить курс влево"
    REDUCE_SPEED = "уменьшить скорость"
    STOP = "остановиться"
    MAINTAIN_COURSE = "держать курс и скорость"
    MAINTAIN_COURSE_MONITOR = "держать курс, контролировать ситуацию"


@dataclass
class Signal:
    """Звуковой или световой сигнал по МППСС-72."""
    signal_type: str  # "sound" или "light"
    description: str  # Описание сигнала
    rule: int  # Номер правила
    pattern: str  # Паттерн сигнала (например, "один короткий")


@dataclass
class DecisionResult:
    """Результат принятия решения."""
    encounter_type: EncounterType
    maneuver: ManeuverType
    new_course: Optional[float]  # Новый курс в градусах
    new_speed: Optional[float]  # Новая скорость в узлах
    signals: List[Signal]
    target_vessel_id: int
    reasoning: str  # Объяснение решения
    risk_level: str  # "low", "medium", "high"


class COLREGDecisionMaker:
    """
    Модуль принятия решений на основе правил МППСС-72.
    
    Определяет тип ситуации сближения и рекомендует маневр
    в соответствии с международными правилами предупреждения столкновений.
    """
    
    # Пороги для определения ситуаций
    HEAD_ON_BEARING_THRESHOLD = 5.0  # градусов для встречного курса
    CROSSING_THRESHOLD = 112.5  # градусов для пересечения
    OVERTAKING_BEARING_THRESHOLD = 67.5  # градусов для обгона (сзади траверза)
    
    SAFE_DCPA_METERS = 500  # Минимальная безопасная дистанция сближения
    TCPA_THRESHOLD_MINUTES = 12  # Максимальное время до CPA для вмешательства
    
    def __init__(self, own_vessel_type: VesselType = VesselType.POWER_DRIVEN):
        """
        Инициализация модуля принятия решений.
        
        :param own_vessel_type: Тип своего судна
        """
        self.own_vessel_type = own_vessel_type
    
    def determine_encounter_type(
        self,
        relative_bearing: float,
        target_course: float,
        own_course: float
    ) -> EncounterType:
        """
        Определяет тип ситуации сближения на основе относительного пеленга и курсов.
        
        :param relative_bearing: Относительный пеленг цели (-180 до +180)
        :param target_course: Курс целевого судна (0-360)
        :param own_course: Курс своего судна (0-360)
        :return: Тип ситуации сближения
        """
        # Нормализуем относительный пеленг к диапазону [-180, 180]
        rel_bearing = angle_difference(0, relative_bearing)
        
        # Разница курсов
        course_diff = abs(angle_difference(own_course, target_course))
        
        # Проверка на обгон (Rule 13)
        # Обгон - когда цель находится более чем на 22.5° позади траверза
        if abs(rel_bearing) > (180 - self.OVERTAKING_BEARING_THRESHOLD):
            return EncounterType.OVERTAKING
        
        # Проверка на встречный курс (Rule 14)
        # Встречный - когда цель почти прямо по носу и курсы противоположны
        if (abs(rel_bearing) <= self.HEAD_ON_BEARING_THRESHOLD and 
            abs(course_diff - 180) <= 22.5):
            return EncounterType.HEAD_ON
        
        # Проверка на пересечение (Rule 15)
        # Цель справа - мы уступаем
        if 0 < rel_bearing <= self.CROSSING_THRESHOLD:
            return EncounterType.CROSSING_GIVE_WAY
        
        # Цель слева - мы стоим на курсе
        if -self.CROSSING_THRESHOLD <= rel_bearing < 0:
            return EncounterType.CROSSING_STAND_ON
        
        return EncounterType.NOT_APPLICABLE
    
    def get_priority(self, vessel_type: VesselType) -> int:
        """
        Возвращает приоритет судна согласно МППСС-72.
        Большее число = больший приоритет (должен уступить дорогу).
        
        Приоритеты (от низшего к высшему):
        1. Судно с механическим двигателем
        2. Парусное судно
        3. Судно, занятое ловом рыбы
        4. Судно, лишенное возможности управляться / ограниченное в маневре
        """
        priority_map = {
            VesselType.POWER_DRIVEN: 1,
            VesselType.SAILING: 2,
            VesselType.FISHING: 3,
            VesselType.NUC: 4,
            VesselType.RAM: 4,
            VesselType.CBD: 3
        }
        return priority_map.get(vessel_type, 1)
    
    def should_give_way(
        self,
        own_type: VesselType,
        target_type: VesselType,
        encounter_type: EncounterType
    ) -> bool:
        """
        Определяет, должно ли наше судно уступить дорогу.
        
        :param own_type: Тип нашего судна
        :param target_type: Тип целевого судна
        :param encounter_type: Тип ситуации сближения
        :return: True если должны уступить
        """
        #特殊情况： обгоняющее судно всегда уступает
        if encounter_type == EncounterType.OVERTAKING:
            return True
        
        #特殊情况： встречный курс - оба поворачивают вправо
        if encounter_type == EncounterType.HEAD_ON:
            return True  # Оба судна поворачивают вправо
        
        #特殊情况： пересечение - цель справа, мы уступаем
        if encounter_type == EncounterType.CROSSING_GIVE_WAY:
            return True
        
        #特殊情况： пересечение - цель слева, мы стоим на курсе
        if encounter_type == EncounterType.CROSSING_STAND_ON:
            return False
        
        # Проверка по приоритету типов судов
        own_priority = self.get_priority(own_type)
        target_priority = self.get_priority(target_type)
        
        if own_priority < target_priority:
            return True  # Наш приоритет ниже - уступаем
        elif own_priority > target_priority:
            return False  # Наш приоритет выше - стоим на курсе
        else:
            # Одинаковый приоритет - применяем стандартные правила
            return True  # По умолчанию уступаем для безопасности
    
    def generate_signals(
        self,
        maneuver: ManeuverType,
        encounter_type: EncounterType
    ) -> List[Signal]:
        """
        Генерирует звуковые и световые сигналы для маневра.
        
        Rule 34: Сигналы маневроуказания
        - Один короткий: изменяю курс вправо
        - Два коротких: изменяю курс влево
        - Три коротких: работаю машиной заднего хода
        
        Rule 34(d): Сомнения - 5+ коротких звуков
        """
        signals = []
        
        if maneuver == ManeuverType.ALTER_COURSE_STARBOARD:
            signals.append(Signal(
                signal_type="sound",
                description="Один короткий гудок",
                rule=34,
                pattern="•"
            ))
            signals.append(Signal(
                signal_type="light",
                description="Один проблеск белого огня",
                rule=34,
                pattern="•"
            ))
        
        elif maneuver == ManeuverType.ALTER_COURSE_PORT:
            signals.append(Signal(
                signal_type="sound",
                description="Два коротких гудка",
                rule=34,
                pattern="••"
            ))
            signals.append(Signal(
                signal_type="light",
                description="Два проблеска белого огня",
                rule=34,
                pattern="••"
            ))
        
        elif maneuver == ManeuverType.REDUCE_SPEED or maneuver == ManeuverType.STOP:
            signals.append(Signal(
                signal_type="sound",
                description="Три коротких гудка",
                rule=34,
                pattern="•••"
            ))
            signals.append(Signal(
                signal_type="light",
                description="Три проблеска белого огня",
                rule=34,
                pattern="•••"
            ))
        
        return signals
    
    def make_decision(
        self,
        own_pos: GeoPosition,
        own_speed: float,
        own_course: float,
        target_pos: GeoPosition,
        target_speed: float,
        target_course: float,
        target_type: VesselType,
        target_id: int
    ) -> DecisionResult:
        """
        Принимает решение о маневре расхождения с целью.
        
        :param own_pos: Позиция своего судна
        :param own_speed: Скорость своего судна (узлы)
        :param own_course: Курс своего судна (градусы)
        :param target_pos: Позиция целевого судна
        :param target_speed: Скорость целевого судна (узлы)
        :param target_course: Курс целевого судна (градусы)
        :param target_type: Тип целевого судна
        :param target_id: Идентификатор целевого судна
        :return: Решение с маневром и сигналами
        """
        # Расчет параметров сближения
        collision_risk = calculate_tcpa_dcpa(
            own_pos, own_speed, own_course,
            target_pos, target_speed, target_course
        )
        
        # Расчет пеленга на цель
        bearing = own_pos.bearing_to(target_pos)
        relative_bearing = calculate_relative_bearing(own_course, bearing)
        
        # Определение типа ситуации
        encounter_type = self.determine_encounter_type(
            relative_bearing, target_course, own_course
        )
        
        # Определение необходимости уступить
        should_give_way = self.should_give_way(
            self.own_vessel_type, target_type, encounter_type
        )
        
        # Оценка уровня риска
        if collision_risk.tcpa <= 0:
            risk_level = "low"
        elif collision_risk.dcpa < 200:
            risk_level = "high"
        elif collision_risk.dcpa < self.SAFE_DCPA_METERS:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Если нет риска столкновения
        if not collision_risk.is_risk or risk_level == "low":
            return DecisionResult(
                encounter_type=encounter_type,
                maneuver=ManeuverType.MAINTAIN_COURSE_MONITOR,
                new_course=None,
                new_speed=None,
                signals=[],
                target_vessel_id=target_id,
                reasoning=f"Риск столкновения отсутствует. DCPA={collision_risk.dcpa:.0f}м, TCPA={collision_risk.tcpa:.1f}мин",
                risk_level=risk_level
            )
        
        # Выбор маневра
        maneuver = ManeuverType.MAINTAIN_COURSE
        new_course = None
        new_speed = None
        reasoning = ""
        
        if encounter_type == EncounterType.HEAD_ON:
            # Rule 14: Встречный курс - оба поворачивают вправо
            maneuver = ManeuverType.ALTER_COURSE_STARBOARD
            new_course = (own_course + 30) % 360  # Поворот на 30° вправо
            reasoning = f"Правило 14: Встречный курс. Поворот вправо на 30°. DCPA={collision_risk.dcpa:.0f}м"
        
        elif encounter_type == EncounterType.CROSSING_GIVE_WAY:
            # Rule 15: Пересечение, цель справа - уступаем
            # Лучше всего повернуть вправо, чтобы пройти за кормой
            maneuver = ManeuverType.ALTER_COURSE_STARBOARD
            new_course = (own_course + 45) % 360  # Поворот на 45° вправо
            reasoning = f"Правило 15: Пересечение, цель справа. Поворот вправо на 45° для прохода за кормой. DCPA={collision_risk.dcpa:.0f}м"
        
        elif encounter_type == EncounterType.CROSSING_STAND_ON:
            # Rule 17: Стоящее на курсе судно должно держать курс
            # Но если становится ясно, что другое не уступает -采取行动
            maneuver = ManeuverType.MAINTAIN_COURSE
            new_speed = own_speed * 0.7  # Уменьшаем скорость как предосторожность
            reasoning = f"Правило 17: Держим курс, но уменьшаем скорость для безопасности. DCPA={collision_risk.dcpa:.0f}м"
        
        elif encounter_type == EncounterType.OVERTAKING:
            # Rule 13: Обгоняющее судно уступает дорогу
            # Поворачиваем вправо, чтобы обойти сзади
            maneuver = ManeuverType.ALTER_COURSE_STARBOARD
            new_course = (own_course + 20) % 360
            reasoning = f"Правило 13: Обгон. Уступаем дорогу, поворот вправо. DCPA={collision_risk.dcpa:.0f}м"
        
        else:
            # Стандартное действие для безопасности
            if should_give_way:
                maneuver = ManeuverType.ALTER_COURSE_STARBOARD
                new_course = (own_course + 30) % 360
                reasoning = f"Уступаем дорогу по типу судна. Поворот вправо. DCPA={collision_risk.dcpa:.0f}м"
            else:
                maneuver = ManeuverType.REDUCE_SPEED
                new_speed = own_speed * 0.5
                reasoning = f"Предосторожное снижение скорости. DCPA={collision_risk.dcpa:.0f}м"
        
        # Генерация сигналов
        signals = self.generate_signals(maneuver, encounter_type)
        
        return DecisionResult(
            encounter_type=encounter_type,
            maneuver=maneuver,
            new_course=new_course,
            new_speed=new_speed,
            signals=signals,
            target_vessel_id=target_id,
            reasoning=reasoning,
            risk_level=risk_level
        )
    
    def evaluate_multi_vessel_scenario(
        self,
        own_pos: GeoPosition,
        own_speed: float,
        own_course: float,
        targets: List[dict]
    ) -> List[DecisionResult]:
        """
        Оценивает ситуацию с несколькими целями и принимает решения.
        
        :param targets: Список целей с параметрами:
            - pos: GeoPosition
            - speed: float (узлы)
            - course: float (градусы)
            - type: VesselType
            - id: int
        :return: Список решений для каждой цели
        """
        decisions = []
        
        for target in targets:
            decision = self.make_decision(
                own_pos=own_pos,
                own_speed=own_speed,
                own_course=own_course,
                target_pos=target["pos"],
                target_speed=target["speed"],
                target_course=target["course"],
                target_type=target["type"],
                target_id=target["id"]
            )
            decisions.append(decision)
        
        # Сортируем по уровню риска (сначала высокий)
        risk_order = {"high": 0, "medium": 1, "low": 2}
        decisions.sort(key=lambda d: risk_order.get(d.risk_level, 3))
        
        return decisions
