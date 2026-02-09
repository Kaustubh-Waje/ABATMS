"""
TraCI Interface Module for SUMO Communication
Handles connection management, data retrieval, and traffic light control.
"""

import os
import sys
import time
import socket
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Import SUMO libraries
try:
    import traci
    import traci.constants as tc
except ImportError:
    # Try to add SUMO_HOME to path
    sumo_home = os.environ.get('SUMO_HOME', r'C:\Program Files (x86)\Eclipse\Sumo')
    if sumo_home:
        sys.path.append(os.path.join(sumo_home, 'tools'))
    import traci
    import traci.constants as tc

from config import (
    SUMO_CFG, simulation_config, traffic_light_config,
    APPROACH_LANES, LANE_DETECTORS, E3_DETECTORS, QUEUE_DETECTORS,
    EMERGENCY_VEHICLE_TYPES, get_sumo_command
)


# ============================================== #
# DATA CLASSES FOR STRUCTURED DATA
# ============================================== #

@dataclass
class LaneData:
    """Data structure for lane-level traffic information"""
    lane_id: str
    vehicle_count: int
    occupancy: float
    mean_speed: float
    waiting_time: float
    queue_length: int


@dataclass
class ApproachData:
    """Aggregated data for an entire approach direction"""
    direction: str
    total_vehicles: int
    total_waiting_time: float
    mean_speed: float
    queue_length: int
    pressure: float  # Calculated pressure value


@dataclass
class EmergencyVehicle:
    """Information about a detected emergency vehicle"""
    vehicle_id: str
    vehicle_type: str
    edge_id: str
    lane_id: str
    position: float
    speed: float
    distance_to_junction: float


# ============================================== #
# SUMO CONNECTION MANAGER
# ============================================== #

