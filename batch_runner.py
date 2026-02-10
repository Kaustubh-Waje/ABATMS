import subprocess
import sys
import time
import random
import os

def main():
    print("Starting batch generation of 20 runs...")
    
    modes = ['adaptive', 'fixed']
    
    # Define some "scenarios" by just varying duration significantly
    # Short runs (morning rush?), Long runs (day?), etc.
    # Note: density changes require config changes which we are avoiding as per user request.
    
    for i in range(1, 21):
        mode = random.choice(modes)
        # Random duration between 300s (5 min) and 1200s (20 min)
        duration = random.randint(300, 1200) 
        
        print(f"\n--- Run {i}/20: {mode.upper()} for {duration}s ---")
        
        cmd = [
            sys.executable, 
            'src/main.py', 
            '--mode', mode, 
            '--duration', str(duration), 
            '--no-gui'
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"Run {i} complete.")
        except subprocess.CalledProcessError as e:
            print(f"Run {i} failed: {e}")
        except KeyboardInterrupt:
            print("\nBatch generation stopped by user.")
            break
            
        time.sleep(2) # Cooldown

    print("\nBatch generation finished.")

if __name__ == '__main__':
    main()
