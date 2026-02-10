"""
Data Collector Module
Handles real-time metrics collection, logging, and CSV export.
"""

import os
import csv
import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from collections import deque

from config import OUTPUT_DIR, HISTORY_DIR, output_config


# ============================================== #
# DATA STRUCTURES
# ============================================== #

@dataclass
class SimulationSnapshot:
    """Single snapshot of simulation state"""
    timestamp: float
    simulation_time: float
    total_vehicles: int
    average_waiting_time: float
    total_queue_length: int
    north_vehicles: int
    south_vehicles: int
    east_vehicles: int
    west_vehicles: int
    north_pressure: float
    south_pressure: float
    east_pressure: float
    west_pressure: float
    current_phase: int
    controller_mode: str
    emergency_active: bool = False


@dataclass
class PhaseChangeRecord:
    """Record of a traffic light phase change"""
    timestamp: float
    simulation_time: float
    from_phase: int
    to_phase: int
    reason: str
    duration: float


@dataclass
class EmergencyEvent:
    """Record of an emergency vehicle event"""
    timestamp: float
    simulation_time: float
    vehicle_id: str
    approach_direction: str
    preemption_triggered: bool
    response_time: float  # Time from detection to preemption


# ============================================== #
# DATA COLLECTOR
# ============================================== #

