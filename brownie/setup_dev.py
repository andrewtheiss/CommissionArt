import subprocess
import time
import json
import re
import psutil
import os
import shutil
import tempfile
import signal
import atexit
import sys

def check_command_exists(command):
    return shutil.which(command) is not None

def kill_other_script_instances():
    """Kill other instances of this script"""
    current_pid = os.getpid()
    current_script = os.path.basename(__file__)
    killed = False
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip current process
            if proc.info['pid'] == current_pid:
                continue
                
            # Check if it's a Python process
            if 'python' in proc.info['name'].lower():
                if proc.info['cmdline'] and any(current_script in cmd for cmd in proc.info['cmdline']):
                    print(f"Killing other instance of {current_script} (PID: {proc.info['pid']})")
                    proc.kill()
                    killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, IndexError):
            continue
    
    return killed

def kill_ganache_processes(force=False):
    killed = False
    for proc in psutil.process_iter(['name', 'pid', 'cmdline']):
        try:
            # Check process name and command line
            proc_name = str(proc.info['name']).lower()
            is_ganache = False
            
            if 'ganache' in proc_name:
                is_ganache = True
            elif proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline']).lower()
                if 'ganache' in cmdline:
                    is_ganache = True
            
            if is_ganache:
                print(f"Killing existing ganache process (PID: {proc.info['pid']})")
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, IndexError):
            continue
    return killed

def is_ganache_running():
    for proc in psutil.process_iter(['name', 'pid', 'cmdline']):
        try:
            # Check process name and command line
            proc_name = str(proc.info['name']).lower()
            if 'ganache' in proc_name:
                return True
            if proc.info['cmdline']:
                cmdline = ' '.join(str(cmd) for cmd in proc.info['cmdline']).lower()
                if 'ganache' in cmdline:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, IndexError):
            continue
    return False

# Kill other instances of this script
kill_other_script_instances()

# Check for --force flag or ALWAYS_FORCE env var
force_kill = '--force' in sys.argv or os.environ.get('ALWAYS_FORCE') == '1'

# Check if ganache is running
if is_ganache_running():
    if force_kill or '--auto' in sys.argv or input("Ganache is already running. Kill it? (y/n): ").lower() in ['y', 'yes']:
        print("Killing existing ganache processes...")
        kill_ganache_processes(force=True)
        # Give processes time to terminate
        time.sleep(1)
        
        if is_ganache_running():
            print("Warning: Failed to kill all ganache processes.")
            print("Please kill them manually with: pkill -9 -f ganache")
            exit(1)
    else:
        print("Exiting without making changes.")
        exit(0)

# Check if ganache-core or ganache is installed
ganache_command = None
if check_command_exists('ganache'):
    ganache_command = 'ganache'
elif check_command_exists('ganache-core'):
    ganache_command = 'ganache-core'
else:
    print("Error: Neither ganache nor ganache-core is installed.")
    print("Please install it using: npm install -g ganache")
    exit(1)

print(f"Using {ganache_command} for local blockchain...")

# Create a temporary file to capture output
temp_output_file = os.path.join(tempfile.gettempdir(), 'ganache_output.txt')

# Start Ganache in detached mode
print(f"Starting {ganache_command}...")

# Clear any existing config.json
if os.path.exists('config.json'):
    os.remove('config.json')

try:
    # Start ganache as a background process
    process = subprocess.Popen(
        [ganache_command], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Register process for cleanup on exit
    def cleanup():
        if process.poll() is None:  # If process is still running
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
    
    # Don't auto-kill ganache when script exits
    # atexit.register(cleanup)
    
    # Read output in real-time with a timeout
    output = []
    start_time = time.time()
    timeout = 20  # seconds
    found_private_key = False
    private_key = None
    
    print("Waiting for ganache to initialize...")
    while time.time() - start_time < timeout:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            print("Ganache process terminated unexpectedly")
            break
        
        if line:
            output.append(line)
            print(f"  {line.strip()}")
            
            # Look for private key in the output
            if not found_private_key and "Private Keys" in line:
                # The next line should have the first private key
                pk_line = process.stdout.readline()
                if pk_line:
                    output.append(pk_line)
                    print(f"  {pk_line.strip()}")
                    # Typical format: (0) 0xc23c48e840fd5cd8dc61a8b...
                    pk_match = re.search(r'\(\d+\)\s+(0x[a-fA-F0-9]+)', pk_line)
                    if pk_match:
                        private_key = pk_match.group(1)
                        found_private_key = True
            
            # If we see this, ganache is ready
            if "RPC Listening on" in line:
                # We're good to go, but continue reading a bit more for the private key
                if found_private_key:
                    break
        
        # Small delay to avoid CPU hogging
        time.sleep(0.1)
    
    # Check if we timed out
    if time.time() - start_time >= timeout and not found_private_key:
        print(f"Warning: Reached timeout waiting for ganache initialization")
    
    # Join all output and write to file for debugging
    full_output = ''.join(output)
    with open(temp_output_file, 'w') as f:
        f.write(full_output)
    
    # If we haven't found a private key yet, try to parse it from the collected output
    if not found_private_key:
        # Try various patterns for private keys
        patterns = [
            r'\(\d+\)\s+(0x[a-fA-F0-9]{64})',  # (0) 0x...
            r'Private Key:\s+(0x[a-fA-F0-9]{64})',
            r'privateKey["\']?:.*?(0x[a-fA-F0-9]{64})',
            r'(0x[a-fA-F0-9]{64})'  # Last resort: any 0x + 64 hex chars
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, full_output, re.IGNORECASE | re.DOTALL)
            if matches:
                private_key = matches[0]
                found_private_key = True
                break
    
    # If still no private key, use a default one
    if not found_private_key or not private_key:
        private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        print(f"Warning: Could not extract private key from ganache output.")
        print(f"Using default ganache test account private key as fallback.")

except Exception as e:
    print(f"Error starting ganache: {str(e)}")
    exit(1)

# Write to config.json
config = {
    'private_key': private_key,
    'blockchain_link': 'http://127.0.0.1:8545'
}

with open('config.json', 'w') as f:
    json.dump(config, f)

# Print success message and help text
print("\nSetup complete!")
print(f"Ganache is running at http://127.0.0.1:8545")
print(f"Private key saved to config.json: {private_key[:10]}...{private_key[-4:]}")
print(f"To stop Ganache, run 'pkill -9 -f ganache' or find its process ID and kill it.")
print("\nTIP: To always force-kill existing ganache instances, you can:")
print("1. Use the --force flag: python3 setup_dev.py --force")
print("2. Use the --auto flag for non-interactive mode: python3 setup_dev.py --auto")
print("3. Set an environment variable: export ALWAYS_FORCE=1")
print("4. Just press 'y' when prompted")


