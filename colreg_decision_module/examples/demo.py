"""
Example usage and demonstration of the COLREG-72 Decision Module.

This script demonstrates how to use the module for collision avoidance
decision making with various encounter scenarios.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from colreg_decision_module.models.vessel_model import (
    OwnVessel, TargetVessel, VesselType, VesselStatus
)
from colreg_decision_module.core.tcpa_calculator import TCPACalculator
from colreg_decision_module.core.encounter_classifier import EncounterClassifier
from colreg_decision_module.core.decision_engine import COLREGDecisionEngine
from colreg_decision_module.core.signal_generator import SignalGenerator


def print_separator(title: str):
    """Print a formatted section separator."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def scenario_head_on():
    """Demonstrate head-on situation (Rule 14)."""
    print_separator("SCENARIO 1: Head-On Situation (Rule 14)")
    
    # Create own vessel
    own_vessel = OwnVessel(
        vessel_id="OWN",
        lat=51.5000, lon=-0.1000,
        course=0, speed=12,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    # Create target vessel on reciprocal course
    target = TargetVessel(
        vessel_id="TGT_HEADON",
        lat=51.5500, lon=-0.1000,
        course=180, speed=12,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    # Calculate TCPA
    tcpa_calc = TCPACalculator()
    result = tcpa_calc.calculate_single(own_vessel, target)
    
    print(f"\n📍 Own Vessel: Course {own_vessel.course}°, Speed {own_vessel.speed} kn")
    print(f"📍 Target: Course {target.course}°, Speed {target.speed} kn")
    print(f"\n📊 TCPA Analysis:")
    print(f"   Range: {result.range_nm:.2f} NM")
    print(f"   Bearing: {result.bearing_true:.1f}°")
    print(f"   Relative Bearing: {result.relative_bearing:.1f}°")
    print(f"   TCPA: {result.tcpa_minutes:.1f} min")
    print(f"   DCPA: {result.dcpa_nm:.3f} NM")
    print(f"   Risk Level: {result.collision_risk.upper()}")
    
    # Make decision
    engine = COLREGDecisionEngine()
    decisions = engine.make_decisions(own_vessel, [target])
    
    if decisions:
        decision = decisions[0]
        print(f"\n🎯 Decision:")
        print(f"   Maneuver: {decision.recommended_maneuver.value}")
        print(f"   Angle: {decision.maneuver_angle}°" if decision.maneuver_angle else "")
        print(f"   Signals: {', '.join(decision.signals_required)}")
        print(f"   Reasoning: {decision.reasoning}")
    
    return own_vessel, [target], decisions


def scenario_crossing():
    """Demonstrate crossing situation (Rule 15)."""
    print_separator("SCENARIO 2: Crossing Situation (Rule 15)")
    
    own_vessel = OwnVessel(
        vessel_id="OWN",
        lat=51.5000, lon=-0.1000,
        course=90, speed=10,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    target = TargetVessel(
        vessel_id="TGT_CROSSING",
        lat=51.5200, lon=-0.0800,
        course=0, speed=10,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    tcpa_calc = TCPACalculator()
    result = tcpa_calc.calculate_single(own_vessel, target)
    
    print(f"\n📍 Own Vessel: Course {own_vessel.course}°, Speed {own_vessel.speed} kn")
    print(f"📍 Target: Course {target.course}°, Speed {target.speed} kn")
    print(f"\n📊 TCPA Analysis:")
    print(f"   Range: {result.range_nm:.2f} NM")
    print(f"   Relative Bearing: {result.relative_bearing:.1f}°")
    print(f"   TCPA: {result.tcpa_minutes:.1f} min")
    print(f"   DCPA: {result.dcpa_nm:.3f} NM")
    print(f"   Risk Level: {result.collision_risk.upper()}")
    
    engine = COLREGDecisionEngine()
    decisions = engine.make_decisions(own_vessel, [target])
    
    if decisions:
        decision = decisions[0]
        print(f"\n🎯 Decision:")
        print(f"   Maneuver: {decision.recommended_maneuver.value}")
        print(f"   Angle: {decision.maneuver_angle}°" if decision.maneuver_angle else "")
        print(f"   Signals: {', '.join(decision.signals_required)}")
        print(f"   Reasoning: {decision.reasoning}")
    
    return own_vessel, [target], decisions


def scenario_fishing():
    """Demonstrate encounter with fishing vessel (Rule 18)."""
    print_separator("SCENARIO 3: Fishing Vessel Encounter (Rule 18)")
    
    own_vessel = OwnVessel(
        lat=51.5000, lon=-0.1000,
        course=0, speed=12,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    target = TargetVessel(
        vessel_id="TGT_FISHING",
        lat=51.5400, lon=-0.1000,
        course=90, speed=4,
        vessel_type=VesselType.FISHING
    )
    
    tcpa_calc = TCPACalculator()
    result = tcpa_calc.calculate_single(own_vessel, target)
    
    print(f"\n📍 Own Vessel: Power-driven, Course {own_vessel.course}°, Speed {own_vessel.speed} kn")
    print(f"📍 Target: FISHING vessel, Course {target.course}°, Speed {target.speed} kn")
    print(f"\n📊 Priority Analysis:")
    print(f"   According to Rule 18, fishing vessels have priority over power-driven vessels")
    print(f"\n📊 TCPA Analysis:")
    print(f"   Range: {result.range_nm:.2f} NM")
    print(f"   TCPA: {result.tcpa_minutes:.1f} min")
    print(f"   DCPA: {result.dcpa_nm:.3f} NM")
    print(f"   Risk Level: {result.collision_risk.upper()}")
    
    engine = COLREGDecisionEngine()
    decisions = engine.make_decisions(own_vessel, [target])
    
    if decisions:
        decision = decisions[0]
        print(f"\n🎯 Decision:")
        print(f"   Maneuver: {decision.recommended_maneuver.value}")
        print(f"   Angle: {decision.maneuver_angle}°" if decision.maneuver_angle else "")
        print(f"   Signals: {', '.join(decision.signals_required)}")
        print(f"   Reasoning: {decision.reasoning}")
    
    return own_vessel, [target], decisions


def scenario_multiple():
    """Demonstrate multiple target scenario."""
    print_separator("SCENARIO 4: Multiple Targets")
    
    own_vessel = OwnVessel(
        lat=51.5000, lon=-0.1000,
        course=45, speed=12,
        vessel_type=VesselType.POWER_DRIVEN
    )
    
    targets = [
        TargetVessel(
            vessel_id="TGT1",
            lat=51.5300, lon=-0.0800,
            course=225, speed=10,
            vessel_type=VesselType.POWER_DRIVEN
        ),
        TargetVessel(
            vessel_id="TGT2",
            lat=51.4800, lon=-0.1200,
            course=90, speed=6,
            vessel_type=VesselType.SAILING
        ),
        TargetVessel(
            vessel_id="TGT3",
            lat=51.5100, lon=-0.0500,
            course=180, speed=3,
            vessel_type=VesselType.FISHING
        )
    ]
    
    tcpa_calc = TCPACalculator()
    results = tcpa_calc.calculate_all(own_vessel, targets)
    
    print(f"\n📍 Own Vessel: Course {own_vessel.course}°, Speed {own_vessel.speed} kn")
    print(f"\n📊 All Targets:")
    for result in results:
        print(f"   {result.target_id}: Range={result.range_nm:.2f}NM, "
              f"TCPA={result.tcpa_minutes:.1f}min, DCPA={result.dcpa_nm:.3f}NM, "
              f"Risk={result.collision_risk.upper()}")
    
    engine = COLREGDecisionEngine()
    decisions = engine.make_decisions(own_vessel, targets)
    
    print(f"\n🎯 Decisions (sorted by urgency):")
    for decision in decisions:
        print(f"\n   {decision.target_id}:")
        print(f"      Encounter: {decision.encounter_type.value}")
        print(f"      Responsibility: {decision.responsibility.value}")
        print(f"      Maneuver: {decision.recommended_maneuver.value}")
        print(f"      Urgency: {decision.urgency}")
        print(f"      Signals: {', '.join(decision.signals_required) if decision.signals_required else 'None'}")
    
    return own_vessel, targets, decisions


def demonstrate_signals():
    """Demonstrate signal generation."""
    print_separator("COLREG-72 Signals Reference")
    
    generator = SignalGenerator(vessel_length=25)
    
    print("\n🔦 Navigation Lights for Power-Driven Vessel (25m):")
    lights = generator.get_lights_for_vessel(VesselType.POWER_DRIVEN, VesselStatus.UNDERWAY)
    for light in lights:
        info = light.to_dict()
        print(f"   - {info['color']} light at {info['position']}, arc={info['arc_degrees']}°, range={info['range_nm']}NM")
    
    print("\n🔊 Maneuver Sound Signals (Rule 34):")
    signals = ['starboard', 'port', 'astern', 'doubt']
    for sig_type in signals:
        signal = generator.get_maneuver_sound_signal(sig_type)
        info = signal.to_dict()
        blasts = "•" * info['count']
        print(f"   - {sig_type}: {blasts} ({info['meaning']})")
    
    print("\n🌫️ Fog Signals (Rule 35):")
    fog_signal = generator.get_fog_signal(VesselType.POWER_DRIVEN, underway=True, making_way=True)
    info = fog_signal.to_dict()
    print(f"   - Making way: {info['count']} prolonged blast(s) every {info['interval_seconds']}s")
    
    fog_signal_stopped = generator.get_fog_signal(VesselType.POWER_DRIVEN, underway=True, making_way=False)
    info = fog_signal_stopped.to_dict()
    print(f"   - Stopped: {info['count']} prolonged blast(s) every {info['interval_seconds']}s")
    
    print("\n⚫ Day Shapes:")
    shapes = generator.get_day_shapes_for_vessel(VesselType.NUC, VesselStatus.UNDERWAY)
    for shape in shapes:
        info = shape.to_dict()
        print(f"   - {info['shape']} x{info['count']} ({info['meaning']})")


def main():
    """Run all demonstration scenarios."""
    print("\n" + "🚢" * 30)
    print(" COLREG-72 DECISION MODULE DEMONSTRATION")
    print(" International Regulations for Preventing Collisions at Sea")
    print("🚢" * 30)
    
    # Run scenarios
    scenario_head_on()
    scenario_crossing()
    scenario_fishing()
    scenario_multiple()
    
    # Signal reference
    demonstrate_signals()
    
    print_separator("DEMONSTRATION COMPLETE")
    print("\n✅ The COLREG-72 Decision Module is ready for use!")
    print("\nTo run the web interface:")
    print("   cd /workspace/colreg-decision-module")
    print("   python -m frontend.app")
    print("\nThen open http://localhost:5000 in your browser.\n")


if __name__ == "__main__":
    main()
