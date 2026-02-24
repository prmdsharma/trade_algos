import os
import sys
import argparse
import subprocess
import datetime
import yaml

# Load strategies from configuration file
def load_strategies():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies.yaml")
    if not os.path.exists(config_path):
        # Fallback/Default for compatibility during migration
        return {
            "sensex_scalping": {
                "enabled": True,
                "path": "sensex_scalping_algo",
                "live_script": "live_trade.py",
                "paper_script": "paper_trade.py",
                "pm2_live": "sensex-scalper",
                "pm2_paper": "sensex-paper",
                "report_tool": "tools/export_report.py"
            }
        }
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

STRATEGIES = load_strategies()

# Production server configuration
REMOTE_CONFIG = {
    "user": "ubuntu",
    "host": "80.225.201.34",
    "ssh_key": "~/ocip/ssh-key-2026-02-17.key",
    "remote_root": "~/trade_algos"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_log_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_command(command, cwd=None, capture=False, verbose=True):
    """Run a shell command and return result."""
    if verbose:
        print(f"[{get_log_time()}] EXEC: {command}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=capture, 
            text=True, 
            check=True
        )
        return result.stdout if capture else True
    except subprocess.CalledProcessError as e:
        print(f"[{get_log_time()}] ERROR: Command failed: {command}")
        if e.output:
            print(e.output)
        return False

def setup_strategy(name):
    """Set up virtual environment and install dependencies."""
    if name == "all":
        for s_name, config in STRATEGIES.items():
            if config.get("enabled", False):
                setup_strategy(s_name)
        return

    if name not in STRATEGIES:
        print(f"[{get_log_time()}] ERROR: Strategy '{name}' not found.")
        return

    strategy = STRATEGIES[name]
    strat_dir = os.path.join(BASE_DIR, str(strategy["path"]))
    
    print(f"[{get_log_time()}] 📦 Setting up {name}...")
    
    # Create venv if not exists
    venv_dir = os.path.join(strat_dir, "venv")
    if not os.path.exists(venv_dir):
        run_command("python3 -m venv venv", cwd=strat_dir)
    
    # Install requirements
    python_path = os.path.join(venv_dir, "bin", "python")
    req_file = os.path.join(strat_dir, "requirements.txt")
    if os.path.exists(req_file):
        run_command(f"{python_path} -m pip install -r requirements.txt", cwd=strat_dir)
    
    print(f"[{get_log_time()}] ✅ Setup complete for {name}.")

def deploy_strategy(name):
    """Deploy strategy to production server."""
    if name == "all":
        for s_name, config in STRATEGIES.items():
            if config.get("enabled", False):
                deploy_strategy(s_name)
        return

    if name not in STRATEGIES:
        print(f"[{get_log_time()}] ERROR: Strategy '{name}' not found.")
        return

    strategy = STRATEGIES[name]
    local_strat_dir = os.path.join(BASE_DIR, str(strategy["path"]))
    remote_strat_dir = os.path.join(str(REMOTE_CONFIG["remote_root"]), str(strategy["path"]))
    
    print(f"[{get_log_time()}] ⬆️ Deploying {name} to {REMOTE_CONFIG['host']}...")
    
    # 1. Create remote directory
    ssh_cmd = f"ssh -i {REMOTE_CONFIG['ssh_key']} {REMOTE_CONFIG['user']}@{REMOTE_CONFIG['host']}"
    run_command(f"{ssh_cmd} 'mkdir -p {remote_strat_dir}'")
    
    # 2. Sync files via rsync
    exclude_list = [
        ".env", "__pycache__", ".git", ".DS_Store", "database/*.db", 
        "logs/*", "venv", ".pytest_cache", "reports/*"
    ]
    excludes = " ".join([f"--exclude '{ex}'" for ex in exclude_list])
    
    rsync_cmd = (
        f"rsync -avz {excludes} "
        f"-e 'ssh -i {REMOTE_CONFIG['ssh_key']}' "
        f"{local_strat_dir}/ {REMOTE_CONFIG['user']}@{REMOTE_CONFIG['host']}:{remote_strat_dir}/"
    )
    run_command(rsync_cmd)
    
    # 3. Synchronize also the master script itself
    rsync_master = (
        f"rsync -avz -e 'ssh -i {REMOTE_CONFIG['ssh_key']}' "
        f"{os.path.join(BASE_DIR, 'algo_master.py')} "
        f"{REMOTE_CONFIG['user']}@{REMOTE_CONFIG['host']}:{REMOTE_CONFIG['remote_root']}/"
    )
    run_command(rsync_master)

    # 4. Finalize on remote (pip install)
    remote_finalize = (
        f"cd {remote_strat_dir} && "
        f"if [ ! -d \"venv\" ]; then python3 -m venv venv; fi && "
        f"venv/bin/python3 -m pip install -r requirements.txt"
    )
    run_command(f"{ssh_cmd} '{remote_finalize}'")

    print(f"[{get_log_time()}] ✅ Deployment complete for {name}.")

def start_strategy(name, mode=None):
    if name == "all":
        for s_name, config in STRATEGIES.items():
            if config.get("enabled", False):
                # Use strategy-specific mode if provided, else fall back
                s_mode = mode or config.get("mode", "paper")
                start_strategy(s_name, s_mode)
        return

    if name not in STRATEGIES:
        print(f"[{get_log_time()}] ERROR: Strategy '{name}' not found.")
        return

    strategy = STRATEGIES[name]
    strat_dir = os.path.join(BASE_DIR, str(strategy["path"]))
    
    # Mode priority: 1. CLI Argument, 2. Strategy Config, 3. Default (paper)
    active_mode = mode or strategy.get("mode", "paper")
    
    script = strategy["paper_script"] if active_mode == "paper" else strategy["live_script"]
    pm2_name = strategy["pm2_paper"] if active_mode == "paper" else strategy["pm2_live"]
    
    print(f"[{get_log_time()}] 🚀 Starting {name} in {active_mode} mode...")
    
    # 1. Sync latest code (local)
    # run_command("git pull origin master", cwd=strat_dir)
    
    # 2. Check PM2
    python_path = os.path.join(strat_dir, "venv", "bin", "python")
    # Use --cwd to ensure PM2 tracks the correct path
    start_cmd = f"pm2 start '{python_path} {script}' --name {pm2_name} --cwd {strat_dir}"
    
    pm2_exists = run_command(f"pm2 describe {pm2_name}", capture=True, verbose=False)
    if pm2_exists:
        # If it exists, delete and start fresh to update paths/scripts
        print(f"[{get_log_time()}] 🔄 Updating PM2 process for {pm2_name}...")
        run_command(f"pm2 delete {pm2_name}")
        run_command(start_cmd, cwd=strat_dir)
        run_command("pm2 save")
    else:
        run_command(start_cmd, cwd=strat_dir)
        run_command("pm2 save")

    print(f"[{get_log_time()}] ✅ {name} started via PM2.")

def stop_strategy(name):
    if name == "all":
        for s_name, config in STRATEGIES.items():
            if config.get("enabled", False):
                stop_strategy(s_name)
        return

    if name not in STRATEGIES:
        print(f"[{get_log_time()}] ERROR: Strategy '{name}' not found.")
        return

    strategy = STRATEGIES[name]
    pm2_paper = strategy["pm2_paper"]
    pm2_live = strategy["pm2_live"]
    
    for pm2_name in [pm2_paper, pm2_live]:
        if run_command(f"pm2 describe {pm2_name}", capture=True, verbose=False):
            print(f"[{get_log_time()}] ⏹️ Stopping {pm2_name}...")
            run_command(f"pm2 stop {pm2_name}")
            
            # Generate report if stopping paper mode
            if pm2_name == pm2_paper:
                generate_report(name)

def generate_report(name):
    if name == "all":
        for s_name, config in STRATEGIES.items():
            if config.get("enabled", False):
                generate_report(s_name)
        return

    strategy = STRATEGIES[name]
    strat_dir = os.path.join(BASE_DIR, strategy["path"])
    python_path = os.path.join(strat_dir, "venv", "bin", "python")
    report_tool = os.path.join(strat_dir, strategy["report_tool"])
    
    report_name = f"reports/{name}_summary_{datetime.datetime.now().strftime('%Y-%m-%d')}.csv"
    os.makedirs(os.path.join(strat_dir, "reports"), exist_ok=True)
    
    print(f"[{get_log_time()}] 📊 Generating report for {name}...")
    run_command(f"{python_path} {report_tool} {report_name} today", cwd=strat_dir)

def show_status():
    print(f"\n--- Strategy Status Summary [{get_log_time()}] ---")
    run_command("pm2 list")

def main():
    parser = argparse.ArgumentParser(description="AlgoMaster: Manage Trading Strategies")
    parser.add_argument("command", nargs="?", choices=["start", "stop", "status", "report", "setup", "deploy"], help="Command to execute")
    parser.add_argument("strategy", nargs="?", default="all", help="Strategy name or 'all'")
    parser.add_argument("--mode", choices=["paper", "live"], help="Mode for start command (overrides YAML)")

    args = parser.parse_args()

    if not args.command or args.command == "status":
        show_status()
    elif args.command == "start":
        start_strategy(args.strategy, args.mode)
    elif args.command == "stop":
        stop_strategy(args.strategy)
    elif args.command == "report":
        generate_report(args.strategy)
    elif args.command == "setup":
        setup_strategy(args.strategy)
    elif args.command == "deploy":
        deploy_strategy(args.strategy)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
