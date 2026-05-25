"""
Модуль звуковых и световых сигналов по МППСС-72
Реализация Правил 34, 35 для сигналов маневроуказания и предупреждения
"""

from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass


class SoundSignalType(Enum):
    """Типы звуковых сигналов"""
    SHORT = "short"  # Короткий звук (~1 секунда)
    PROLONGED = "prolonged"  # Продолжительный звук (4-6 секунд)


class LightSignalType(Enum):
    """Типы световых сигналов"""
    FLASH = "flash"  # Вспышка
    MORSE = "morse"  # Азбука Морзе


@dataclass
class Signal:
    """Сигнал (звуковой или световой)"""
    signal_type: str
    description: str
    pattern: List[str]  # Последовательность сигналов
    meaning: str  # Значение сигнала
    rule_number: int  # Номер правила МППСС


class SoundSignals:
    """
    Звуковые сигналы по МППСС-72
    
    Правило 34: Сигналы маневроуказания и предупреждения
    Правило 35: Звуковые сигналы при ограниченной видимости
    """
    
    # Маневросигналы (Правило 34)
    MANEUVER_SIGNALS: Dict[str, Signal] = {
        'starboard': Signal(
            signal_type='sound',
            description='1 короткий гудок',
            pattern=['short'],
            meaning='Я изменяю свой курс вправо',
            rule_number=34
        ),
        'port': Signal(
            signal_type='sound',
            description='2 коротких гудка',
            pattern=['short', 'short'],
            meaning='Я изменяю свой курс влево',
            rule_number=34
        ),
        'astern': Signal(
            signal_type='sound',
            description='3 коротких гудка',
            pattern=['short', 'short', 'short'],
            meaning='Мои движители работают на задний ход',
            rule_number=34
        ),
        'doubt': Signal(
            signal_type='sound',
            description='5 или более коротких гудков',
            pattern=['short'] * 5,
            meaning='Сигнал предупреждения / сомнения в действиях другого судна',
            rule_number=34
        ),
        'overtake_starboard': Signal(
            signal_type='sound',
            description='2 продолжительных + 1 короткий',
            pattern=['prolonged', 'prolonged', 'short'],
            meaning='Я намереваюсь обогнать вас с правого борта',
            rule_number=34
        ),
        'overtake_port': Signal(
            signal_type='sound',
            description='2 продолжительных + 2 коротких',
            pattern=['prolonged', 'prolonged', 'short', 'short'],
            meaning='Я намереваюсь обогнать вас с левого борта',
            rule_number=34
        ),
        'overtake_agree': Signal(
            signal_type='sound',
            description='1 продолжительный + 1 короткий + 1 продолжительный + 1 короткий',
            pattern=['prolonged', 'short', 'prolonged', 'short'],
            meaning='Согласен на обгон',
            rule_number=34
        ),
        'overtake_danger': Signal(
            signal_type='sound',
            description='5 или более коротких гудков',
            pattern=['short'] * 5,
            meaning='Опасность обгона / не согласен',
            rule_number=34
        )
    }
    
    # Сигналы при ограниченной видимости (Правило 35)
    FOG_SIGNALS: Dict[str, Signal] = {
        'power_underway': Signal(
            signal_type='sound',
            description='1 продолжительный гудок каждые 2 минуты',
            pattern=['prolonged'],
            meaning='Судно с механическим двигателем на ходу',
            rule_number=35
        ),
        'power_stopped': Signal(
            signal_type='sound',
            description='2 продолжительных гудка каждые 2 минуты',
            pattern=['prolonged', 'prolonged'],
            meaning='Судно с механическим двигателем на ходу, но остановившееся',
            rule_number=35
        ),
        'nuc_ram': Signal(
            signal_type='sound',
            description='1 продолжительный + 2 коротких каждые 2 минуты',
            pattern=['prolonged', 'short', 'short'],
            meaning='Судно NUC, RAM, стесненное осадкой, парусное, рыболовное, буксирующее',
            rule_number=35
        ),
        'towing': Signal(
            signal_type='sound',
            description='1 продолжительный + 2 коротких каждые 2 минуты',
            pattern=['prolonged', 'short', 'short'],
            meaning='Буксирующее судно',
            rule_number=35
        ),
        'anchored': Signal(
            signal_type='sound',
            description='Быстрый звон колокола 5 секунд каждые 1 минуту',
            pattern=['bell_5s'],
            meaning='Судно на якоре',
            rule_number=35
        ),
        'aground': Signal(
            signal_type='sound',
            description='3 удара колокола + быстрый звон 5с + 3 удара колокола',
            pattern=['bell_3', 'bell_5s', 'bell_3'],
            meaning='Судно на мели',
            rule_number=35
        )
    }
    
    @classmethod
    def get_maneuver_signal(cls, maneuver: str) -> Optional[Signal]:
        """
        Получение звукового сигнала для маневра
        
        Args:
            maneuver: Тип маневра ('starboard', 'port', 'astern', 'doubt')
            
        Returns:
            Signal или None если не найдено
        """
        return cls.MANEUVER_SIGNALS.get(maneuver)
    
    @classmethod
    def get_fog_signal(cls, vessel_status: str) -> Optional[Signal]:
        """
        Получение звукового сигнала для условий ограниченной видимости
        
        Args:
            vessel_status: Статус судна ('power_underway', 'power_stopped', 'nuc_ram', etc.)
            
        Returns:
            Signal или None если не найдено
        """
        return cls.FOG_SIGNALS.get(vessel_status)
    
    @classmethod
    def get_all_maneuver_signals(cls) -> Dict[str, Signal]:
        """Возвращает все маневросигналы"""
        return cls.MANEUVER_SIGNALS.copy()
    
    @classmethod
    def get_all_fog_signals(cls) -> Dict[str, Signal]:
        """Возвращает все туманные сигналы"""
        return cls.FOG_SIGNALS.copy()