class DataCollector:
    """
    Collects, stores, and exports simulation metrics.
    Provides real-time data for dashboard visualization.
    """
    
    def __init__(self, mode: str = 'adaptive'):
        """
        Initialize the data collector.
        
        Args:
            mode: Controller mode ('adaptive' or 'fixed')
        """
        self.mode = mode
        self.config = output_config
        
        # Data storage
        self.snapshots: List[SimulationSnapshot] = []
        self.phase_changes: List[PhaseChangeRecord] = []
        self.emergency_events: List[EmergencyEvent] = []
        
        # Real-time buffers (for streaming to dashboard)
        self.buffer_size = 100
        self.waiting_time_buffer = deque(maxlen=self.buffer_size)
        self.queue_length_buffer = deque(maxlen=self.buffer_size)
        self.throughput_buffer = deque(maxlen=self.buffer_size)
        
        # Counters
        self.total_vehicles_processed = 0
        self.start_time = None
        self.last_collection_time = 0.0
        
        # Run ID and directory
        self.timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{self.timestamp_str}_{self.mode}"
        self.run_dir = os.path.join(HISTORY_DIR, self.run_id)
        
        # Ensure output directories exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(HISTORY_DIR, exist_ok=True)
        os.makedirs(self.run_dir, exist_ok=True)
        
    def start(self):
        """Start data collection session."""
        self.start_time = datetime.now()
        print(f"[DATA] Collection started at {self.start_time.isoformat()}")
        
    def collect_snapshot(self, simulation_time: float, approach_data: Dict, 
                        controller_state: Dict) -> SimulationSnapshot:
        """
        Collect a snapshot of current simulation state.
        
        Args:
            simulation_time: Current simulation time
            approach_data: Traffic data for all approaches
            controller_state: Current controller state
            
        Returns:
            SimulationSnapshot object
        """
        # Calculate totals
        total_vehicles = sum(d.get('total_vehicles', 0) for d in approach_data.values())
        total_queue = sum(d.get('queue_length', 0) for d in approach_data.values())
        
        # Calculate average waiting time
        total_waiting = sum(d.get('total_waiting_time', 0) for d in approach_data.values())
        avg_waiting = total_waiting / max(total_vehicles, 1)
        
        snapshot = SimulationSnapshot(
            timestamp=time.time(),
            simulation_time=simulation_time,
            total_vehicles=total_vehicles,
            average_waiting_time=avg_waiting,
            total_queue_length=total_queue,
            north_vehicles=approach_data.get('north', {}).get('total_vehicles', 0),
            south_vehicles=approach_data.get('south', {}).get('total_vehicles', 0),
            east_vehicles=approach_data.get('east', {}).get('total_vehicles', 0),
            west_vehicles=approach_data.get('west', {}).get('total_vehicles', 0),
            north_pressure=approach_data.get('north', {}).get('pressure', 0),
            south_pressure=approach_data.get('south', {}).get('pressure', 0),
            east_pressure=approach_data.get('east', {}).get('pressure', 0),
            west_pressure=approach_data.get('west', {}).get('pressure', 0),
            current_phase=controller_state.get('current_phase', 0),
            controller_mode=self.mode,
            emergency_active=controller_state.get('emergency_active', False)
        )
        
        # Store snapshot
        self.snapshots.append(snapshot)
        
        # Update real-time buffers
        self.waiting_time_buffer.append({
            'time': simulation_time,
            'value': avg_waiting
        })
        self.queue_length_buffer.append({
            'time': simulation_time,
            'value': total_queue
        })
        
        return snapshot
    
    def record_phase_change(self, simulation_time: float, from_phase: int, 
                           to_phase: int, reason: str, duration: float):
        """Record a traffic light phase change."""
        record = PhaseChangeRecord(
            timestamp=time.time(),
            simulation_time=simulation_time,
            from_phase=from_phase,
            to_phase=to_phase,
            reason=reason,
            duration=duration
        )
        self.phase_changes.append(record)
        
    def record_emergency_event(self, simulation_time: float, vehicle_id: str,
                               approach_direction: str, preemption_triggered: bool,
                               response_time: float = 0.0):
        """Record an emergency vehicle event."""
        event = EmergencyEvent(
            timestamp=time.time(),
            simulation_time=simulation_time,
            vehicle_id=vehicle_id,
            approach_direction=approach_direction,
            preemption_triggered=preemption_triggered,
            response_time=response_time
        )
        self.emergency_events.append(event)
        
    def get_real_time_data(self) -> Dict[str, Any]:
        """
        Get current real-time data for dashboard.
        
        Returns:
            Dictionary with current metrics and recent history
        """
        return {
            'waiting_time_history': list(self.waiting_time_buffer),
            'queue_length_history': list(self.queue_length_buffer),
            'latest_snapshot': asdict(self.snapshots[-1]) if self.snapshots else None,
            'total_snapshots': len(self.snapshots),
            'phase_changes_count': len(self.phase_changes),
            'emergency_events_count': len(self.emergency_events),
        }
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Calculate summary statistics from all collected data.
        
        Returns:
            Dictionary with aggregated statistics
        """
        if not self.snapshots:
            return {}
        
        # Waiting time statistics
        waiting_times = [s.average_waiting_time for s in self.snapshots]
        avg_waiting = sum(waiting_times) / len(waiting_times)
        max_waiting = max(waiting_times)
        min_waiting = min(waiting_times)
        
        # Queue length statistics
        queue_lengths = [s.total_queue_length for s in self.snapshots]
        avg_queue = sum(queue_lengths) / len(queue_lengths)
        max_queue = max(queue_lengths)
        
        # Phase statistics
        ns_phases = sum(1 for p in self.phase_changes if p.to_phase in [0])
        ew_phases = sum(1 for p in self.phase_changes if p.to_phase in [3])
        
        # Emergency statistics
        emergency_preemptions = sum(1 for e in self.emergency_events if e.preemption_triggered)
        
        return {
            'mode': self.mode,
            'total_samples': len(self.snapshots),
            'simulation_duration': self.snapshots[-1].simulation_time if self.snapshots else 0,
            
            # Waiting time
            'average_waiting_time': avg_waiting,
            'max_waiting_time': max_waiting,
            'min_waiting_time': min_waiting,
            
            # Queue length  
            'average_queue_length': avg_queue,
            'max_queue_length': max_queue,
            
            # Phase changes
            'total_phase_changes': len(self.phase_changes),
            'ns_green_phases': ns_phases,
            'ew_green_phases': ew_phases,
            
            # Emergency
            'emergency_events': len(self.emergency_events),
            'emergency_preemptions': emergency_preemptions,
        }
    
    def export_to_csv(self, filename: Optional[str] = None) -> str:
        """
        Export collected data to CSV file.
        
        Args:
            filename: Output filename (uses default if None)
            
        Returns:
            Path to the exported file
        """
        filename = filename or f"{self.mode}_{output_config.metrics_file}"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, 'w', newline='') as f:
            if self.snapshots:
                writer = csv.DictWriter(f, fieldnames=asdict(self.snapshots[0]).keys())
                writer.writeheader()
                for snapshot in self.snapshots:
                    writer.writerow(asdict(snapshot))
        
        print(f"[DATA] Exported {len(self.snapshots)} snapshots to {filepath}")
        
        # Also save to run directory
        run_filepath = os.path.join(self.run_dir, filename)
        with open(run_filepath, 'w', newline='') as f:
            if self.snapshots:
                writer = csv.DictWriter(f, fieldnames=asdict(self.snapshots[0]).keys())
                writer.writeheader()
                for snapshot in self.snapshots:
                    writer.writerow(asdict(snapshot))
        
        return filepath
    
    def export_summary(self, filename: str = "simulation_summary.json") -> str:
        """
        Export summary statistics to JSON file.
        
        Returns:
            Path to the exported file
        """
        filepath = os.path.join(OUTPUT_DIR, filename)
        summary = self.get_summary_statistics()
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"[DATA] Exported summary to {filepath}")
        
        # Also save to run directory
        run_filepath = os.path.join(self.run_dir, filename)
        with open(run_filepath, 'w') as f:
            json.dump(summary, f, indent=2)
            
        # Update history index
        self._update_history_index(summary)
        
        return filepath

    def _update_history_index(self, summary: Dict[str, Any]):
        """Update the history index file with this run."""
        index_file = os.path.join(HISTORY_DIR, 'index.json')
        history = []
        
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        # Add new entry
        entry = {
            'run_id': self.run_id,
            'timestamp': self.timestamp_str,
            'mode': self.mode,
            'summary': summary
        }
        history.append(entry)
        
        # Sort by timestamp descending
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        with open(index_file, 'w') as f:
            json.dump(history, f, indent=2)


# ============================================== #
# COMPARISON DATA MANAGER
# ============================================== #

class ComparisonManager:
    """
    Manages data for comparing adaptive vs fixed-time control.
    """
    
    def __init__(self):
        self.fixed_collector: Optional[DataCollector] = None
        self.adaptive_collector: Optional[DataCollector] = None
        
    def set_fixed_results(self, collector: DataCollector):
        """Store fixed-time simulation results."""
        self.fixed_collector = collector
        
    def set_adaptive_results(self, collector: DataCollector):
        """Store adaptive simulation results."""
        self.adaptive_collector = collector
        
    def generate_comparison(self) -> Dict[str, Any]:
        """
        Generate comparison between both modes.
        
        Returns:
            Dictionary with comparison metrics
        """
        if not self.fixed_collector or not self.adaptive_collector:
            return {'error': 'Both simulations must be run first'}
        
        fixed_stats = self.fixed_collector.get_summary_statistics()
        adaptive_stats = self.adaptive_collector.get_summary_statistics()
        
        # Calculate improvements
        def improvement(fixed, adaptive):
            if fixed == 0:
                return 0
            return ((fixed - adaptive) / fixed) * 100
        
        waiting_improvement = improvement(
            fixed_stats['average_waiting_time'],
            adaptive_stats['average_waiting_time']
        )
        
        queue_improvement = improvement(
            fixed_stats['average_queue_length'],
            adaptive_stats['average_queue_length']
        )
        
        # Calculate efficiency score
        efficiency_score = (waiting_improvement * 0.6) + (queue_improvement * 0.4)
        
        return {
            'fixed_time_results': fixed_stats,
            'adaptive_results': adaptive_stats,
            'comparison': {
                'waiting_time_improvement_percent': waiting_improvement,
                'queue_length_improvement_percent': queue_improvement,
                'overall_efficiency_score': efficiency_score,
                'adaptive_is_better': efficiency_score > 0,
                'recommendation': 'Adaptive control is recommended' if efficiency_score > 0 
                                 else 'Consider tuning adaptive parameters'
            }
        }
    
    def export_comparison(self, filename: str = "mode_comparison.json") -> str:
        """Export comparison results to JSON."""
        filepath = os.path.join(OUTPUT_DIR, filename)
        comparison = self.generate_comparison()
        
        with open(filepath, 'w') as f:
            json.dump(comparison, f, indent=2)
        
        return filepath


# ============================================== #
# LOGGER
# ============================================== #

class SimulationLogger:
    """Simple logging utility for simulation events."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file or os.path.join(OUTPUT_DIR, output_config.log_file)
        self.log_buffer = []
        
    def log(self, level: str, message: str, simulation_time: float = 0):
        """Log a message."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] [t={simulation_time:.1f}] {message}"
        
        self.log_buffer.append(log_entry)
        
        # Also print to console
        if level in ['ERROR', 'WARNING', 'EMERGENCY']:
            print(log_entry)
    
    def info(self, message: str, simulation_time: float = 0):
        self.log('INFO', message, simulation_time)
        
    def warning(self, message: str, simulation_time: float = 0):
        self.log('WARNING', message, simulation_time)
        
    def error(self, message: str, simulation_time: float = 0):
        self.log('ERROR', message, simulation_time)
        
    def emergency(self, message: str, simulation_time: float = 0):
        self.log('EMERGENCY', message, simulation_time)
    
    def flush(self):
        """Write buffered logs to file."""
        with open(self.log_file, 'a') as f:
            for entry in self.log_buffer:
                f.write(entry + '\n')
        self.log_buffer.clear()
