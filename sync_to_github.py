import json
import os
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

REPO_PATH    = Path(config["github"]["repo_local_path"])
ACCOUNTS_CFG = config["mt5_accounts"]

def read_account(account_cfg):
    files_path = Path(account_cfg["files_path"])
    json_file  = files_path / "risk_data.json"
    if not json_file.exists():
        print(f"  [SKIP] No file found: {json_file}")
        return None
    try:
        with open(json_file, "r") as f:
            data = json.load(f)
        data["account_label"] = account_cfg.get("label", "Unknown")
        data["account_type"]  = account_cfg.get("account_type", "Unknown")
        data["platform"]      = account_cfg.get("platform", "MT5")
        return data
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None

def git(cmd):
    result = subprocess.run(
        ["git", "-C", str(REPO_PATH)] + cmd,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  [GIT ERROR] {result.stderr.strip()}")
        return False
    return True

def main():
    print(f"\n=== MT5 Risk Sync — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    accounts_data = []
    for acc in ACCOUNTS_CFG:
        print(f"  Reading: {acc['label']}")
        data = read_account(acc)
        if data:
            accounts_data.append(data)
            print(f"    Balance={data.get('balance','?')}  DailyPnL={data.get('daily_pnl','?')}  DD={data.get('drawdown_pct','?')}%")

    if not accounts_data:
        print("No data found. Make sure the EA is running in MT5.")
        sys.exit(0)

    merged = {
        "last_synced": datetime.now().isoformat(),
        "accounts_synced": len(accounts_data),
        "accounts": accounts_data
    }

    data_dir = REPO_PATH / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    with open(data_dir / "accounts_data.json", "w") as f:
        json.dump(merged, f, indent=2)

    snapshot_dir = data_dir / "history"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    with open(snapshot_dir / f"{date.today().isoformat()}.json", "w") as f:
        json.dump(merged, f, indent=2)

    git(["add", "."])
    msg = f"Risk sync — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    subprocess.run(["git", "-C", str(REPO_PATH), "commit", "-m", msg], capture_output=True, text=True)
    if git(["push", "origin", "main"]):
        print(f"  [OK] Pushed to GitHub!")
    print(f"Done. {len(accounts_data)} account(s) synced.\n")

if __name__ == "__main__":
    main()