class LightSignals:
    """
    Световые сигналы по МППСС-72
    
    Правило 34: Световые сигналы маневроуказания
    Приложение 1: Технические характеристики огней
    """
    
    # Маневросигналы (Правило 34)
    MANEUVER_LIGHTS: Dict[str, Signal] = {
        'starboard': Signal(
            signal_type='light',
            description='1 вспышка белого огня',
            pattern=['flash'],
            meaning='Я изменяю свой курс вправо',
            rule_number=34
        ),
        'port': Signal(
            signal_type='light',
            description='2 вспышки белого огня',
            pattern=['flash', 'flash'],
            meaning='Я изменяю свой курс влево',
            rule_number=34
        ),
        'astern': Signal(
            signal_type='light',
            description='3 вспышки белого огня',
            pattern=['flash', 'flash', 'flash'],
            meaning='Мои движители работают на задний ход',
            rule_number=34
        ),
        'doubt': Signal(
            signal_type='light',
            description='5 или более вспышек',
            pattern=['flash'] * 5,
            meaning='Сигнал предупреждения / сомнения',
            rule_number=34
        )
    }
    
    # Сигнальные огни судов (для идентификации типа)
    VESSEL_LIGHTS: Dict[str, Dict] = {
        'power_driven': {
            'description': 'Топовый огонь (белый, 225°), бортовые огни (красный/зеленый, 112.5° каждый), кормовой огонь (белый, 135°)',
            'lights': ['masthead', 'sidelights', 'stern']
        },
        'sailing': {
            'description': 'Бортовые огни (красный/зеленый), кормовой огонь (белый). Может иметь дополнительный топовый огонь',
            'lights': ['sidelights', 'stern', 'optional_masthead']
        },
        'fishing': {
            'description': 'Красный над белым круговые огни. Дополнительный зеленый над белым при тралении',
            'lights': ['red_over_white_all_round', 'optional_green_over_white']
        },
        'nuc': {
            'description': 'Два красных круговых огня один над другим',
            'lights': ['red_over_red_all_round']
        },
        'ram': {
            'description': 'Красный-белый-красный круговые огни',
            'lights': ['red_white_red_all_round']
        },
        'cbd': {
            'description': 'Три зеленых круговых огня. Дополнительно топовые и бортовые огни',
            'lights': ['three_green_all_round', 'masthead', 'sidelights', 'stern']
        },
        'pilot': {
            'description': 'Белый над красным круговые огни',
            'lights': ['white_over_red_all_round']
        },
        'anchored': {
            'description': 'Белый круговой огонь на носу. Второй белый круговой огонь на корме (для судов >50м)',
            'lights': ['white_all_round_forward', 'optional_white_all_round_aft']
        }
    }
    
    @classmethod
    def get_maneuver_light(cls, maneuver: str) -> Optional[Signal]:
        """
        Получение светового сигнала для маневра
        
        Args:
            maneuver: Тип маневра ('starboard', 'port', 'astern', 'doubt')
            
        Returns:
            Signal или None если не найдено
        """
        return cls.MANEUVER_LIGHTS.get(maneuver)
    
    @classmethod
    def get_vessel_lights(cls, vessel_type: str) -> Optional[Dict]:
        """
        Получение информации о ходовых огнях для типа судна
        
        Args:
            vessel_type: Тип судна
            
        Returns:
            Dict с описанием огней или None
        """
        return cls.VESSEL_LIGHTS.get(vessel_type)
    
    @classmethod
    def get_all_maneuver_lights(cls) -> Dict[str, Signal]:
        """Возвращает все маневросигналы"""
        return cls.MANEUVER_LIGHTS.copy()


