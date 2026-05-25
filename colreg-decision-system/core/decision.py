"""
Модуль принятия решений по МППСС-72
Определяет необходимые маневры и сигналы для расхождения с судами
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from .vessel import Vessel, VesselType
from .collision import CollisionAnalyzer, CollisionRisk, EncounterSituation


class ManeuverType(Enum):
    """Типы маневров"""
    KEEP_COURSE = "keep_course"  # Сохранять курс и скорость
    TURN_STARBOARD = "turn_starboard"  # Поворот вправо
    TURN_PORT = "turn_port"  # Поворот влево
    REDUCE_SPEED = "reduce_speed"  # Уменьшить скорость
    STOP = "stop"  # Остановиться
    REVERSE = "reverse"  # Задний ход
    INCREASE_SPEED = "increase_speed"  # Увеличить скорость (редко)


@dataclass
class ManeuverAction:
    """
    Рекомендация по маневру
    
    Атрибуты:
        maneuver_type: Тип маневра
        description: Текстовое описание действия
        rule_number: Номер правила МППСС-72
        sound_signal: Звуковой сигнал (если применимо)
        light_signal: Световой сигнал (если применимо)
        priority: Приоритет маневра (1 - высший)
        target_vessel_id: ID судна, с которым расходимся
    """
    maneuver_type: ManeuverType
    description: str
    rule_number: int
    sound_signal: Optional[str] = None
    light_signal: Optional[str] = None
    priority: int = 5
    target_vessel_id: Optional[str] = None


@dataclass
class DecisionResult:
    """
    Полный результат принятия решения
    
    Атрибуты:
        actions: Список рекомендованных маневров
        warnings: Предупреждения
        situation_summary: Краткое описание ситуации
        has_collision_risk: Флаг наличия опасности столкновения
    """
    actions: List[ManeuverAction]
    warnings: List[str]
    situation_summary: str
    has_collision_risk: bool


class COLREGDecisionMaker:
    """
    Система принятия решений по правилам МППСС-72
    
    Анализирует ситуацию и рекомендует действия для безопасного расхождения
    """
    
    # Пороги для принятия решений
    HIGH_RISK_TCPA = 6.0  # минуты
    HIGH_RISK_DCPA = 0.25  # морские мили
    
    def __init__(self, collision_analyzer: CollisionAnalyzer = None):
        """
        Инициализация системы принятия решений
        
        Args:
            collision_analyzer: Анализатор столкновений (создается по умолчанию если не указан)
        """
        self.analyzer = collision_analyzer or CollisionAnalyzer()
    
    def _get_sound_signal(self, maneuver: ManeuverType) -> str:
        """Возвращает звуковой сигнал для маневра по Правилу 34"""
        signals = {
            ManeuverType.TURN_STARBOARD: "1 короткий гудок (изменяю курс вправо)",
            ManeuverType.TURN_PORT: "2 коротких гудка (изменяю курс влево)",
            ManeuverType.REVERSE: "3 коротких гудка (работаю на задний ход)",
            ManeuverType.STOP: "3 коротких гудка (останавливаюсь)",
        }
        return signals.get(maneuver, None)
    
    def _get_light_signal(self, maneuver: ManeuverType) -> str:
        """Возвращает световой сигнал для маневра по Правилу 34"""
        signals = {
            ManeuverType.TURN_STARBOARD: "1 вспышка белого огня (вправо)",
            ManeuverType.TURN_PORT: "2 вспышки белого огня (влево)",
            ManeuverType.REVERSE: "3 вспышки белого огня (задний ход)",
        }
        return signals.get(maneuver, None)
    
    def decide_for_situation(
        self, 
        own_ship: Vessel, 
        target_ship: Vessel,
        collision_risk: CollisionRisk,
        encounter: EncounterSituation
    ) -> List[ManeuverAction]:
        """
        Принятие решения для конкретной ситуации встречи
        
        Args:
            own_ship: Свое судно
            target_ship: Целевое судно
            collision_risk: Результат анализа риска столкновения
            encounter: Классификация ситуации
            
        Returns:
            Список рекомендованных маневров
        """
        actions = []
        
        # Если нет опасности столкновения
        if not collision_risk.is_risk:
            actions.append(ManeuverAction(
                maneuver_type=ManeuverType.KEEP_COURSE,
                description="Сохранять курс и скорость - опасность столкновения отсутствует",
                rule_number=17,
                priority=5,
                target_vessel_id=target_ship.id
            ))
            return actions
        
        # Определение действий на основе типа ситуации
        situation = encounter.situation_type
        give_way = encounter.give_way_vessel_id
        
        # Правило 13: Обгон
        if situation == 'overtaking':
            if give_way == own_ship.id:
                # Мы обгоняем - должны уступить
                actions.append(ManeuverAction(
                    maneuver_type=ManeuverType.TURN_STARBOARD,
                    description=f"Обгон: изменить курс вправо для расхождения с судном {target_ship.id}",
                    rule_number=13,
                    sound_signal=self._get_sound_signal(ManeuverType.TURN_STARBOARD),
                    light_signal=self._get_light_signal(ManeuverType.TURN_STARBOARD),
                    priority=1,
                    target_vessel_id=target_ship.id
                ))
                # При высокой опасности - дополнительно уменьшить скорость
                if collision_risk.risk_level in ['high', 'critical']:
                    actions.append(ManeuverAction(
                        maneuver_type=ManeuverType.REDUCE_SPEED,
                        description="Уменьшить скорость для безопасного расхождения",
                        rule_number=16,
                        priority=2,
                        target_vessel_id=target_ship.id
                    ))
            else:
                # Нас обгоняют - сохраняем курс
                actions.append(ManeuverAction(
                    maneuver_type=ManeuverType.KEEP_COURSE,
                    description="Нас обгоняют - сохранять курс и скорость (Правило 17)",
                    rule_number=17,
                    priority=4,
                    target_vessel_id=target_ship.id
                ))
        
        # Правило 14: Лоб в лоб
        elif situation == 'head_on':
            actions.append(ManeuverAction(
                maneuver_type=ManeuverType.TURN_STARBOARD,
                description=f"Лоб в лоб: изменить курс вправо для расхождения с судном {target_ship.id}",
                rule_number=14,
                sound_signal=self._get_sound_signal(ManeuverType.TURN_STARBOARD),
                light_signal=self._get_light_signal(ManeuverType.TURN_STARBOARD),
                priority=1,
                target_vessel_id=target_ship.id
            ))
            
            # При критической опасности - комбинированный маневр
            if collision_risk.risk_level == 'critical':
                actions.append(ManeuverAction(
                    maneuver_type=ManeuverType.REDUCE_SPEED,
                    description="Критическая опасность: уменьшить скорость и дать задний ход при необходимости",
                    rule_number=8,
                    sound_signal=self._get_sound_signal(ManeuverType.REVERSE),
                    priority=1,
                    target_vessel_id=target_ship.id
                ))
        
        # Правило 15: Пересечение курсов
        elif situation == 'crossing':
            if give_way == own_ship.id:
                # Мы уступаем - судно справа
                actions.append(ManeuverAction(
                    maneuver_type=ManeuverType.TURN_STARBOARD,
                    description=f"Пересечение: судно справа, изменить курс вправо для расхождения",
                    rule_number=15,
                    sound_signal=self._get_sound_signal(ManeuverType.TURN_STARBOARD),
                    light_signal=self._get_light_signal(ManeuverType.TURN_STARBOARD),
                    priority=1,
                    target_vessel_id=target_ship.id
                ))
                
                # Важно: избегать пересечения курса другого судна у него по носу
                if collision_risk.tcpa < self.HIGH_RISK_TCPA:
                    actions.append(ManeuverAction(
                        maneuver_type=ManeuverType.REDUCE_SPEED,
                        description="Уменьшить скорость, чтобы пройти за кормой другого судна",
                        rule_number=16,
                        priority=2,
                        target_vessel_id=target_ship.id
                    ))
            else:
                # Мы сохраняем курс - судно слева
                actions.append(ManeuverAction(
                    maneuver_type=ManeuverType.KEEP_COURSE,
                    description="Судно слева уступает дорогу - сохранять курс и скорость",
                    rule_number=17,
                    priority=4,
                    target_vessel_id=target_ship.id
                ))
                
                # Если другое судно не уступает - действуем самостоятельно (Правило 17.a.ii)
                if collision_risk.risk_level in ['high', 'critical']:
                    actions.append(ManeuverAction(
                        maneuver_type=ManeuverType.TURN_STARBOARD,
                        description="Другое судно не уступает! Изменить курс вправо для избежания столкновения",
                        rule_number=17,
                        sound_signal=self._get_sound_signal(ManeuverType.TURN_STARBOARD),
                        light_signal=self._get_light_signal(ManeuverType.TURN_STARBOARD),
                        priority=1,
                        target_vessel_id=target_ship.id
                    ))
                    # Избегать изменения курса влево если судно слева от нас
                    actions.append(ManeuverAction(
                        maneuver_type=ManeuverType.AVOID_PORT_TURN,
                        description="ВНИМАНИЕ: Не изменять курс влево!",
                        rule_number=17,
                        priority=1,
                        target_vessel_id=target_ship.id
                    ))
        
        # Правило 18: Приоритеты по типу судна
        elif situation == 'priority':
            if give_way == own_ship.id:
                # Мы уступаем судну с более высоким приоритетом
                vessel_type_desc = self._get_vessel_type_description(target_ship.vessel_type)
                actions.append(ManeuverAction(
                    maneuver_type=ManeuverType.TURN_STARBOARD,
                    description=f"Уступить дорогу судну {vessel_type_desc} ({target_ship.id})",
                    rule_number=18,
                    sound_signal=self._get_sound_signal(ManeuverType.TURN_STARBOARD),
                    priority=1,
                    target_vessel_id=target_ship.id
                ))
            else:
                # Нам уступают
                actions.append(ManeuverAction(
                    maneuver_type=ManeuverType.KEEP_COURSE,
                    description=f"Судно {target_ship.id} должно уступить дорогу нашему типу судна",
                    rule_number=18,
                    priority=4,
                    target_vessel_id=target_ship.id
                ))
        
        # Правило 19: Ограниченная видимость
        # (должно активироваться отдельно при получении данных о видимости)
        
        return actions
    
    def _get_vessel_type_description(self, vessel_type: VesselType) -> str:
        """Возвращает описание типа судна"""
        descriptions = {
            VesselType.NUC: "лишенное возможности управляться (NUC)",
            VesselType.RAM: "ограниченное в возможности маневрировать (RAM)",
            VesselType.CBD: "стесненное осадкой (CBD)",
            VesselType.FISHING: "занятое ловом рыбы",
            VesselType.SAILING: "парусное",
            VesselType.POWER_DRIVEN: "с механическим двигателем",
            VesselType.TOWING: "буксирующее",
            VesselType.SEAPLANE: "гидросамолет"
        }
        return descriptions.get(vessel_type, "неизвестного типа")
    
    def make_decision(
        self, 
        own_ship: Vessel, 
        target_ships: List[Vessel],
        limited_visibility: bool = False
    ) -> DecisionResult:
        """
        Принятие решения для всех целевых судов
        
        Args:
            own_ship: Свое судно
            target_ships: Список целевых судов
            limited_visibility: Флаг ограниченной видимости
            
        Returns:
            DecisionResult с рекомендованными действиями
        """
        all_actions = []
        warnings = []
        has_risk = False
        
        # Анализ всех судов
        analysis = self.analyzer.analyze_all_targets(own_ship, target_ships)
        
        for target_id, result in analysis.items():
            target = result['vessel']
            risk = result['collision_risk']
            encounter = result['encounter_situation']
            
            if risk.is_risk:
                has_risk = True
                
                # Получение рекомендаций
                actions = self.decide_for_situation(own_ship, target, risk, encounter)
                all_actions.extend(actions)
                
                # Добавление предупреждений для высоких уровней риска
                if risk.risk_level == 'critical':
                    warnings.append(
                        f"КРИТИЧЕСКАЯ ОПАСНОСТЬ с судном {target_id}: "
                        f"TCPA={risk.tcpa:.1f} мин, DCPA={risk.dcpa:.2f} миль"
                    )
                elif risk.risk_level == 'high':
                    warnings.append(
                        f"ВЫСОКАЯ ОПАСНОСТЬ с судном {target_id}: "
                        f"TCPA={risk.tcpa:.1f} мин, DCPA={risk.dcpa:.2f} миль"
                    )
        
        # Правило 19: Ограниченная видимость
        if limited_visibility and has_risk:
            warnings.append("ОГРАНИЧЕННАЯ ВИДИМОСТЬ: следовать Правилу 19")
            warnings.append("Избегать изменения курса влево для судов впереди траверза")
            warnings.append("Быть готовым к немедленной остановке")
            
            # Добавить специальные рекомендации для ограниченной видимости
            all_actions.append(ManeuverAction(
                maneuver_type=ManeuverType.REDUCE_SPEED,
                description="Ограниченная видимость: уменьшить ход до безопасной скорости",
                rule_number=19,
                priority=1
            ))
        
        # Сортировка действий по приоритету
        all_actions.sort(key=lambda x: x.priority)
        
        # Формирование сводки
        if has_risk:
            situation_summary = f"Обнаружена опасность столкновения с {len([a for a in all_actions if a.target_vessel_id])} судном(ами)"
        else:
            situation_summary = "Опасность столкновения отсутствует. Продолжать движение."
        
        return DecisionResult(
            actions=all_actions,
            warnings=warnings,
            situation_summary=situation_summary,
            has_collision_risk=has_risk
        )
    
    def get_emergency_action(self, own_ship: Vessel, target_ship: Vessel) -> ManeuverAction:
        """
        Возвращает экстренное действие для избежания столкновения
        Используется когда столкновение неизбежно при стандартных маневрах
        
        Правило 2: Допускается отступление от правил для избежания непосредственной опасности
        """
        return ManeuverAction(
            maneuver_type=ManeuverType.STOP,
            description="ЭКСТРЕННОЕ ДЕЙСТВИЕ: Полная остановка и задний ход для избежания столкновения!",
            rule_number=2,
            sound_signal="5+ коротких гудков (сигнал тревоги) + 3 коротких (задний ход)",
            light_signal="5+ вспышек (сигнал тревоги)",
            priority=0,  # Высший приоритет
            target_vessel_id=target_ship.id
        )
