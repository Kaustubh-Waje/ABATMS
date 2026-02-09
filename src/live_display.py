"""
Live Traffic Display Window
Shows real-time vehicle counts and traffic light status.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TrafficState:
    """Current traffic state data"""
    vehicle_counts: Dict[str, int]
    current_green: str
    waiting_times: Dict[str, float]
    queue_lengths: Dict[str, int]
    simulation_time: float
    phase_name: str


class LiveDisplayWindow:
    """Real-time traffic display window using Tkinter"""
    
    def __init__(self):
        self.root = None
        self.running = False
        self.thread = None
        self.current_state = None
        
        # UI elements
        self.direction_frames = {}
        self.vehicle_labels = {}
        self.wait_labels = {}
        self.queue_labels = {}
        self.light_indicators = {}
        self.time_label = None
        self.phase_label = None
        
    def start(self):
        """Start the display window in a separate thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run_window, daemon=True)
        self.thread.start()
        time.sleep(0.5)  # Allow window to initialize
        
    def stop(self):
        """Stop the display window"""
        self.running = False
        if self.root:
            try:
                self.root.quit()
            except:
                pass
    
    def _run_window(self):
        """Main window loop"""
        self.root = tk.Tk()
        self.root.title("🚦 Live Traffic Monitor")
        self.root.geometry("500x600")
        self.root.configure(bg='#1a1a2e')
        self.root.attributes('-topmost', True)  # Keep on top
        
        self._create_ui()
        self._update_loop()
        
        try:
            self.root.mainloop()
        except:
            pass
    
    def _create_ui(self):
        """Create the UI layout"""
        # Title
        title = tk.Label(
            self.root, 
            text="🚦 LIVE TRAFFIC MONITOR",
            font=('Segoe UI', 16, 'bold'),
            bg='#1a1a2e',
            fg='#00d4ff'
        )
        title.pack(pady=10)
        
        # Simulation time
        time_frame = tk.Frame(self.root, bg='#1a1a2e')
        time_frame.pack(fill='x', padx=20)
        
        self.time_label = tk.Label(
            time_frame,
            text="Time: 0.0s",
            font=('Consolas', 14),
            bg='#1a1a2e',
            fg='#ffffff'
        )
        self.time_label.pack(side='left')
        
        self.phase_label = tk.Label(
            time_frame,
            text="Phase: --",
            font=('Consolas', 14),
            bg='#1a1a2e',
            fg='#00ff88'
        )
        self.phase_label.pack(side='right')
        
        # Separator
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', pady=10)
        
        # Direction panels
        directions = [
            ('NORTH', '⬆️', '#16213e'),
            ('EAST', '➡️', '#16213e'),
            ('SOUTH', '⬇️', '#16213e'),
            ('WEST', '⬅️', '#16213e'),
        ]
        
        for direction, arrow, bg_color in directions:
            self._create_direction_panel(direction, arrow, bg_color)
        
        # Legend
        legend_frame = tk.Frame(self.root, bg='#1a1a2e')
        legend_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(legend_frame, text="🟢 GREEN = GO", font=('Segoe UI', 10), 
                bg='#1a1a2e', fg='#00ff00').pack(side='left', padx=10)
        tk.Label(legend_frame, text="🔴 RED = STOP", font=('Segoe UI', 10), 
                bg='#1a1a2e', fg='#ff4444').pack(side='left', padx=10)
    
    def _create_direction_panel(self, direction: str, arrow: str, bg_color: str):
        """Create a panel for one direction"""
        frame = tk.Frame(self.root, bg=bg_color, relief='raised', bd=2)
        frame.pack(fill='x', padx=20, pady=5)
        
        # Direction header with light indicator
        header = tk.Frame(frame, bg=bg_color)
        header.pack(fill='x', padx=10, pady=5)
        
        # Traffic light indicator (circle)
        light_canvas = tk.Canvas(header, width=30, height=30, bg=bg_color, highlightthickness=0)
        light_canvas.pack(side='left')
        light_id = light_canvas.create_oval(2, 2, 28, 28, fill='#444444', outline='#666666', width=2)
        self.light_indicators[direction.lower()] = (light_canvas, light_id)
        
        tk.Label(header, text=f"{arrow} {direction}", font=('Segoe UI', 14, 'bold'),
                bg=bg_color, fg='#ffffff').pack(side='left', padx=10)
        
        # Stats frame
        stats = tk.Frame(frame, bg=bg_color)
        stats.pack(fill='x', padx=10, pady=5)
        
        # Vehicle count
        self.vehicle_labels[direction.lower()] = tk.Label(
            stats, text="🚗 Vehicles: 0",
            font=('Consolas', 12), bg=bg_color, fg='#00d4ff'
        )
        self.vehicle_labels[direction.lower()].pack(side='left', padx=15)
        
        # Queue length
        self.queue_labels[direction.lower()] = tk.Label(
            stats, text="📊 Queue: 0",
            font=('Consolas', 12), bg=bg_color, fg='#ffaa00'
        )
        self.queue_labels[direction.lower()].pack(side='left', padx=15)
        
        # Wait time
        self.wait_labels[direction.lower()] = tk.Label(
            stats, text="⏱️ Wait: 0.0s",
            font=('Consolas', 12), bg=bg_color, fg='#ff6b6b'
        )
        self.wait_labels[direction.lower()].pack(side='left', padx=15)
        
        self.direction_frames[direction.lower()] = frame
    
    def _update_loop(self):
        """Update UI periodically"""
        if not self.running:
            return
        
        if self.current_state:
            self._refresh_display()
        
        if self.root:
            self.root.after(100, self._update_loop)  # Update every 100ms
    
    def _refresh_display(self):
        """Refresh all display elements"""
        state = self.current_state
        
        # Update time
        if self.time_label:
            self.time_label.config(text=f"Time: {state.simulation_time:.1f}s")
        
        if self.phase_label:
            self.phase_label.config(text=f"Phase: {state.phase_name}")
        
        # Update each direction
        for direction in ['north', 'east', 'south', 'west']:
            # Vehicle count
            count = state.vehicle_counts.get(direction, 0)
            if direction in self.vehicle_labels:
                self.vehicle_labels[direction].config(text=f"🚗 Vehicles: {count}")
            
            # Queue length
            queue = state.queue_lengths.get(direction, 0)
            if direction in self.queue_labels:
                self.queue_labels[direction].config(text=f"📊 Queue: {queue}")
            
            # Wait time
            wait = state.waiting_times.get(direction, 0)
            if direction in self.wait_labels:
                self.wait_labels[direction].config(text=f"⏱️ Wait: {wait:.1f}s")
            
            # Traffic light indicator
            if direction in self.light_indicators:
                canvas, oval_id = self.light_indicators[direction]
                if state.current_green == direction:
                    canvas.itemconfig(oval_id, fill='#00ff00', outline='#88ff88')
                else:
                    canvas.itemconfig(oval_id, fill='#ff0000', outline='#ff8888')
    
    def update_state(self, state: TrafficState):
        """Update the current traffic state"""
        self.current_state = state


# Singleton instance
_display_instance: Optional[LiveDisplayWindow] = None


def get_display() -> LiveDisplayWindow:
    """Get or create the live display window"""
    global _display_instance
    if _display_instance is None:
        _display_instance = LiveDisplayWindow()
    return _display_instance


def start_display():
    """Start the live display"""
    display = get_display()
    display.start()
    return display


def stop_display():
    """Stop the live display"""
    global _display_instance
    if _display_instance:
        _display_instance.stop()
        _display_instance = None