class SUMOConnection:
    """
    Manages TraCI connection to SUMO with retry logic and error handling.
    """
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the SUMO connection manager.
        
        Args:
            config: SimulationConfig instance (uses default if None)
        """
        self.config = config or simulation_config
        self.connected = False
        self.step_count = 0
        self.start_time = None
        
    def connect(self, gui: bool = True, port: Optional[int] = None) -> bool:
        """
        Establish connection to SUMO with retry logic.
        
        Args:
            gui: Use SUMO-GUI if True
            port: TraCI port (uses config default if None)
            
        Returns:
            True if connection successful, False otherwise
        """
        port = port or self.config.port
        sumo_cmd = get_sumo_command(gui)
        
        for attempt in range(self.config.max_retries):
            try:
                print(f"[INFO] Attempting SUMO connection (attempt {attempt + 1}/{self.config.max_retries})...")
                
                # Check if port is available
                if self._is_port_in_use(port):
                    print(f"[WARN] Port {port} in use, trying next port...")
                    port += 1
                    continue
                
                # Start SUMO with TraCI
                traci.start(sumo_cmd, port=port)
                
                self.connected = True
                self.start_time = time.time()
                print(f"[INFO] Successfully connected to SUMO on port {port}")
                return True
                
            except traci.exceptions.TraCIException as e:
                print(f"[ERROR] TraCI connection failed: {e}")
                time.sleep(self.config.retry_delay)
                
            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")
                time.sleep(self.config.retry_delay)
        
        print("[ERROR] Failed to connect to SUMO after all retries")
        return False
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def disconnect(self):
        """Close the TraCI connection properly."""
        if self.connected:
            try:
                traci.close()
                print("[INFO] SUMO connection closed")
            except Exception as e:
                print(f"[WARN] Error closing connection: {e}")
            finally:
                self.connected = False
        
        # Force close any remaining connections
        try:
            traci.close()
        except:
            pass
        
        # Small delay to ensure cleanup
        import time
        time.sleep(1)
    
    def step(self) -> bool:
        """
        Advance simulation by one step.
        
        Returns:
            True if step successful, False if simulation ended
        """
        if not self.connected:
            return False
            
        try:
            traci.simulationStep()
            self.step_count += 1
            return True
        except traci.exceptions.FatalTraCIError:
            print("[INFO] Simulation ended")
            self.connected = False
            return False
    
    def get_simulation_time(self) -> float:
        """Get current simulation time in seconds."""
        if self.connected:
            return traci.simulation.getTime()
        return 0.0
    
    def get_remaining_vehicles(self) -> int:
        """Get number of vehicles still in simulation."""
        if self.connected:
            return traci.simulation.getMinExpectedNumber()
        return 0


# ============================================== #
# DETECTOR DATA RETRIEVAL
# ============================================== #

class DetectorInterface:
    """Interface for retrieving data from simulation detectors."""
    
    @staticmethod
    def get_lane_data(lane_id: str) -> LaneData:
        """
        Get traffic data for a specific lane.
        
        Args:
            lane_id: The lane identifier
            
        Returns:
            LaneData object with current lane metrics
        """
        try:
            vehicle_ids = traci.lane.getLastStepVehicleIDs(lane_id)
            vehicle_count = len(vehicle_ids)
            occupancy = traci.lane.getLastStepOccupancy(lane_id)
            mean_speed = traci.lane.getLastStepMeanSpeed(lane_id)
            waiting_time = traci.lane.getWaitingTime(lane_id)
            
            # Calculate queue (vehicles with speed < 0.1 m/s)
            queue_length = sum(1 for vid in vehicle_ids 
                             if traci.vehicle.getSpeed(vid) < 0.1)
            
            return LaneData(
                lane_id=lane_id,
                vehicle_count=vehicle_count,
                occupancy=occupancy,
                mean_speed=mean_speed,
                waiting_time=waiting_time,
                queue_length=queue_length
            )
        except traci.exceptions.TraCIException:
            return LaneData(lane_id, 0, 0.0, 0.0, 0.0, 0)
    
    @staticmethod
    def get_approach_data(direction: str) -> ApproachData:
        """
        Get aggregated traffic data for an approach direction.
        
        Args:
            direction: 'north', 'south', 'east', or 'west'
            
        Returns:
            ApproachData with aggregated metrics
        """
        lanes = APPROACH_LANES.get(direction, [])
        
        total_vehicles = 0
        total_waiting_time = 0.0
        total_speed = 0.0
        total_queue = 0
        
        for lane_id in lanes:
            lane_data = DetectorInterface.get_lane_data(lane_id)
            total_vehicles += lane_data.vehicle_count
            total_waiting_time += lane_data.waiting_time
            total_speed += lane_data.mean_speed
            total_queue += lane_data.queue_length
        
        mean_speed = total_speed / len(lanes) if lanes else 0.0
        
        # Calculate pressure (combination of vehicle count and waiting time)
        pressure = total_vehicles + (total_waiting_time * 0.1)
        
        return ApproachData(
            direction=direction,
            total_vehicles=total_vehicles,
            total_waiting_time=total_waiting_time,
            mean_speed=mean_speed,
            queue_length=total_queue,
            pressure=pressure
        )
    
    @staticmethod
    def get_all_approach_data() -> Dict[str, ApproachData]:
        """Get data for all approach directions."""
        return {
            direction: DetectorInterface.get_approach_data(direction)
            for direction in ['north', 'south', 'east', 'west']
        }
    
    @staticmethod
    def get_induction_loop_data(detector_id: str) -> Dict[str, Any]:
        """
        Get data from an E1 induction loop detector.
        
        Args:
            detector_id: The detector identifier
            
        Returns:
            Dictionary with detector readings
        """
        try:
            return {
                'vehicle_count': traci.inductionloop.getLastStepVehicleNumber(detector_id),
                'mean_speed': traci.inductionloop.getLastStepMeanSpeed(detector_id),
                'occupancy': traci.inductionloop.getLastStepOccupancy(detector_id),
                'vehicle_ids': traci.inductionloop.getLastStepVehicleIDs(detector_id),
            }
        except traci.exceptions.TraCIException:
            return {'vehicle_count': 0, 'mean_speed': 0.0, 'occupancy': 0.0, 'vehicle_ids': []}


# ============================================== #
# TRAFFIC LIGHT CONTROL
# ============================================== #

class TrafficLightController:
    """Interface for controlling traffic light states."""
    
    def __init__(self, junction_id: str = None):
        """
        Initialize the traffic light controller.
        
        Args:
            junction_id: The traffic light junction ID
        """
        self.junction_id = junction_id or traffic_light_config.junction_id
        self.current_phase = 0
        self.phase_start_time = 0.0
        
    def get_current_phase(self) -> int:
        """Get the current traffic light phase index."""
        try:
            return traci.trafficlight.getPhase(self.junction_id)
        except traci.exceptions.TraCIException:
            return 0
    
    def get_current_state(self) -> str:
        """Get the current traffic light state string (e.g., 'GGGrrr')."""
        try:
            return traci.trafficlight.getRedYellowGreenState(self.junction_id)
        except traci.exceptions.TraCIException:
            return ""
    
    def set_phase(self, phase_index: int):
        """
        Set the traffic light to a specific phase.
        
        Args:
            phase_index: The phase index to set
        """
        try:
            traci.trafficlight.setPhase(self.junction_id, phase_index)
            self.current_phase = phase_index
            self.phase_start_time = traci.simulation.getTime()
        except traci.exceptions.TraCIException as e:
            print(f"[ERROR] Failed to set phase: {e}")
    
    def set_phase_duration(self, duration: float):
        """
        Set the remaining duration for the current phase.
        
        Args:
            duration: Duration in seconds
        """
        try:
            traci.trafficlight.setPhaseDuration(self.junction_id, duration)
        except traci.exceptions.TraCIException as e:
            print(f"[ERROR] Failed to set phase duration: {e}")
    
    def get_phase_duration(self) -> float:
        """Get the remaining duration of the current phase."""
        try:
            return traci.trafficlight.getNextSwitch(self.junction_id) - traci.simulation.getTime()
        except traci.exceptions.TraCIException:
            return 0.0
    
    def get_time_in_phase(self) -> float:
        """Get time spent in current phase."""
        return traci.simulation.getTime() - self.phase_start_time
    
    def set_program(self, program_id: str):
        """
        Switch to a different traffic light program.
        
        Args:
            program_id: 'fixed' or 'adaptive'
        """
        try:
            traci.trafficlight.setProgram(self.junction_id, program_id)
        except traci.exceptions.TraCIException as e:
            print(f"[ERROR] Failed to set program: {e}")


# ============================================== #
# VEHICLE DATA INTERFACE
# ============================================== #

class VehicleInterface:
    """Interface for vehicle-level data and detection."""
    
    @staticmethod
    def get_all_vehicles() -> List[str]:
        """Get list of all vehicle IDs in simulation."""
        try:
            return list(traci.vehicle.getIDList())
        except traci.exceptions.TraCIException:
            return []
    
    @staticmethod
    def get_vehicle_data(vehicle_id: str) -> Dict[str, Any]:
        """
        Get comprehensive data for a specific vehicle.
        
        Args:
            vehicle_id: The vehicle identifier
            
        Returns:
            Dictionary with vehicle properties
        """
        try:
            return {
                'id': vehicle_id,
                'type': traci.vehicle.getTypeID(vehicle_id),
                'speed': traci.vehicle.getSpeed(vehicle_id),
                'position': traci.vehicle.getPosition(vehicle_id),
                'lane': traci.vehicle.getLaneID(vehicle_id),
                'edge': traci.vehicle.getRoadID(vehicle_id),
                'waiting_time': traci.vehicle.getWaitingTime(vehicle_id),
                'accumulated_waiting_time': traci.vehicle.getAccumulatedWaitingTime(vehicle_id),
                'distance': traci.vehicle.getDistance(vehicle_id),
            }
        except traci.exceptions.TraCIException:
            return {}
    
    @staticmethod
    def detect_emergency_vehicles(approaches: List[str] = None) -> List[EmergencyVehicle]:
        """
        Detect emergency vehicles approaching the junction.
        
        Args:
            approaches: List of approach directions to check (all if None)
            
        Returns:
            List of EmergencyVehicle objects
        """
        if approaches is None:
            approaches = ['north', 'south', 'east', 'west']
        
        emergency_vehicles = []
        
        for vehicle_id in VehicleInterface.get_all_vehicles():
            try:
                veh_type = traci.vehicle.getTypeID(vehicle_id)
                
                # Check if emergency vehicle
                if veh_type in EMERGENCY_VEHICLE_TYPES:
                    edge_id = traci.vehicle.getRoadID(vehicle_id)
                    lane_id = traci.vehicle.getLaneID(vehicle_id)
                    position = traci.vehicle.getLanePosition(vehicle_id)
                    speed = traci.vehicle.getSpeed(vehicle_id)
                    
                    # Check if on an incoming edge
                    for direction in approaches:
                        lanes = APPROACH_LANES.get(direction, [])
                        if lane_id in lanes or any(lane_id.startswith(l.rsplit('_', 1)[0]) for l in lanes):
                            # Calculate distance to junction (approximate)
                            lane_length = traci.lane.getLength(lane_id)
                            distance_to_junction = lane_length - position
                            
                            emergency_vehicles.append(EmergencyVehicle(
                                vehicle_id=vehicle_id,
                                vehicle_type=veh_type,
                                edge_id=edge_id,
                                lane_id=lane_id,
                                position=position,
                                speed=speed,
                                distance_to_junction=distance_to_junction
                            ))
                            break
            except traci.exceptions.TraCIException:
                continue
        
        return emergency_vehicles
    
    @staticmethod
    def get_average_waiting_time() -> float:
        """Calculate average waiting time across all vehicles."""
        vehicles = VehicleInterface.get_all_vehicles()
        if not vehicles:
            return 0.0
        
        total_waiting = sum(
            traci.vehicle.getWaitingTime(vid) 
            for vid in vehicles
        )
        return total_waiting / len(vehicles)
    
    @staticmethod
    def get_total_queue_length() -> int:
        """Get total number of queued vehicles (speed < 0.1 m/s)."""
        count = 0
        for vid in VehicleInterface.get_all_vehicles():
            try:
                if traci.vehicle.getSpeed(vid) < 0.1:
                    count += 1
            except:
                pass
        return count


# ============================================== #
# METRICS AGGREGATOR
# ============================================== #

class MetricsCollector:
    """Collects and aggregates simulation metrics."""
    
    def __init__(self):
        self.metrics_history = []
        
    def collect_instant_metrics(self) -> Dict[str, Any]:
        """Collect current simulation metrics."""
        all_approach_data = DetectorInterface.get_all_approach_data()
        
        metrics = {
            'simulation_time': traci.simulation.getTime(),
            'total_vehicles': sum(a.total_vehicles for a in all_approach_data.values()),
            'average_waiting_time': VehicleInterface.get_average_waiting_time(),
            'total_queue_length': VehicleInterface.get_total_queue_length(),
            'approach_data': {k: vars(v) for k, v in all_approach_data.items()},
        }
        
        self.metrics_history.append(metrics)
        return metrics
    
    def get_summary_statistics(self) -> Dict[str, float]:
        """Calculate summary statistics from collected metrics."""
        if not self.metrics_history:
            return {}
        
        avg_waiting = sum(m['average_waiting_time'] for m in self.metrics_history) / len(self.metrics_history)
        avg_queue = sum(m['total_queue_length'] for m in self.metrics_history) / len(self.metrics_history)
        max_queue = max(m['total_queue_length'] for m in self.metrics_history)
        
        return {
            'average_waiting_time': avg_waiting,
            'average_queue_length': avg_queue,
            'max_queue_length': max_queue,
            'total_samples': len(self.metrics_history),
        }
