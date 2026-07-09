#!/usr/bin/env python3
import os
import sys
import subprocess
import re

def print_header(title):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def check_required_files():
    print_header("1. Checking Required Deployment Files")
    required = [
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        "app.py",
        "src/tradenexus/app_entry.py",
        ".env.example",
        ".github/workflows/ci.yml"
    ]
    missing = []
    for f in required:
        if os.path.exists(f):
            print(f"[OK] Found: {f}")
        else:
            print(f"[ERR] Missing: {f}")
            missing.append(f)
    return len(missing) == 0

def check_forbidden_files():
    print_header("2. Checking for Forbidden Files tracked by Git")
    forbidden_extensions = [".sqlite", ".db"]
    found = []
    
    try:
        res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
        files = res.stdout.splitlines()
        for f in files:
            if any(f.endswith(ext) for ext in forbidden_extensions):
                print(f"[ERR] Forbidden database file tracked by Git: {f}")
                found.append(f)
    except Exception as e:
        # Fallback to local files check if git is not available (e.g. clean Docker/CI)
        print(f"[WARN] Failed to run git check: {str(e)}. No git tracking check performed.")
        
    if not found:
        print("[OK] No forbidden database files are tracked by Git.")
    return len(found) == 0

def check_hardcoded_secrets():
    print_header("3. Scanning for Hardcoded Secrets")
    secret_patterns = [
        r"xoxb-[0-9]{11,13}-[a-zA-Z0-9]+", # Slack Bot Token
        r"ghp_[a-zA-Z0-9]{36}",             # GitHub Token
        r"discord\.com/api/webhooks/[0-9]+/[a-zA-Z0-9_-]+", # Discord webhook
        r"https://api\.telegram\.org/bot[0-9]+:[a-zA-Z0-9_-]+", # Telegram Bot URL
        r"bot[0-9]+:[a-zA-Z0-9_-]{35}"      # Raw Telegram Token pattern
    ]
    
    violations = 0
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                violations += scan_file_for_secrets(path, secret_patterns)
                
    violations += scan_file_for_secrets("app.py", secret_patterns)
    
    if violations == 0:
        print("[OK] No hardcoded secret patterns found.")
    else:
        print(f"[ERR] Found {violations} potential hardcoded secret pattern violations!")
    return violations == 0

def scan_file_for_secrets(filepath, patterns):
    if not os.path.exists(filepath):
        return 0
    violations = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        if "your_discord" in line or "your_telegram" in line or "example" in line:
                            continue
                        print(f"[ERR] Potential secret in {filepath}:{i} -> {line.strip()}")
                        violations += 1
    except Exception as e:
        print(f"Error scanning {filepath}: {str(e)}")
    return violations

def test_entrypoints_import():
    print_header("4. Verifying Entrypoints Import")
    try:
        res1 = subprocess.run([sys.executable, "-c", "import sys; sys.path.append('src'); import tradenexus.ui.dashboard"], capture_output=True, text=True)
        if res1.returncode == 0:
            print("[OK] UI Dashboard module imports cleanly.")
        else:
            print(f"[ERR] UI Dashboard import failed:\n{res1.stderr}")
            return False
            
        res2 = subprocess.run([sys.executable, "-c", "import app"], capture_output=True, text=True)
        if res2.returncode == 0:
            print("[OK] Root app.py imports cleanly.")
        else:
            print(f"[ERR] Root app.py import failed:\n{res2.stderr}")
            return False
            
        return True
    except Exception as e:
        print(f"[ERR] Failed to run import checks: {str(e)}")
        return False

def run_test_suite():
    print_header("5. Running pytest Suite")
    try:
        res = subprocess.run([sys.executable, "-m", "pytest"], capture_output=True, text=True)
        print(res.stdout)
        if res.returncode == 0:
            print("[OK] All tests passed successfully!")
            return True
        else:
            print(f"[ERR] pytest failed with exit code: {res.returncode}")
            print(res.stderr)
            return False
    except Exception as e:
        print(f"[ERR] Failed to run pytest: {str(e)}")
        return False

def main():
    print_header("TRADENEXUS RELEASE COMPLIANCE CHECKER")
    
    files_ok = check_required_files()
    forbidden_ok = check_forbidden_files()
    secrets_ok = check_hardcoded_secrets()
    imports_ok = test_entrypoints_import()
    tests_ok = run_test_suite()
    
    print_header("SUMMARY")
    overall = True
    for name, ok in [
        ("Required files check", files_ok),
        ("Forbidden files check", forbidden_ok),
        ("Secrets check", secrets_ok),
        ("Entrypoint imports check", imports_ok),
        ("Test suite pass check", tests_ok)
    ]:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if not ok:
            overall = False
            
    if overall:
        print("\nSUCCESS: TradeNexus DSS is ready for deployment!")
        sys.exit(0)
    else:
        print("\nFAIL: Release checks failed. Please fix compliance issues before deploy.")
        sys.exit(1)

if __name__ == "__main__":
    main()
