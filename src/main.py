"""
Main Entry Point for Intelligent Traffic Management System
Runs SUMO simulation with either adaptive or fixed-time control.
"""

import os
import sys
import argparse
import time
from typing import Optional

# Ensure SUMO tools are in path
SUMO_HOME = os.environ.get('SUMO_HOME', r'C:\Program Files (x86)\Eclipse\Sumo')
if SUMO_HOME:
    tools_path = os.path.join(SUMO_HOME, 'tools')
    if tools_path not in sys.path:
        sys.path.append(tools_path)

from config import (
    simulation_config, validate_config, OUTPUT_DIR,
    SUMO_CFG
)
from traci_interface import (
    SUMOConnection, DetectorInterface, VehicleInterface, MetricsCollector
)
from logic import (
    create_controller, ControllerMode, PressureBasedController, 
    FixedTimeController, EfficiencyCalculator
)
from data_collector import DataCollector, SimulationLogger, ComparisonManager


# ============================================== #
# SIMULATION RUNNER
# ============================================== #

class SimulationRunner:
    """
    Main simulation runner that orchestrates SUMO simulation
    with traffic control logic.
    """
    
    def __init__(self, mode: str = 'adaptive', gui: bool = True):
        """
        Initialize the simulation runner.
        
        Args:
            mode: 'adaptive' or 'fixed'
            gui: Use SUMO-GUI if True
        """
        self.mode = mode
        self.gui = gui
        
        # Initialize components
        self.connection = SUMOConnection()
        self.controller = create_controller(mode)
        self.data_collector = DataCollector(mode)
        self.logger = SimulationLogger()
        self.metrics_collector = MetricsCollector()
        
        # State tracking
        self.running = False
        self.step_count = 0
        self.collection_interval = 10  # Collect data every N simulation steps
        
        # Live display
        self.live_display = None
        self.display_update_interval = 50  # Update display every N steps
        
    def run(self, duration: Optional[int] = None, on_step_callback=None, show_live_display: bool = True) -> dict:
        """
        Run the simulation.
        
        Args:
            duration: Simulation duration in seconds (uses config default if None)
            on_step_callback: Optional callback function called each step
            show_live_display: Show live traffic display window
            
        Returns:
            Dictionary with simulation results
        """
        duration = duration or simulation_config.simulation_duration
        
        # Validate configuration
        if not validate_config():
            self.logger.error("Configuration validation failed")
            return {'success': False, 'error': 'Configuration validation failed'}
        
        # Connect to SUMO
        if not self.connection.connect(gui=self.gui):
            self.logger.error("Failed to connect to SUMO")
            return {'success': False, 'error': 'SUMO connection failed'}
        
        self.running = True
        self.data_collector.start()
        self.logger.info(f"Starting {self.mode} simulation for {duration} seconds")
        
        # Start live display if enabled
        if show_live_display:
            try:
                from live_display import start_display, TrafficState
                self.live_display = start_display()
            except Exception as e:
                print(f"[WARNING] Could not start live display: {e}")
                self.live_display = None
        
        try:
            # Main simulation loop
            while self.running:
                # Get current time
                sim_time = self.connection.get_simulation_time()
                
                # Check if simulation should end
                if sim_time >= duration:
                    self.logger.info(f"Simulation completed at t={sim_time:.1f}s")
                    break
                
                # Step simulation
                if not self.connection.step():
                    break
                
                self.step_count += 1
                
                # Update controller
                decision = self.controller.update(sim_time)
                if decision:
                    self.controller.apply_decision(decision)
                    self.data_collector.record_phase_change(
                        sim_time,
                        self.controller.state.current_phase,
                        decision.phase_index,
                        decision.reason,
                        decision.duration
                    )
                    
                    # Log emergency events
                    if decision.priority_vehicle:
                        self.logger.emergency(
                            f"Preemption for {decision.priority_vehicle}",
                            sim_time
                        )
                
                # Collect metrics periodically
                if self.step_count % self.collection_interval == 0:
                    approach_data = {
                        k: vars(v) for k, v in 
                        DetectorInterface.get_all_approach_data().items()
                    }
                    controller_state = self.controller.get_statistics()
                    self.data_collector.collect_snapshot(
                        sim_time, approach_data, controller_state
                    )
                
                # Update live display
                if self.live_display and self.step_count % self.display_update_interval == 0:
                    try:
                        from live_display import TrafficState
                        approach_data = DetectorInterface.get_all_approach_data()
                        
                        # Get current green direction
                        current_green = getattr(self.controller.state, 'current_direction', 'unknown')
                        if hasattr(self.controller, 'current_direction'):
                            current_green = self.controller.current_direction
                        
                        state = TrafficState(
                            vehicle_counts={
                                d: approach_data[d].total_vehicles for d in approach_data
                            },
                            current_green=current_green,
                            waiting_times={
                                d: approach_data[d].total_waiting_time for d in approach_data
                            },
                            queue_lengths={
                                d: approach_data[d].queue_length for d in approach_data
                            },
                            simulation_time=sim_time,
                            phase_name=f"{current_green.upper()} GREEN" if current_green != 'unknown' else "--"
                        )
                        self.live_display.update_state(state)
                    except Exception as e:
                        pass  # Don't crash on display errors
                
                # Call step callback if provided
                if on_step_callback:
                    on_step_callback(sim_time, self.data_collector.get_real_time_data())
                
                # Log progress periodically
                if sim_time > 0 and sim_time % 300 == 0:  # Every 5 minutes
                    self.logger.info(
                        f"Progress: {sim_time/duration*100:.1f}% complete",
                        sim_time
                    )
        
        except KeyboardInterrupt:
            self.logger.warning("Simulation interrupted by user")
        
        except Exception as e:
            self.logger.error(f"Simulation error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.running = False
            self.connection.disconnect()
            self.logger.flush()
            
            # Stop live display
            if self.live_display:
                try:
                    from live_display import stop_display
                    stop_display()
                except:
                    pass
        
        # Export results
        self.data_collector.export_to_csv()
        summary = self.data_collector.get_summary_statistics()
        self.data_collector.export_summary(f"{self.mode}_summary.json")
        
        return {
            'success': True,
            'mode': self.mode,
            'duration': duration,
            'steps': self.step_count,
            'summary': summary,
        }
    
    def stop(self):
        """Stop the simulation gracefully."""
        self.running = False


# ============================================== #
# COMPARISON RUNNER
# ============================================== #

def run_comparison(duration: int = 3600, gui: bool = False) -> dict:
    """
    Run both fixed-time and adaptive simulations for comparison.
    
    Args:
        duration: Simulation duration for each mode
        gui: Use SUMO-GUI if True
        
    Returns:
        Comparison results
    """
    import traci
    
    comparison_manager = ComparisonManager()
    
    print("=" * 60)
    print("RUNNING COMPARISON: Fixed-Time vs Adaptive Control")
    print("=" * 60)
    
    # Run fixed-time simulation
    print("\n[PHASE 1] Running Fixed-Time Simulation...")
    fixed_runner = SimulationRunner(mode='fixed', gui=gui)
    fixed_results = fixed_runner.run(duration, show_live_display=False)
    
    if fixed_results['success']:
        comparison_manager.set_fixed_results(fixed_runner.data_collector)
        print(f"  ✓ Fixed-time completed: Avg Wait = {fixed_results['summary']['average_waiting_time']:.2f}s")
    else:
        print(f"  ✗ Fixed-time failed: {fixed_results.get('error', 'Unknown error')}")
        return {'error': 'Fixed-time simulation failed'}
    
    # Explicit cleanup between simulations
    print("\n[INFO] Preparing for next simulation...")
    try:
        traci.close()
    except:
        pass
    
    # Longer delay to ensure cleanup
    time.sleep(3)
    
    # Run adaptive simulation
    print("\n[PHASE 2] Running Adaptive Simulation...")
    adaptive_runner = SimulationRunner(mode='adaptive', gui=gui)
    adaptive_results = adaptive_runner.run(duration, show_live_display=False)
    
    if adaptive_results['success']:
        comparison_manager.set_adaptive_results(adaptive_runner.data_collector)
        print(f"  ✓ Adaptive completed: Avg Wait = {adaptive_results['summary']['average_waiting_time']:.2f}s")
    else:
        print(f"  ✗ Adaptive failed: {adaptive_results.get('error', 'Unknown error')}")
        return {'error': 'Adaptive simulation failed'}
    
    # Generate comparison
    comparison = comparison_manager.generate_comparison()
    comparison_manager.export_comparison()
    
    # Print results
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)
    
    comp = comparison['comparison']
    print(f"\nWaiting Time Improvement: {comp['waiting_time_improvement_percent']:.1f}%")
    print(f"Queue Length Improvement: {comp['queue_length_improvement_percent']:.1f}%")
    print(f"Overall Efficiency Score: {comp['overall_efficiency_score']:.1f}")
    print(f"\nRecommendation: {comp['recommendation']}")
    
    return comparison


