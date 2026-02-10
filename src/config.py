"""
Configuration Module for Intelligent Traffic Management System
Contains all simulation parameters, traffic light configurations, and algorithm thresholds.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ============================================== #
# SUMO PATHS AND ENVIRONMENT
# ============================================== #

# Try to get SUMO_HOME from environment, fallback to common paths
SUMO_HOME = os.environ.get('SUMO_HOME', r'C:\Program Files (x86)\Eclipse\Sumo')

# Add SUMO tools to Python path
if SUMO_HOME:
    SUMO_TOOLS = os.path.join(SUMO_HOME, 'tools')
    if SUMO_TOOLS not in os.sys.path:
        os.sys.path.append(SUMO_TOOLS)

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_DIR = os.path.join(PROJECT_ROOT, 'sumo_network')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

# SUMO configuration files
SUMO_CFG = os.path.join(NETWORK_DIR, 'simulation.sumocfg')
NETWORK_FILE = os.path.join(NETWORK_DIR, 'junction.net.xml')
ROUTE_FILE = os.path.join(NETWORK_DIR, 'vehicles.rou.xml')
DETECTOR_FILE = os.path.join(NETWORK_DIR, 'detectors.add.xml')


# ============================================== #
# SIMULATION PARAMETERS
# ============================================== #

@dataclass
class SimulationConfig:
    """Simulation runtime configuration"""
    step_length: float = 0.1          # Simulation step in seconds
    simulation_duration: int = 3600    # Total simulation time (1 hour)
    gui_mode: bool = True              # Use SUMO-GUI or headless
    delay: int = 0                     # GUI delay (ms) for visualization
    port: int = 8813                   # TraCI port
    max_retries: int = 3               # Connection retry attempts
    retry_delay: float = 2.0           # Seconds between retries


# ============================================== #
# TRAFFIC LIGHT CONFIGURATION
# ============================================== #

@dataclass
class TrafficLightConfig:
    """Traffic light phase and timing configuration"""
    junction_id: str = "center"
    
    # Phase indices for 4-phase rotation (North → East → South → West)
    PHASE_NORTH_GREEN: int = 0
    PHASE_NORTH_YELLOW: int = 1
    PHASE_EAST_GREEN: int = 2
    PHASE_EAST_YELLOW: int = 3
    PHASE_SOUTH_GREEN: int = 4
    PHASE_SOUTH_YELLOW: int = 5
    PHASE_WEST_GREEN: int = 6
    PHASE_WEST_YELLOW: int = 7
    
    # Fixed-time durations (seconds)
    fixed_green_duration: int = 30
    yellow_duration: int = 4
    
    # Adaptive timing bounds (seconds)
    min_green_duration: int = 10   # Minimum green time
    max_green_duration: int = 60   # Maximum green time
    extension_time: int = 3        # Green extension per detected vehicle
    
    # Cycle configuration  
    min_cycle_length: int = 60
    max_cycle_length: int = 180


# ============================================== #
# LANE AND EDGE CONFIGURATION
# ============================================== #

# Approach definitions: direction -> (incoming edge, outgoing edge)
APPROACHES: Dict[str, Tuple[str, str]] = {
    'north': ('north_in', 'north_out'),
    'south': ('south_in', 'south_out'),
    'east': ('east_in', 'east_out'),
    'west': ('west_in', 'west_out'),
}

# Lanes for each approach (3 lanes: right-turn, straight, left-turn)
APPROACH_LANES: Dict[str, List[str]] = {
    'north': ['north_in_0', 'north_in_1', 'north_in_2'],
    'south': ['south_in_0', 'south_in_1', 'south_in_2'],
    'east': ['east_in_0', 'east_in_1', 'east_in_2'],
    'west': ['west_in_0', 'west_in_1', 'west_in_2'],
}

# Detector IDs for each lane
LANE_DETECTORS: Dict[str, str] = {
    'north_in_0': 'det_north_0',
    'north_in_1': 'det_north_1',
    'north_in_2': 'det_north_2',
    'south_in_0': 'det_south_0',
    'south_in_1': 'det_south_1',
    'south_in_2': 'det_south_2',
    'east_in_0': 'det_east_0',
    'east_in_1': 'det_east_1',
    'east_in_2': 'det_east_2',
    'west_in_0': 'det_west_0',
    'west_in_1': 'det_west_1',
    'west_in_2': 'det_west_2',
}

# E3 Detector IDs for each approach
E3_DETECTORS: Dict[str, str] = {
    'north': 'e3_north',
    'south': 'e3_south',
    'east': 'e3_east',
    'west': 'e3_west',
}

# Queue detector IDs
QUEUE_DETECTORS: Dict[str, List[str]] = {
    'north': ['queue_north_0', 'queue_north_1', 'queue_north_2'],
    'south': ['queue_south_0', 'queue_south_1', 'queue_south_2'],
    'east': ['queue_east_0', 'queue_east_1', 'queue_east_2'],
    'west': ['queue_west_0', 'queue_west_1', 'queue_west_2'],
}


# ============================================== #
# ALGORITHM CONFIGURATION
# ============================================== #

@dataclass
class AlgorithmConfig:
    """Parameters for the adaptive control algorithms"""
    
    # Pressure-based algorithm weights
    vehicle_count_weight: float = 1.0      # Weight for vehicle count
    waiting_time_weight: float = 0.5       # Weight for accumulated waiting time
    queue_length_weight: float = 0.3       # Weight for queue length
    
    # Emergency preemption
    emergency_detection_distance: float = 200.0  # Distance to detect emergency (meters)
    emergency_preemption_time: int = 15          # Min green time for emergency (seconds)
    emergency_cooldown: int = 10                 # Cooldown after preemption (seconds)
    
    # Phase switching thresholds
    min_green_before_switch: float = 8.0   # Minimum green before allowing switch
    pressure_ratio_threshold: float = 1.5  # Switch if opposing pressure > this * current
    
    # Adaptive timing calculation
    saturation_headway: float = 2.0        # Seconds per vehicle at saturation flow
    lost_time_per_phase: float = 4.0       # Yellow + startup lost time


# ============================================== #
# VEHICLE CLASSIFICATION
# ============================================== #

# Vehicle type classes
VEHICLE_CLASSES = {
    'passenger': ['car', 'passenger'],
    'truck': ['truck', 'trailer'],
    'emergency': ['emergency', 'ambulance', 'fire'],
    'bus': ['bus', 'coach'],
}

EMERGENCY_VEHICLE_TYPES = ['emergency']


# ============================================== #
# OUTPUT AND LOGGING CONFIGURATION
# ============================================== #

@dataclass
class OutputConfig:
    """Configuration for data collection and output"""
    
    # Data collection intervals
    metrics_interval: int = 10          # Collect metrics every N seconds
    summary_interval: int = 60          # Log summary every N seconds
    
    # Output files
    metrics_file: str = "simulation_metrics.csv"
    comparison_file: str = "mode_comparison.csv"
    log_file: str = "simulation.log"
    
    # Enable/disable outputs
    save_detector_data: bool = True
    save_vehicle_data: bool = True
    save_traffic_light_data: bool = True


# ============================================== #
# DEFAULT INSTANCES
# ============================================== #

# Create default configuration instances
simulation_config = SimulationConfig()
traffic_light_config = TrafficLightConfig()
algorithm_config = AlgorithmConfig()
output_config = OutputConfig()


# ============================================== #
# SUMO COMMAND BUILDER
# ============================================== #

def get_sumo_command(gui: bool = True) -> List[str]:
    """
    Build the SUMO command with appropriate arguments.
    
    Args:
        gui: If True, use sumo-gui; otherwise use headless sumo
        
    Returns:
        List of command arguments for subprocess
    """
    sumo_binary = 'sumo-gui' if gui else 'sumo'
    
    # Try to find SUMO binary
    if SUMO_HOME:
        sumo_path = os.path.join(SUMO_HOME, 'bin', sumo_binary)
        if os.path.exists(sumo_path + '.exe'):  # Windows
            sumo_binary = sumo_path + '.exe'
        elif os.path.exists(sumo_path):
            sumo_binary = sumo_path
    
    cmd = [
        sumo_binary,
        '-c', SUMO_CFG,
        '--step-length', str(simulation_config.step_length),
        '--no-step-log', 'true',
        '--time-to-teleport', '-1',
    ]
    
    if gui:
        cmd.extend(['--delay', str(simulation_config.delay)])
    
    return cmd


def validate_config() -> bool:
    """
    Validate that all required files and paths exist.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    required_files = [NETWORK_FILE, ROUTE_FILE, DETECTOR_FILE, SUMO_CFG]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"[ERROR] Required file not found: {file_path}")
            return False
    
    # Create output directory if needed
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    return True