class SignalGenerator:
    """
    Генератор сигналов для визуализации
    
    Создает отображаемые представления сигналов для frontend
    """
    
    @staticmethod
    def generate_signal_display(signal: Signal) -> Dict:
        """
        Генерация отображаемого представления сигнала
        
        Args:
            signal: Объект Signal
            
        Returns:
            Dict с данными для отображения
        """
        if signal.signal_type == 'sound':
            return {
                'type': 'sound',
                'icon': '🔊',
                'description': signal.description,
                'pattern': signal.pattern,
                'meaning': signal.meaning,
                'rule': f"Правило {signal.rule_number}",
                'visual_pattern': SignalGenerator._sound_to_visual(signal.pattern)
            }
        elif signal.signal_type == 'light':
            return {
                'type': 'light',
                'icon': '💡',
                'description': signal.description,
                'pattern': signal.pattern,
                'meaning': signal.meaning,
                'rule': f"Правило {signal.rule_number}",
                'visual_pattern': SignalGenerator._light_to_visual(signal.pattern)
            }
        
        return {}
    
    @staticmethod
    def _sound_to_visual(pattern: List[str]) -> str:
        """Преобразование звукового паттерна в визуальное представление"""
        visual = []
        for p in pattern:
            if p == 'short':
                visual.append('●')  # Короткий
            elif p == 'prolonged':
                visual.append('━━━')  # Продолжительный
            elif p.startswith('bell'):
                visual.append('🔔')  # Колокол
        return ' '.join(visual)
    
    @staticmethod
    def _light_to_visual(pattern: List[str]) -> str:
        """Преобразование светового паттерна в визуальное представление"""
        visual = []
        for p in pattern:
            if p == 'flash':
                visual.append('⚡')  # Вспышка
        return ' '.join(visual)
    
    @staticmethod
    def get_vessel_lights_display(vessel_type: str) -> Dict:
        """
        Получение информации о ходовых огнях для отображения
        
        Args:
            vessel_type: Тип судна
            
        Returns:
            Dict с информацией для отображения
        """
        lights_info = LightSignals.get_vessel_lights(vessel_type)
        
        if not lights_info:
            return {
                'error': f'Неизвестный тип судна: {vessel_type}'
            }
        
        return {
            'vessel_type': vessel_type,
            'description': lights_info['description'],
            'lights': lights_info['lights'],
            'diagram_available': True
        }
    
    @staticmethod
    def generate_emergency_signal() -> Dict:
        """Генерация сигнала тревоги"""
        return {
            'type': 'emergency',
            'icon': '🚨',
            'sound': '🔊 5+ коротких гудков + 3 коротких (задний ход)',
            'light': '💡 5+ вспышек (тревога)',
            'meaning': 'ЭКСТРЕННОЕ ДЕЙСТВИЕ - Избежание столкновения!',
            'rule': 'Правило 2 (отступление от правил)'
        }