# ============================================== #
# TEST CONNECTION
# ============================================== #

def test_connection():
    """Test SUMO connection without running full simulation."""
    print("Testing SUMO connection...")
    
    if not validate_config():
        print("✗ Configuration validation failed")
        return False
    
    connection = SUMOConnection()
    if connection.connect(gui=True):
        print("✓ SUMO connection successful")
        
        # Run a few steps
        for i in range(10):
            connection.step()
            sim_time = connection.get_simulation_time()
            print(f"  Step {i+1}: t={sim_time:.2f}s")
        
        connection.disconnect()
        return True
    else:
        print("✗ SUMO connection failed")
        return False


# ============================================== #
# CLI INTERFACE
# ============================================== #

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Intelligent Density-Based Traffic Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode adaptive              # Run adaptive control with GUI
  python main.py --mode fixed --no-gui        # Run fixed-time without GUI
  python main.py --compare --duration 1800    # Compare both modes for 30 minutes
  python main.py --test-connection            # Test SUMO connection
        """
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['adaptive', 'fixed'],
        default='adaptive',
        help='Controller mode (default: adaptive)'
    )
    
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=3600,
        help='Simulation duration in seconds (default: 3600)'
    )
    
    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Run without SUMO GUI (headless mode)'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Run comparison between fixed and adaptive modes'
    )
    
    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Test SUMO connection and exit'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    print("\n" + "=" * 60)
    print("  INTELLIGENT DENSITY-BASED TRAFFIC MANAGEMENT SYSTEM")
    print("=" * 60)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if args.test_connection:
        success = test_connection()
        sys.exit(0 if success else 1)
    
    if args.compare:
        results = run_comparison(duration=args.duration, gui=not args.no_gui)
        if 'error' in results:
            sys.exit(1)
    else:
        runner = SimulationRunner(mode=args.mode, gui=not args.no_gui)
        results = runner.run(duration=args.duration)
        
        if results['success']:
            print("\n" + "=" * 60)
            print("SIMULATION RESULTS")
            print("=" * 60)
            summary = results['summary']
            print(f"\nMode: {results['mode'].upper()}")
            print(f"Duration: {results['duration']} seconds")
            print(f"Total Steps: {results['steps']}")
            print(f"\nAverage Waiting Time: {summary['average_waiting_time']:.2f}s")
            print(f"Max Waiting Time: {summary['max_waiting_time']:.2f}s")
            print(f"Average Queue Length: {summary['average_queue_length']:.1f}")
            print(f"Max Queue Length: {summary['max_queue_length']}")
            print(f"\nPhase Changes: {summary['total_phase_changes']}")
            print(f"Emergency Events: {summary['emergency_events']}")
            print(f"Emergency Preemptions: {summary['emergency_preemptions']}")
            print(f"\nResults saved to: {OUTPUT_DIR}")
        else:
            print(f"\n✗ Simulation failed: {results.get('error', 'Unknown error')}")
            sys.exit(1)


if __name__ == '__main__':
    main()
