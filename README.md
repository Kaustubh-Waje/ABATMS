# 🚦 Intelligent Density-Based Traffic Management System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![SUMO](https://img.shields.io/badge/SUMO-1.14+-green.svg)](https://sumo.dlr.de)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.29+-red.svg)](https://streamlit.io)

An AI-powered adaptive traffic signal control system using SUMO simulation with real-time analytics dashboard. Implements pressure-based algorithms and emergency vehicle preemption for optimized traffic flow.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Algorithm Details](#-algorithm-details)
- [Results](#-results)
- [License](#-license)

---

## ✨ Features

### 🧠 Adaptive Signal Control
- **Pressure-Based Algorithm**: Dynamically allocates green time based on real-time traffic density
- **Emergency Preemption**: Automatic priority green for emergency vehicles
- **Dynamic Cycle Optimization**: Adjusts cycle length based on demand

### 📊 Analytics Dashboard
- Real-time visualization of waiting times and queue lengths
- Comparison between adaptive and fixed-time control
- System efficiency scoring

### 🚗 SUMO Integration
- 4-way X-junction with 3 lanes per approach
- Multi-type vehicles: Cars, Trucks, Emergency
- E1/E2/E3 detectors for comprehensive monitoring

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUMO SIMULATION ENGINE                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Network   │  │   Vehicles  │  │       Detectors         │  │
│  │  4-Way X    │  │  Car/Truck  │  │  E1/E2/E3 Induction    │  │
│  │  Junction   │  │  Emergency  │  │      Loops             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ TraCI
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PYTHON CONTROLLER                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  Pressure-Based │  │   Emergency  │  │    Data          │   │
│  │    Algorithm    │──│  Preemption  │──│   Collector      │   │
│  └─────────────────┘  └──────────────┘  └───────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 STREAMLIT DASHBOARD                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │  Real-Time   │  │  Comparison   │  │    Efficiency       │  │
│  │   Charts     │  │   Analysis    │  │      Score          │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Prerequisites

1. **Python 3.10+** - [Download](https://python.org/downloads)
2. **SUMO** - [Download](https://sumo.dlr.de/docs/Downloads.php)

### Quick Setup (Windows)

```bash
# Clone or download the project
cd d:\traffic_management

# Run the setup script
setup.bat
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set SUMO_HOME environment variable
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo
```

---

## 🚀 Usage

### Command Line Interface

```bash
# Run adaptive control simulation
python src/main.py --mode adaptive

# Run fixed-time baseline
python src/main.py --mode fixed

# Compare both modes
python src/main.py --compare

# Run without GUI (headless)
python src/main.py --mode adaptive --no-gui

# Custom duration (seconds)
python src/main.py --mode adaptive --duration 1800

# Test SUMO connection
python src/main.py --test-connection
```

### Analytics Dashboard

```bash
# Launch Streamlit dashboard
streamlit run dashboard/app.py
```

Open `http://localhost:8501` in your browser.

---

## 📁 Project Structure

```
traffic_management/
├── sumo_network/
│   ├── junction.net.xml      # 4-way road network
│   ├── vehicles.rou.xml      # Vehicle routes & flows
│   ├── detectors.add.xml     # Loop detector definitions
│   └── simulation.sumocfg    # SUMO configuration
├── src/
│   ├── config.py             # Configuration parameters
│   ├── traci_interface.py    # SUMO TraCI connection
│   ├── logic.py              # AI control algorithms
│   ├── data_collector.py     # Metrics collection
│   └── main.py               # Main entry point
├── dashboard/
│   ├── app.py                # Streamlit application
│   └── charts.py             # Plotly visualizations
├── docs/
│   └── Project_Report.md     # IEEE format report
├── output/                   # Simulation results
├── setup.bat                 # Windows setup script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 🔬 Algorithm Details

### Pressure-Based Control

The adaptive controller uses a weighted pressure formula:

```
Pressure = (Vehicle_Count × W1) + (Waiting_Time × W2) + (Queue_Length × W3)
```

Where:
- W1 = 1.0 (vehicle count weight)
- W2 = 0.5 (waiting time weight)
- W3 = 0.3 (queue length weight)

**Decision Logic:**
1. Compare pressure of current green direction vs opposing
2. Switch if: `opposing_pressure > current_pressure × threshold`
3. Extend green if demand persists (up to max_green_duration)

### Emergency Preemption

1. Detect emergency vehicles within 200m of junction
2. Determine approach direction
3. Immediately switch to green for that direction
4. Maintain green until emergency passes + cooldown period

---

## 📊 Results

### Expected Performance Improvements

| Metric | Fixed-Time | Adaptive | Improvement |
|--------|------------|----------|-------------|
| Avg Waiting Time | ~45s | ~32s | **~29%** |
| Avg Queue Length | ~12 | ~8 | **~33%** |
| Emergency Response | N/A | Priority | ✓ |

### Efficiency Score

The system calculates an efficiency score:
```
Score = (Wait_Improvement × 0.6) + (Queue_Improvement × 0.4)
```

Positive score indicates adaptive control outperforms fixed-time.

---

## 📝 Documentation

- [Project Report](docs/Project_Report.md) - Full IEEE format research paper
- Code documentation in each Python module

---

## 🛠 Troubleshooting

### SUMO Connection Failed
```
[ERROR] TraCI connection failed
```
**Solution:** Ensure SUMO_HOME is set correctly and SUMO is installed.

### Module Not Found
```
ModuleNotFoundError: No module named 'traci'
```
**Solution:** Add SUMO tools to Python path or reinstall with the venv activated.

---

## 📄 License

This project is developed for educational and research purposes.

---

## 👥 Authors

Traffic Management Research Team

---

*Built with ❤️ using SUMO, Python, and Streamlit*
