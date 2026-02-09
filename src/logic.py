"""
AI Logic Controller Module
Implements Pressure-Based Adaptive Algorithm with 4-Direction Phases.
Each direction (North, East, South, West) gets its own dedicated green phase.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import time

from config import traffic_light_config, algorithm_config, APPROACH_LANES
from traci_interface import (
    DetectorInterface, TrafficLightController, VehicleInterface,
    ApproachData, EmergencyVehicle
)


# ============================================== #
# ENUMS AND DATA STRUCTURES
# ============================================== #

class ControllerMode(Enum):
    """Traffic controller operation modes"""
    FIXED_TIME = "fixed"
    ADAPTIVE = "adaptive"


class PhaseType(Enum):
    """Traffic light phase types - 4 direction rotation"""
    NORTH_GREEN = "north_green"
    NORTH_YELLOW = "north_yellow"
    EAST_GREEN = "east_green"
    EAST_YELLOW = "east_yellow"
    SOUTH_GREEN = "south_green"
    SOUTH_YELLOW = "south_yellow"
    WEST_GREEN = "west_green"
    WEST_YELLOW = "west_yellow"


# Direction to phase mapping
DIRECTION_TO_GREEN_PHASE = {
    'north': (0, PhaseType.NORTH_GREEN),
    'east': (2, PhaseType.EAST_GREEN),
    'south': (4, PhaseType.SOUTH_GREEN),
    'west': (6, PhaseType.WEST_GREEN),
}

DIRECTION_TO_YELLOW_PHASE = {
    'north': (1, PhaseType.NORTH_YELLOW),
    'east': (3, PhaseType.EAST_YELLOW),
    'south': (5, PhaseType.SOUTH_YELLOW),
    'west': (7, PhaseType.WEST_YELLOW),
}

# Phase rotation order
PHASE_ORDER = ['north', 'east', 'south', 'west']


@dataclass
class PhaseDecision:
    """Represents a traffic light phase decision"""
    phase_index: int
    phase_type: PhaseType
    duration: float
    reason: str
    priority_vehicle: Optional[str] = None


@dataclass
class ControllerState:
    """Tracks the internal state of the controller"""
    current_phase: int = 0
    current_direction: str = 'north'
    phase_start_time: float = 0.0
    last_switch_time: float = 0.0
    emergency_active: bool = False
    emergency_cooldown_end: float = 0.0
    direction_green_times: Dict[str, float] = field(default_factory=lambda: {
        'north': 0.0, 'east': 0.0, 'south': 0.0, 'west': 0.0
    })


# ============================================== #
# BASE CONTROLLER CLASS
# ============================================== #

class BaseController:
    """Base class for traffic light controllers"""
    
    def __init__(self, junction_id: str = None):
        self.tl_controller = TrafficLightController(junction_id)
        self.config = traffic_light_config
        self.state = ControllerState()
        self.mode = ControllerMode.FIXED_TIME
        
    def update(self, simulation_time: float) -> Optional[PhaseDecision]:
        raise NotImplementedError("Subclass must implement update()")
    
    def apply_decision(self, decision: PhaseDecision):
        self.tl_controller.set_phase(decision.phase_index)
        self.tl_controller.set_phase_duration(decision.duration)
        self.state.current_phase = decision.phase_index
        self.state.phase_start_time = self._get_simulation_time()
        
    def _get_simulation_time(self) -> float:
        try:
            import traci
            return traci.simulation.getTime()
        except:
            return 0.0
    
    def get_statistics(self) -> Dict:
        return {
            'mode': self.mode.value,
            'current_phase': self.state.current_phase,
            'current_direction': self.state.current_direction,
            'direction_green_times': self.state.direction_green_times,
            'emergency_active': self.state.emergency_active,
        }


# ============================================== #
# FIXED-TIME CONTROLLER - 4 Direction Rotation
# ============================================== #

class FixedTimeController(BaseController):
    """Fixed-time controller with 4-direction rotation."""
    
    def __init__(self, junction_id: str = None):
        super().__init__(junction_id)
        self.mode = ControllerMode.FIXED_TIME
        
        # 8 phases: North Green, North Yellow, East Green, East Yellow, etc.
        self.phase_sequence = [
            (0, PhaseType.NORTH_GREEN, 'north', self.config.fixed_green_duration),
            (1, PhaseType.NORTH_YELLOW, 'north', self.config.yellow_duration),
            (2, PhaseType.EAST_GREEN, 'east', self.config.fixed_green_duration),
            (3, PhaseType.EAST_YELLOW, 'east', self.config.yellow_duration),
            (4, PhaseType.SOUTH_GREEN, 'south', self.config.fixed_green_duration),
            (5, PhaseType.SOUTH_YELLOW, 'south', self.config.yellow_duration),
            (6, PhaseType.WEST_GREEN, 'west', self.config.fixed_green_duration),
            (7, PhaseType.WEST_YELLOW, 'west', self.config.yellow_duration),
        ]
        self.current_phase_index = 0
        self.phase_end_time = 0.0
        
    def update(self, simulation_time: float) -> Optional[PhaseDecision]:
        # Initialize on first call
        if self.phase_end_time == 0.0:
            self.phase_end_time = simulation_time + self.phase_sequence[0][3]
            self.state.current_direction = 'north'
            return PhaseDecision(
                phase_index=0,
                phase_type=PhaseType.NORTH_GREEN,
                duration=self.config.fixed_green_duration,
                reason="Initial phase: North green"
            )
        
        if simulation_time >= self.phase_end_time:
            self.current_phase_index = (self.current_phase_index + 1) % len(self.phase_sequence)
            phase_idx, phase_type, direction, duration = self.phase_sequence[self.current_phase_index]
            self.phase_end_time = simulation_time + duration
            self.state.current_direction = direction
            
            # Track green times
            if 'GREEN' in phase_type.name:
                self.state.direction_green_times[direction] += duration
            
            return PhaseDecision(
                phase_index=phase_idx,
                phase_type=phase_type,
                duration=duration,
                reason=f"Fixed-time: {direction.upper()} {phase_type.name.split('_')[1].lower()}"
            )
        
        return None


# ============================================== #
# PRESSURE-BASED ADAPTIVE CONTROLLER - 4 Directions
# ============================================== #

class PressureBasedController(BaseController):
    """
    Adaptive controller with 4-direction rotation.
    Includes starvation prevention - ensures all directions get a turn.
    """
    
    # Maximum time any direction can wait without getting green (seconds)
    MAX_STARVATION_TIME = 120.0  # 2 minutes max wait
    
    def __init__(self, junction_id: str = None):
        super().__init__(junction_id)
        self.mode = ControllerMode.ADAPTIVE
        self.algo_config = algorithm_config
        
        self.current_direction = 'north'
        self.is_green_phase = True  # True = green, False = yellow
        self.phase_end_time = 0.0
        self.preemption_direction = None
        
        # Fairness tracking - track when each direction last had green
        self.last_green_time = {
            'north': 0.0, 'east': 0.0, 'south': 0.0, 'west': 0.0
        }
        # Track which directions have had a turn in current cycle
        self.served_this_cycle = set()
        
    def update(self, simulation_time: float) -> Optional[PhaseDecision]:
        # Check for emergency vehicles first
        emergency_decision = self._check_emergency_preemption(simulation_time)
        if emergency_decision:
            return emergency_decision
        
        # Handle emergency cooldown
        if self.state.emergency_active and simulation_time < self.state.emergency_cooldown_end:
            return None
        elif self.state.emergency_active:
            self.state.emergency_active = False
        
        # Initialize on first call
        if self.phase_end_time == 0.0:
            initial_duration = self._calculate_green_duration('north')
            self.phase_end_time = simulation_time + initial_duration
            self.current_direction = 'north'
            self.is_green_phase = True
            self.last_green_time['north'] = simulation_time
            self.served_this_cycle.add('north')
            return self._make_green_decision('north', initial_duration, "Initial adaptive phase")
        
        time_in_phase = simulation_time - self.state.phase_start_time
        
        # Yellow phase - wait for it to end
        if not self.is_green_phase:
            if simulation_time >= self.phase_end_time:
                return self._transition_to_next_green(simulation_time)
            return None
        
        # Green phase - adaptive logic
        return self._evaluate_green_phase(simulation_time, time_in_phase)
    
    def _calculate_pressure(self, direction: str) -> float:
        """Calculate traffic pressure for a single direction."""
        approach_data = DetectorInterface.get_approach_data(direction)
        
        vehicle_pressure = approach_data.total_vehicles * self.algo_config.vehicle_count_weight
        waiting_pressure = approach_data.total_waiting_time * self.algo_config.waiting_time_weight
        queue_pressure = approach_data.queue_length * self.algo_config.queue_length_weight
        
        return vehicle_pressure + waiting_pressure + queue_pressure
    
    def _calculate_green_duration(self, direction: str) -> float:
        """Calculate green duration based on pressure."""
        pressure = self._calculate_pressure(direction)
        green_time = self.config.min_green_duration + (pressure * 0.5)
        return max(self.config.min_green_duration, 
                   min(self.config.max_green_duration, green_time))
    
    def _get_next_direction(self, simulation_time: float) -> Tuple[str, float, str]:
        """
        Get next direction with fairness consideration.
        Returns: (direction, pressure, reason)
        """
        # First, check if any direction is starving (hasn't had green for too long)
        starved_directions = []
        for direction in PHASE_ORDER:
            if direction == self.current_direction:
                continue
            wait_time = simulation_time - self.last_green_time[direction]
            if wait_time > self.MAX_STARVATION_TIME:
                starved_directions.append((direction, wait_time))
        
        # If any direction is starving, serve the most starved one first
        if starved_directions:
            starved_directions.sort(key=lambda x: x[1], reverse=True)  # Most starved first
            starved_dir = starved_directions[0][0]
            pressure = self._calculate_pressure(starved_dir)
            return starved_dir, pressure, f"FAIRNESS: {starved_dir.upper()} waited {starved_directions[0][1]:.0f}s"
        
        # Check if we need to serve unserved directions in this cycle
        unserved = [d for d in PHASE_ORDER if d not in self.served_this_cycle and d != self.current_direction]
        if unserved:
            # Among unserved, pick the one with highest pressure
            best_unserved = max(unserved, key=lambda d: self._calculate_pressure(d))
            pressure = self._calculate_pressure(best_unserved)
            return best_unserved, pressure, f"CYCLE: Serving {best_unserved.upper()} (unserved this cycle)"
        
        # All directions served this cycle - reset and pick by pressure
        self.served_this_cycle.clear()
        
        # Pick direction with highest pressure (excluding current)
        max_pressure = -1
        max_direction = 'north'
        for direction in PHASE_ORDER:
            if direction == self.current_direction:
                continue
            pressure = self._calculate_pressure(direction)
            if pressure > max_pressure:
                max_pressure = pressure
                max_direction = direction
        
        return max_direction, max_pressure, f"PRESSURE: {max_direction.upper()} has highest demand"
    
    def _evaluate_green_phase(self, simulation_time: float, time_in_phase: float) -> Optional[PhaseDecision]:
        """Evaluate whether to extend or end current green phase."""
        
        # HARD LIMIT: Never exceed max green duration (60 seconds)
        if time_in_phase >= self.config.max_green_duration:
            self.state.direction_green_times[self.current_direction] += time_in_phase
            print(f"[LIMIT] {self.current_direction.upper()} reached max {self.config.max_green_duration}s - forcing switch")
            return self._transition_to_yellow(simulation_time)
        
        # Check if any other direction is starving
        for direction in PHASE_ORDER:
            if direction == self.current_direction:
                continue
            wait_time = simulation_time - self.last_green_time[direction]
            if wait_time > self.MAX_STARVATION_TIME:
                # Another direction has been waiting too long - switch!
                self.state.direction_green_times[self.current_direction] += time_in_phase
                print(f"[FAIRNESS] {direction.upper()} waiting {wait_time:.0f}s - forcing switch")
                return self._transition_to_yellow(simulation_time)
        
        # Minimum green time check
        if time_in_phase < self.algo_config.min_green_before_switch:
            return None
        
        current_pressure = self._calculate_pressure(self.current_direction)
        
        # Get next best direction info
        next_dir, next_pressure, _ = self._get_next_direction(simulation_time)
        
        # Decision: switch if another direction has significantly higher pressure
        pressure_ratio = next_pressure / max(current_pressure, 0.1)
        
        should_switch = (
            pressure_ratio > self.algo_config.pressure_ratio_threshold or
            (current_pressure < 1.0 and next_pressure > 5.0)
        )
        
        if should_switch:
            self.state.direction_green_times[self.current_direction] += time_in_phase
            return self._transition_to_yellow(simulation_time)
        
        # Extend green if pressure is high (but respect max limit checked above)
        if simulation_time >= self.phase_end_time and current_pressure > next_pressure:
            extension = min(self.config.extension_time, 
                          self.config.max_green_duration - time_in_phase)
            if extension > 0:
                self.phase_end_time = simulation_time + extension
        
        return None
    
    def _make_green_decision(self, direction: str, duration: float, reason: str) -> PhaseDecision:
        """Create a green phase decision."""
        phase_idx, phase_type = DIRECTION_TO_GREEN_PHASE[direction]
        self.current_direction = direction
        self.state.current_direction = direction
        self.is_green_phase = True
        return PhaseDecision(phase_idx, phase_type, duration, reason)
    
    def _transition_to_yellow(self, simulation_time: float) -> PhaseDecision:
        """Transition from green to yellow."""
        phase_idx, phase_type = DIRECTION_TO_YELLOW_PHASE[self.current_direction]
        self.phase_end_time = simulation_time + self.config.yellow_duration
        self.is_green_phase = False
        
        return PhaseDecision(
            phase_index=phase_idx,
            phase_type=phase_type,
            duration=self.config.yellow_duration,
            reason=f"{self.current_direction.upper()} yellow"
        )
    
    def _transition_to_next_green(self, simulation_time: float) -> PhaseDecision:
        """Select next direction with fairness and transition to green."""
        # Get next direction considering fairness
        next_direction, pressure, reason = self._get_next_direction(simulation_time)
        
        # Calculate adaptive green duration
        green_duration = self._calculate_green_duration(next_direction)
        self.phase_end_time = simulation_time + green_duration
        
        # Update fairness tracking
        self.last_green_time[next_direction] = simulation_time
        self.served_this_cycle.add(next_direction)
        
        print(f"[PHASE] {next_direction.upper()} green ({green_duration:.1f}s) - {reason}")
        
        return self._make_green_decision(
            next_direction, 
            green_duration,
            f"Adaptive: {next_direction.upper()} - {reason}"
        )
    
    def _check_emergency_preemption(self, simulation_time: float) -> Optional[PhaseDecision]:
        """Check for emergency vehicles and preempt if necessary."""
        if self.state.emergency_active:
            return None
        
        emergency_vehicles = VehicleInterface.detect_emergency_vehicles()
        
        for ev in emergency_vehicles:
            if ev.distance_to_junction <= self.algo_config.emergency_detection_distance:
                direction = self._get_direction_from_lane(ev.lane_id)
                
                if direction == 'unknown':
                    continue
                
                # Set emergency state
                self.state.emergency_active = True
                self.state.emergency_cooldown_end = (
                    simulation_time + 
                    self.algo_config.emergency_preemption_time + 
                    self.algo_config.emergency_cooldown
                )
                
                phase_idx, phase_type = DIRECTION_TO_GREEN_PHASE[direction]
                self.current_direction = direction
                self.is_green_phase = True
                self.phase_end_time = simulation_time + self.algo_config.emergency_preemption_time
                
                print(f"[EMERGENCY] Preempting for {ev.vehicle_id} on {direction} approach")
                
                return PhaseDecision(
                    phase_index=phase_idx,
                    phase_type=phase_type,
                    duration=self.algo_config.emergency_preemption_time,
                    reason=f"Emergency preemption for {ev.vehicle_id}",
                    priority_vehicle=ev.vehicle_id
                )
        
        return None
    
    def _get_direction_from_lane(self, lane_id: str) -> str:
        """Determine approach direction from lane ID."""
        for direction, lanes in APPROACH_LANES.items():
            if lane_id in lanes or any(lane_id.startswith(l.rsplit('_', 1)[0]) for l in lanes):
                return direction
        return 'unknown'


# ============================================== #
# CONTROLLER FACTORY
# ============================================== #

def create_controller(mode: str, junction_id: str = None) -> BaseController:
    """Factory function to create appropriate controller."""
    if mode.lower() == 'fixed':
        return FixedTimeController(junction_id)
    elif mode.lower() == 'adaptive':
        return PressureBasedController(junction_id)
    else:
        raise ValueError(f"Unknown controller mode: {mode}")


# ============================================== #
# EFFICIENCY CALCULATOR
# ============================================== #

class EfficiencyCalculator:
    """Calculates efficiency scores comparing adaptive vs fixed-time control."""
    
    def __init__(self):
        self.fixed_metrics = {'waiting_time': [], 'queue_length': [], 'throughput': 0}
        self.adaptive_metrics = {'waiting_time': [], 'queue_length': [], 'throughput': 0}
    
    def record_metrics(self, mode: str, waiting_time: float, queue_length: int, throughput: int = 0):
        metrics = self.fixed_metrics if mode == 'fixed' else self.adaptive_metrics
        metrics['waiting_time'].append(waiting_time)
        metrics['queue_length'].append(queue_length)
        metrics['throughput'] = max(metrics['throughput'], throughput)
    
    def calculate_efficiency_score(self) -> Dict:
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0
        
        fixed_avg_wait = avg(self.fixed_metrics['waiting_time'])
        adaptive_avg_wait = avg(self.adaptive_metrics['waiting_time'])
        
        fixed_avg_queue = avg(self.fixed_metrics['queue_length'])
        adaptive_avg_queue = avg(self.adaptive_metrics['queue_length'])
        
        wait_improvement = ((fixed_avg_wait - adaptive_avg_wait) / max(fixed_avg_wait, 0.1)) * 100
        queue_improvement = ((fixed_avg_queue - adaptive_avg_queue) / max(fixed_avg_queue, 0.1)) * 100
        
        efficiency_score = (wait_improvement * 0.6) + (queue_improvement * 0.4)
        
        return {
            'fixed_avg_waiting_time': fixed_avg_wait,
            'adaptive_avg_waiting_time': adaptive_avg_wait,
            'waiting_time_improvement': wait_improvement,
            'fixed_avg_queue_length': fixed_avg_queue,
            'adaptive_avg_queue_length': adaptive_avg_queue,
            'queue_improvement': queue_improvement,
            'overall_efficiency_score': efficiency_score,
            'adaptive_is_better': efficiency_score > 0,
        }
