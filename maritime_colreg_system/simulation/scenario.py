"""
Модуль симуляции морских судов и их движения.
Генерирует сценарии расхождения для тестирования системы принятия решений.
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from ..core import GeoPosition
from ..decision_maker import VesselType


@dataclass
class SimulatedVessel:
    """Представляет симулированное судно."""
    id: int
    pos: GeoPosition
    speed: float  # узлы
    course: float  # градусы (0-360)
    vessel_type: VesselType
    length: float = 50.0  # метров
    name: str = ""
    destination: Optional[GeoPosition] = None  # Целевая точка назначения
    
    def update_position(self, time_delta_minutes: float):
        """
        Обновляет позицию судна на основе скорости и курса.
        
        :param time_delta_minutes: Прошедшее время в минутах
        """
        # Скорость в м/мин: узлы * 1852 / 60
        distance_m = self.speed * 1852 / 60 * time_delta_minutes
        self.pos = self.pos.offset_by(distance_m, self.course)
    
    def update_course_to_destination(self):
        """Обновляет курс для движения к целевой точке."""
        if self.destination:
            self.course = self.pos.bearing_to(self.destination)
    
    def to_dict(self) -> dict:
        """Преобразует судно в словарь для JSON сериализации."""
        return {
            "id": self.id,
            "lat": self.pos.lat,
            "lon": self.pos.lon,
            "speed": self.speed,
            "course": self.course,
            "vessel_type": self.vessel_type.name,
            "length": self.length,
            "name": self.name,
            "destination": {"lat": self.destination.lat, "lon": self.destination.lon} if self.destination else None
        }


@dataclass
class ScenarioConfig:
    """Конфигурация для генерации сценариев."""
    num_vessels: int = 5  # Количество других судов
    max_distance_nm: float = 10.0  # Максимальная дистанция в морских милях
    own_speed_range: tuple = field(default_factory=lambda: (10.0, 15.0))
    target_speed_range: tuple = field(default_factory=lambda: (5.0, 20.0))
    risk_scenarios: bool = True  # Генерировать рискованные сближения


class ScenarioGenerator:
    """
    Генератор сценариев расхождения судов.
    
    Создает реалистичные ситуации с несколькими судами для тестирования
    модуля принятия решений COLREG.
    """
    
    VESSEL_NAMES = [
        "ATLANTIC STAR", "BALTIC WIND", "NORTHERN LIGHT", "PACIFIC QUEEN",
        "OCEAN VOYAGER", "SEA BREEZE", "COASTAL TRADER", "DEEP HORIZON",
        "MARITIME SPIRIT", "HARBOR GUARDIAN", "WAVE RIDER", "STORM CHASER"
    ]
    
    # Границы морских зон (упрощенно - прямоугольные области воды)
    # Формат: (min_lat, max_lat, min_lon, max_lon)
    WATER_ZONES = [
        # Черное море near Новороссийск
        (44.5, 45.2, 37.0, 38.5),
        # Средиземное море
        (35.0, 36.5, 28.0, 30.0),
        # Балтийское море
        (54.0, 56.0, 19.0, 21.0),
    ]
    
    def __init__(self, seed: Optional[int] = None, water_zone_index: int = 0):
        """
        Инициализация генератора.
        
        :param seed: Seed для воспроизводимости (None для случайности)
        :param water_zone_index: Индекс морской зоны для генерации
        """
        if seed is not None:
            random.seed(seed)
        self.water_zone = self.WATER_ZONES[water_zone_index % len(self.WATER_ZONES)]
    
    def _is_in_water(self, lat: float, lon: float) -> bool:
        """Проверяет, находится ли точка в воде (в пределах морской зоны)."""
        min_lat, max_lat, min_lon, max_lon = self.water_zone
        return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
    
    def _generate_water_position(self, center_lat: float, center_lon: float, 
                                   max_distance_nm: float) -> GeoPosition:
        """Генерирует случайную позицию в воде."""
        max_attempts = 50
        for _ in range(max_attempts):
            # Генерируем случайную позицию в пределах зоны
            lat = random.uniform(self.water_zone[0], self.water_zone[1])
            lon = random.uniform(self.water_zone[2], self.water_zone[3])
            
            if self._is_in_water(lat, lon):
                return GeoPosition(lat=lat, lon=lon)
        
        # Если не удалось сгенерировать, возвращаем точку в центре зоны
        center_lat = (self.water_zone[0] + self.water_zone[1]) / 2
        center_lon = (self.water_zone[2] + self.water_zone[3]) / 2
        return GeoPosition(lat=center_lat, lon=center_lon)
    
    def generate_own_vessel(
        self,
        start_lat: float = 44.95,  # Пример: Новороссийск
        start_lon: float = 37.50,
        speed_range: tuple = (10.0, 15.0),
        destination_lat: Optional[float] = None,
        destination_lon: Optional[float] = None
    ) -> SimulatedVessel:
        """
        Генерирует наше судно с целевой точкой назначения.
        
        :param start_lat: Начальная широта
        :param start_lon: Начальная долгота
        :param speed_range: Диапазон скорости (мин, макс)
        :param destination_lat: Широта цели (если None, генерируется автоматически)
        :param destination_lon: Долгота цели (если None, генерируется автоматически)
        :return: SimulatedVessel для нашего судна
        """
        speed = random.uniform(*speed_range)
        
        # Если цель не задана, генерируем её в пределах морской зоны
        if destination_lat is None or destination_lon is None:
            # Цель должна быть на расстоянии 20-50 миль от старта
            dest_bearing = random.uniform(0, 360)
            dest_distance_m = random.uniform(20 * 1852, 50 * 1852)
            dest_pos = GeoPosition(lat=start_lat, lon=start_lon).offset_by(dest_distance_m, dest_bearing)
            
            # Убедимся, что цель в воде
            if not self._is_in_water(dest_pos.lat, dest_pos.lon):
                dest_pos = self._generate_water_position(start_lat, start_lon, 50)
        else:
            dest_pos = GeoPosition(lat=destination_lat, lon=destination_lon)
        
        # Начальный курс к цели
        initial_course = GeoPosition(lat=start_lat, lon=start_lon).bearing_to(dest_pos)
        
        vessel = SimulatedVessel(
            id=0,
            pos=GeoPosition(lat=start_lat, lon=start_lon),
            speed=speed,
            course=initial_course,
            vessel_type=VesselType.POWER_DRIVEN,
            length=150.0,
            name="OUR VESSEL",
            destination=dest_pos
        )
        
        return vessel
    
    def generate_target_vessel(
        self,
        own_vessel: SimulatedVessel,
        max_distance_nm: float = 10.0,
        create_risk: bool = True,
        vessel_id: int = 1
    ) -> SimulatedVessel:
        """
        Генерирует целевое судно относительно нашего.
        
        :param own_vessel: Наше судно
        :param max_distance_nm: Максимальная дистанция в морских милях
        :param create_risk: Если True, создает ситуацию риска столкновения
        :param vessel_id: ID судна
        :return: SimulatedVessel цели
        """
        # Конвертируем морские мили в метры
        max_distance_m = max_distance_nm * 1852
        
        # Выбираем случайную дистанцию и пеленг
        if create_risk:
            # Для рискованных ситуаций - ближе и на коллизионном курсе
            distance_m = random.uniform(1000, max_distance_m * 0.5)
            bearing = own_vessel.course + random.uniform(-30, 30)
        else:
            distance_m = random.uniform(max_distance_m * 0.3, max_distance_m)
            bearing = random.uniform(0, 360)
        
        # Позиция цели - генерируем только в воде
        target_pos = self._generate_water_position(own_vessel.pos.lat, own_vessel.pos.lon, max_distance_nm)
        
        # Выбор типа судна
        type_weights = [
            (VesselType.POWER_DRIVEN, 0.6),
            (VesselType.SAILING, 0.15),
            (VesselType.FISHING, 0.15),
            (VesselType.NUC, 0.03),
            (VesselType.RAM, 0.05),
            (VesselType.CBD, 0.02)
        ]
        
        vessel_type = random.choices(
            [t[0] for t in type_weights],
            weights=[t[1] for t in type_weights]
        )[0]
        
        # Скорость цели
        speed = random.uniform(5.0, 20.0)
        
        # Курс цели - также с целевой точкой
        if create_risk:
            # Создаем коллизионный курс - цель движется к нашему судну или пересекает курс
            reciprocal_course = (own_vessel.course + 180) % 360
            course = reciprocal_course + random.uniform(-15, 15)
        else:
            course = random.uniform(0, 360)
        
        # Генерируем целевую точку для другого судна
        dest_bearing = random.uniform(0, 360)
        dest_distance_m = random.uniform(30 * 1852, 80 * 1852)
        dest_pos = target_pos.offset_by(dest_distance_m, dest_bearing)
        
        # Убедимся, что цель в воде
        if not self._is_in_water(dest_pos.lat, dest_pos.lon):
            dest_pos = self._generate_water_position(target_pos.lat, target_pos.lon, 50)
        
        # Длина судна в зависимости от типа
        length_map = {
            VesselType.POWER_DRIVEN: random.uniform(50, 300),
            VesselType.SAILING: random.uniform(10, 50),
            VesselType.FISHING: random.uniform(20, 80),
            VesselType.NUC: random.uniform(100, 200),
            VesselType.RAM: random.uniform(80, 150),
            VesselType.CBD: random.uniform(200, 400)
        }
        
        name = random.choice(self.VESSEL_NAMES)
        
        return SimulatedVessel(
            id=vessel_id,
            pos=target_pos,
            speed=speed,
            course=course,
            vessel_type=vessel_type,
            length=length_map[vessel_type],
            name=name,
            destination=dest_pos
        )
    
    def generate_scenario(
        self,
        start_lat: float = 44.95,
        start_lon: float = 37.50,
        num_targets: int = 5,
        create_risks: bool = True
    ) -> tuple:
        """
        Генерирует полный сценарий с нашим судном и целями.
        
        :param start_lat: Начальная широта
        :param start_lon: Начальная долгота
        :param num_targets: Количество целевых судов
        :param create_risks: Генерировать рискованные ситуации
        :return: (own_vessel, list of target_vessels)
        """
        # Генерируем наше судно
        own_vessel = self.generate_own_vessel(start_lat, start_lon)
        
        # Генерируем целевые суда
        targets = []
        for i in range(num_targets):
            # Каждое N-ное судно создаем как рискованное
            is_risk = create_risks and (i < num_targets // 2 or random.random() < 0.5)
            
            target = self.generate_target_vessel(
                own_vessel,
                max_distance_nm=10.0,
                create_risk=is_risk,
                vessel_id=i + 1
            )
            targets.append(target)
        
        return own_vessel, targets
    
    def update_scenario(
        self,
        own_vessel: SimulatedVessel,
        targets: List[SimulatedVessel],
        time_delta_minutes: float = 1.0
    ):
        """
        Обновляет позиции всех судов в сценарии.
        Судна движутся к своим целевым точкам, но при маневрах расхождения
        временно отклоняются от курса к цели.
        
        :param own_vessel: Наше судно
        :param targets: Список целевых судов
        :param time_delta_minutes: Шаг времени в минутах
        """
        # Обновляем наше судно - оно всегда стремится к цели
        # Сначала обновляем курс к цели (если нет активного маневра расхождения)
        own_vessel.update_course_to_destination()
        own_vessel.update_position(time_delta_minutes)
        
        # Обновляем цели - они также движутся к своим целям
        for target in targets:
            # Цели также стремятся к своим целям
            target.update_course_to_destination()
            target.update_position(time_delta_minutes)
    
    def apply_decision_to_vessel(
        self,
        vessel: SimulatedVessel,
        new_course: Optional[float],
        new_speed: Optional[float]
    ):
        """
        Применяет решение к судну (изменяет курс/скорость).
        После маневра расхождения судно вернется к курсу на цель.
        
        :param vessel: Судно
        :param new_course: Новый курс или None
        :param new_speed: Новая скорость или None
        """
        if new_course is not None:
            vessel.course = new_course
        
        if new_speed is not None:
            vessel.speed = new_speed
    
    def remove_passed_vessels(
        self,
        own_vessel: SimulatedVessel,
        targets: List[SimulatedVessel],
        max_distance_nm: float = 15.0
    ) -> List[SimulatedVessel]:
        """
        Удаляет суда, которые вышли за пределы видимости.
        
        :param own_vessel: Наше судно
        :param targets: Список целей
        :param max_distance_nm: Максимальная дистанция видимости
        :return: Обновленный список целей
        """
        max_distance_m = max_distance_nm * 1852
        
        active_targets = []
        for target in targets:
            distance = own_vessel.pos.distance_to(target.pos)
            if distance <= max_distance_m:
                active_targets.append(target)
        
        return active_targets
    
    def spawn_new_vessels(
        self,
        own_vessel: SimulatedVessel,
        existing_targets: List[SimulatedVessel],
        min_targets: int = 3,
        max_targets: int = 8
    ) -> List[SimulatedVessel]:
        """
        Добавляет новые суда если их слишком мало.
        
        :param own_vessel: Наше судно
        :param existing_targets: Существующие цели
        :param min_targets: Минимальное количество целей
        :param max_targets: Максимальное количество целей
        :return: Обновленный список целей
        """
        targets = existing_targets.copy()
        
        while len(targets) < min_targets:
            new_id = max([t.id for t in targets], default=0) + 1
            create_risk = random.random() < 0.4
            
            new_target = self.generate_target_vessel(
                own_vessel,
                max_distance_nm=10.0,
                create_risk=create_risk,
                vessel_id=new_id
            )
            targets.append(new_target)
        
        # Ограничиваем максимальное количество
        if len(targets) > max_targets:
            targets = targets[:max_targets]
        
        return targets
