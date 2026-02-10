
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import sys
import os
import json
from pathlib import Path
from typing import List, Optional
import shutil

app = FastAPI(title="Traffic Control API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
HISTORY_DIR = OUTPUT_DIR / "history"
FRONTEND_DIR = BASE_DIR / "frontend"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)
FRONTEND_DIR.mkdir(exist_ok=True)

class SimulationRequest(BaseModel):
    mode: str = "adaptive"  # adaptive, fixed, comparison
    duration: int = 3600
    use_gui: bool = True

def run_simulation_task(req: SimulationRequest):
    """Background task to run the simulation."""
    cmd = [sys.executable, str(BASE_DIR / 'src' / 'main.py')]
    
    if req.mode == 'comparison':
        cmd.append('--compare')
    else:
        cmd.extend(['--mode', req.mode])
    
    cmd.extend(['--duration', str(req.duration)])
    
    if not req.use_gui:
        cmd.append('--no-gui')
        
    subprocess.run(cmd, cwd=str(BASE_DIR))

@app.post("/api/simulate")
async def start_simulation(req: SimulationRequest, background_tasks: BackgroundTasks):
    """Start a new simulation run."""
    background_tasks.add_task(run_simulation_task, req)
    return {"status": "started", "message": f"Simulation ({req.mode}) started in background"}

@app.get("/api/history")
async def get_history():
    """Get list of historical runs."""
    index_path = HISTORY_DIR / 'index.json'
    if index_path.exists():
        try:
            with open(index_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

@app.get("/api/run/{run_id}")
async def get_run_details(run_id: str):
    """Get details for a specific run."""
    run_dir = HISTORY_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    
    results = {}
    
    # Load summary
    for mode in ['adaptive', 'fixed']:
        summary_path = run_dir / f"{mode}_summary.json"
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                results[mode] = json.load(f)
                
    # Load comparison if exists
    comp_path = run_dir / 'mode_comparison.json'
    if comp_path.exists():
        with open(comp_path, 'r') as f:
            results['comparison'] = json.load(f)
            
    return results

@app.get("/api/data/{run_id}/{mode}")
async def get_run_data(run_id: str, mode: str):
    """Get raw time-series data (CSV) for a specific run."""
    run_dir = HISTORY_DIR / run_id
    if run_id == "latest":
        run_dir = OUTPUT_DIR
        
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")
        
    csv_path = run_dir / f"{mode}_simulation_metrics.csv"
    if not csv_path.exists():
        return []
        
    # Return as JSON records for easy frontend consumption
    import pandas as pd
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/latest")
async def get_latest_results():
    """Get results from the latest local run (output/ directory)."""
    results = {}
    for mode in ['adaptive', 'fixed']:
        summary_path = OUTPUT_DIR / f"{mode}_summary.json"
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                results[mode] = json.load(f)
                
    comp_path = OUTPUT_DIR / 'mode_comparison.json'
    if comp_path.exists():
        with open(comp_path, 'r') as f:
            results['comparison'] = json.load(f)
            
    return results

@app.get("/api/history/aggregate")
async def get_aggregate_history():
    """Get aggregated metrics across all historical runs, including latest."""
    runs = []
    
    # helper to process a directory
    def process_dir(d, run_id):
        data = {"run_id": run_id, "timestamp": "", "adaptive": {}, "fixed": {}}
        adaptive_path = d / "adaptive_summary.json"
        fixed_path = d / "fixed_summary.json"
        
        if adaptive_path.exists():
            with open(adaptive_path, 'r') as f:
                data["adaptive"] = json.load(f)
                
        if fixed_path.exists():
            with open(fixed_path, 'r') as f:
                data["fixed"] = json.load(f)
        
        # Include if AT LEAST ONE mode exists
        if adaptive_path.exists() or fixed_path.exists():
            runs.append(data)

    # 1. Process History
    if HISTORY_DIR.exists():
        for run_dir in HISTORY_DIR.iterdir():
            if run_dir.is_dir():
                process_dir(run_dir, run_dir.name)

    # 2. Process Latest (Output Dir)
    process_dir(OUTPUT_DIR, "latest_local")
    
    # Sort by run_id
    runs.sort(key=lambda x: x["run_id"])
    return runs

# Mount static files (Frontend)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
