import os
import json
import shutil
import subprocess
import time
import re
from pathlib import Path

VERSION = "1.2.0"
DATA_FILE_NAME = "nightu_vps.json"
APP_NAME = "nightu"


# =========================
# BASIC FUNCTIONS
# =========================


def clear():
    os.system("clear" if os.name != "nt" else "cls")


def pause():
    try:
        input("\nPress ENTER to continue...")
    except EOFError:
        # Non-interactive environment
        pass


def command_exists(command):
    return shutil.which(command) is not None


def safe_run(cmd_list, capture_output=True):
    """Run a command given as a list (no shell). Returns CompletedProcess.

    Always use list form to avoid shell injection.
    """
    try:
        return subprocess.run(
            cmd_list,
            check=False,
            capture_output=capture_output,
            text=True,
        )
    except Exception as e:
        # Return a simple object-like structure with returncode and stderr
        class R:
            pass

        r = R()
        r.returncode = 1
        r.stdout = ""
        r.stderr = str(e)
        return r


def get_data_file_path():
    """Determine preferred data file location.

    Priority:
      1. If DATA_FILE exists in cwd (backwards compatibility) use it.
      2. Use XDG_CONFIG_HOME or ~/.config/<APP_NAME>/DATA_FILE_NAME
    """
    cwd_path = Path(DATA_FILE_NAME)
    if cwd_path.exists():
        return cwd_path

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        config_dir = Path(xdg) / APP_NAME
    else:
        config_dir = Path.home() / ".config" / APP_NAME

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / DATA_FILE_NAME


DATA_FILE = str(get_data_file_path())
CONFIG_FILE = str(Path(DATA_FILE).with_name("config.json"))


def load_vps():
    path = Path(DATA_FILE)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Backup corrupt file
        backup = path.with_suffix(".json.corrupt")
        path.replace(backup)
        print(f"⚠️ Warning: Corrupt data file moved to {backup}")
        return {}
    except Exception as e:
        print(f"Error reading data file: {e}")
        return {}


def save_vps(vps):
    path = Path(DATA_FILE)
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(vps, f, indent=4)
        tmp.replace(path)
    except Exception as e:
        print(f"Error saving data file: {e}")


def load_config():
    path = Path(CONFIG_FILE)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    path = Path(CONFIG_FILE)
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        tmp.replace(path)
    except Exception as e:
        print(f"Error saving config file: {e}")


# =========================
# Backend detection
# =========================


def validate_name(name):
    """Validate container name against a safe pattern.

    Docker allows letters, digits, underscores, periods and dashes.
    We require at least one alphanumeric character and limit length to 128.
    """
    if not name or len(name) > 128:
        return False
    return re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", name) is not None


def docker_permission_check(stderr_text):
    """Return True if stderr indicates permission problem."""
    if not stderr_text:
        return False
    low = stderr_text.lower()
    return (
        "permission denied" in low
        or "cannot connect to the docker daemon" in low
        or "got permission denied" in low
    )


def detect_backend():
    """Detect available backend: 'docker', 'podman', or 'ssh'.

    If neither docker nor podman is available locally, but an SSH remote
    is configured in config.json and ssh is available, return 'ssh'.
    """
    cfg = load_config()

    if command_exists("docker"):
        return "docker"
    if command_exists("podman"):
        return "podman"

    # If SSH remote configured and ssh client exists, use ssh backend
    if command_exists("ssh") and cfg.get("ssh_remote"):
        return "ssh"

    return None


def get_container_cmd(*args):
    """Return command list for container tool with given args.

    Supports local docker/podman or ssh remote (uses docker on remote).
    """
    backend = detect_backend()
    cfg = load_config()

    if backend == "docker":
        return ["docker"] + list(args)
    elif backend == "podman":
        return ["podman"] + list(args)
    elif backend == "ssh":
        remote = cfg.get("ssh_remote")
        if not remote:
            return ["docker"] + list(args)  # fallback
        # Build: ssh remote docker <args...>
        return ["ssh", remote, "docker"] + list(args)

    # Fallback to docker command; safe_run will report not found
    return ["docker"] + list(args)


def backend_available():
    return detect_backend() is not None


# =========================
# UI
# =========================


def banner():
    print(r"""
╔════════════════════════════════════════════╗
║        🌙 NIGHTU VPS MAKER                 ║
║               v1.2.0                      ║
║             VPS MANAGER                   ║
╚════════════════════════════════════════════╝
""")


# =========================
# VPS LIST
# =========================


def list_vps():
    clear()
    banner()

    vps = load_vps()

    if not vps:
        print("📭 No VPS created yet.")
        pause()
        return

    print("📋 VPS LIST\n")

    for name, data in vps.items():
        status = get_status(name)

        print(f"🌙 {name}")
        print(f"   Status : {status}")
        print(f"   CPU    : {data.get('cpu')} cores")
        print(f"   RAM    : {data.get('ram')} MB")
        print(f"   Disk   : {data.get('disk')} GB")
        print()


# =========================
# STATUS
# =========================


def get_status(name):
    if not backend_available():
        return "⚪ No container backend"

    cmd = get_container_cmd("inspect", "-f", "{{.State.Status}}", name)
    result = safe_run(cmd)

    if result.returncode != 0:
        # If stderr suggests permission issue, show helpful message
        if docker_permission_check(getattr(result, "stderr", "")):
            return "⚪ Docker permission error"
        return "⚪ NOT FOUND"

    status = (result.stdout or "").strip()

    if status == "running":
        return "🟢 RUNNING"
    elif status == "exited":
        return "🔴 STOPPED"
    elif status:
        return f"🟡 {status.upper()}"

    return "⚪ NOT FOUND"


# =========================
# CREATE VPS
# =========================


def create_vps():
    clear()
    banner()

    if not backend_available():
        # Offer to configure remote SSH if possible
        if command_exists("ssh"):
            print("❌ No local Docker/Podman found.")
            use_remote = input("Do you want to configure a remote Docker host via SSH? (user@host) [y/N]: ").strip().lower()
            if use_remote == "y" or use_remote == "yes":
                remote = input("Enter SSH target (user@host): ").strip()
                if remote:
                    # Test connection
                    print(f"Testing SSH connection to {remote}...")
                    test = safe_run(["ssh", remote, "docker", "ps"], capture_output=True)
                    if test.returncode == 0:
                        cfg = load_config()
                        cfg["ssh_remote"] = remote
                        save_config(cfg)
                        print("✅ Remote Docker host configured.")
                    else:
                        print("❌ Failed to connect to remote Docker host via SSH. Ensure SSH access and Docker installed on remote.")
                        print(test.stderr)
                        pause()
                        return
                else:
                    print("Cancelled.")
                    pause()
                    return
            else:
                print("Cancelled: No backend available.")
                pause()
                return
        else:
            print("❌ Docker/Podman not available and SSH not found. Cannot create VPS on this device.")
            print("Options: run on a Linux host with Docker, install Podman, or configure a remote Docker SSH target from another machine.")
            pause()
            return

    vps = load_vps()

    print("➕ CREATE VPS\n")

    name = input("VPS name: ").strip()

    if not validate_name(name):
        print("❌ Invalid name. Use letters, numbers, dashes, underscores or dots.")
        pause()
        return

    if name in vps:
        print("❌ A VPS with this name already exists.")
        pause()
        return

    ram = input("RAM in MB [2048]: ").strip() or "2048"
    cpu = input("CPU cores [2]: ").strip() or "2"
    disk = input("Disk in GB [10]: ").strip() or "10"

    try:
        ram = int(ram)
        cpu = int(cpu)
        disk = int(disk)

        if ram < 128 or cpu < 1 or disk < 1:
            raise ValueError

    except ValueError:
        print("❌ Invalid resource values.")
        pause()
        return

    print("\n🌙 Creating VPS...")

    image = "ubuntu:24.04"

    # Ensure image is available (pull if needed)
    print(f"📥 Pulling image {image} (this may take a while)...")
    pull_cmd = get_container_cmd("pull", image)
    pull = safe_run(pull_cmd)
    if pull.returncode != 0:
        if docker_permission_check(getattr(pull, "stderr", "")):
            print("❌ Docker permission error while pulling image. Try running with appropriate privileges.")
        else:
            print("❌ Failed to pull image:")
            print(getattr(pull, "stderr", ""))
        pause()
        return

    # Run container
    cmd = get_container_cmd(
        "run",
        "-d",
        "--name",
        name,
        "--memory",
        f"{ram}m",
        "--cpus",
        str(cpu),
        "--hostname",
        name,
        image,
        "sleep",
        "infinity",
    )

    result = safe_run(cmd)

    if result.returncode != 0:
        print("\n❌ Failed to create VPS.")
        if docker_permission_check(getattr(result, "stderr", "")):
            print("❌ Docker permission error. Make sure your user can access the Docker daemon.")
        else:
            print(getattr(result, "stderr", ""))
        pause()
        return

    vps[name] = {
        "ram": ram,
        "cpu": cpu,
        "disk": disk,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    save_vps(vps)

    print("\n✅ VPS CREATED!")
    print(f"Name : {name}")
    print(f"RAM  : {ram} MB")
    print(f"CPU  : {cpu} cores")
    print(f"Disk : {disk} GB")

    pause()


# =========================
# START
# =========================


def start_vps():
    name = select_vps()

    if not name:
        return

    print(f"\n▶️ Starting {name}...")
    res = safe_run(get_container_cmd("start", name))
    if res.returncode != 0:
        print("❌ Failed to start:")
        print(getattr(res, "stderr", ""))
    else:
        print("✅ Done.")
    pause()


# =========================
# STOP
# =========================


def stop_vps():
    name = select_vps()

    if not name:
        return

    print(f"\n⏹️ Stopping {name}...")
    res = safe_run(get_container_cmd("stop", name))
    if res.returncode != 0:
        print("❌ Failed to stop:")
        print(getattr(res, "stderr", ""))
    else:
        print("✅ Done.")
    pause()


# =========================
# RESTART
# =========================


def restart_vps():
    name = select_vps()

    if not name:
        return

    print(f"\n🔄 Restarting {name}...")
    res = safe_run(get_container_cmd("restart", name))
    if res.returncode != 0:
        print("❌ Failed to restart:")
        print(getattr(res, "stderr", ""))
    else:
        print("✅ Done.")
    pause()


# =========================
# INFO
# =========================


def vps_info():
    name = select_vps()

    if not name:
        return

    vps = load_vps()
    data = vps.get(name, {})

    clear()
    banner()

    print(f"""
🌙 VPS INFORMATION

Name       : {name}
Status     : {get_status(name)}
CPU        : {data.get('cpu')} cores
RAM        : {data.get('ram')} MB
Disk       : {data.get('disk')} GB
Created    : {data.get('created')}
""")

    if backend_available():
        print("📊 Docker stats:\n")
        res = safe_run(get_container_cmd("stats", name, "--no-stream", "--format", "CPU: {{.CPUPerc}} | RAM: {{.MemUsage}}"))
        if res.returncode == 0:
            print(getattr(res, "stdout", ""))
        else:
            print(getattr(res, "stderr", ""))

    pause()


# =========================
# RENAME
# =========================


def rename_vps():
    old_name = select_vps()

    if not old_name:
        return

    vps = load_vps()

    new_name = input("New VPS name: ").strip()

    if not validate_name(new_name):
        print("❌ Invalid name.")
        pause()
        return

    if new_name in vps:
        print("❌ That name already exists.")
        pause()
        return

    result = safe_run(get_container_cmd("rename", old_name, new_name))

    if result.returncode != 0:
        print("❌ Rename failed.")
        print(getattr(result, "stderr", ""))
        pause()
        return

    vps[new_name] = vps.pop(old_name)
    save_vps(vps)

    print("✅ VPS renamed.")
    pause()


# =========================
# CHANGE RAM
# =========================


def change_ram():
    name = select_vps()

    if not name:
        return

    vps = load_vps()

    new_ram = input("New RAM in MB: ").strip()

    try:
        new_ram = int(new_ram)

        if new_ram < 128:
            raise ValueError

    except ValueError:
        print("❌ Invalid RAM.")
        pause()
        return

    # Docker resource update
    result = safe_run(get_container_cmd("update", "--memory", f"{new_ram}m", name))

    if result.returncode != 0:
        print("❌ Failed to change RAM.")
        print(getattr(result, "stderr", ""))
        pause()
        return

    if name in vps:
        vps[name]["ram"] = new_ram
        save_vps(vps)

    print(f"✅ RAM changed to {new_ram} MB.")
    pause()


# =========================
# CHANGE CPU
# =========================


def change_cpu():
    name = select_vps()

    if not name:
        return

    vps = load_vps()

    new_cpu = input("New CPU cores: ").strip()

    try:
        new_cpu = int(new_cpu)

        if new_cpu < 1:
            raise ValueError

    except ValueError:
        print("❌ Invalid CPU.")
        pause()
        return

    result = safe_run(get_container_cmd("update", "--cpus", str(new_cpu), name))

    if result.returncode != 0:
        print("❌ Failed to change CPU.")
        print(getattr(result, "stderr", ""))
        pause()
        return

    if name in vps:
        vps[name]["cpu"] = new_cpu
        save_vps(vps)

    print(f"✅ CPU changed to {new_cpu} cores.")
    pause()


# =========================
# CHANGE DISK
# =========================


def change_disk():
    name = select_vps()

    if not name:
        return

    vps = load_vps()

    print("""
⚠️ Disk resizing depends on the host filesystem/storage driver.

For now Nightu will update the VPS storage configuration.
Actual filesystem expansion will be added in a future version.
""")

    new_disk = input("New disk size in GB: ").strip()

    try:
        new_disk = int(new_disk)

        if new_disk < 1:
            raise ValueError

    except ValueError:
        print("❌ Invalid disk size.")
        pause()
        return

    if name in vps:
        vps[name]["disk"] = new_disk
        save_vps(vps)

    print(f"✅ Disk configuration changed to {new_disk} GB.")
    pause()


# =========================
# ROOT ACCESS / SHELL
# =========================


def root_access():
    """Connect to a VPS container with root shell access."""
    name = select_vps()

    if not name:
        return

    status = get_status(name)
    
    # Check if VPS is running
    if "RUNNING" not in status:
        print("\n❌ VPS is not running. Start it first.")
        pause()
        return

    clear()
    banner()

    print(f"""
🔓 ROOT ACCESS - {name}

You're about to access the root shell of your VPS.
Type 'exit' to return to the menu.

Available options:
  • Install Pterodactyl Panel: curl -sSL https://get.pterodactyl.io | bash
  • Update system: apt update && apt upgrade -y
  • Install utilities: apt install -y curl wget git nano

""")

    input("Press ENTER to connect to root shell...")

    # Use exec to connect to the container interactively
    backend = detect_backend()
    cfg = load_config()

    if backend == "ssh":
        remote = cfg.get("ssh_remote")
        if remote:
            cmd = ["ssh", remote, "docker", "exec", "-it", name, "/bin/bash"]
        else:
            cmd = ["docker", "exec", "-it", name, "/bin/bash"]
    else:
        cmd = get_container_cmd("exec", "-it", name, "/bin/bash")

    try:
        # Use os.system for interactive shell to allow full TTY
        os.system(" ".join(cmd))
        print("\n✅ Shell session closed.")
    except Exception as e:
        print(f"\n❌ Failed to access shell: {e}")

    pause()


# =========================
# DELETE
# =========================


def delete_vps():
    name = select_vps()

    if not name:
        return

    confirm = input(
        f"\n⚠️ Delete VPS '{name}' permanently? (yes/no): "
    ).lower()

    if confirm != "yes":
        print("Cancelled.")
        pause()
        return

    res = safe_run(get_container_cmd("rm", "-f", name))
    if res.returncode != 0:
        print("❌ Failed to delete:")
        print(getattr(res, "stderr", ""))
    else:
        vps = load_vps()
        if name in vps:
            del vps[name]
            save_vps(vps)
        print("🗑️ VPS deleted.")

    pause()


# =========================
# SELECT VPS
# =========================


def select_vps():
    vps = load_vps()

    if not vps:
        print("\n📭 No VPS available.")
        pause()
        return None

    names = list(vps.keys())

    print("\n🌙 VPS:\n")

    for i, name in enumerate(names, 1):
        print(f"{i}. {name} — {get_status(name)}")

    choice = input("\nSelect VPS: ").strip()

    try:
        index = int(choice) - 1

        if index < 0 or index >= len(names):
            raise ValueError

        return names[index]

    except ValueError:
        print("❌ Invalid selection.")
        pause()
        return None


# =========================
# VPS MANAGER
# =========================


def vps_manager():
    while True:
        clear()
        banner()

        print("""
╔════════════════════════════════════════════╗
║              🖥️ VPS MANAGER               ║
╠════════════════════════════════════════════╣
║                                            ║
║  1. ➕ Create VPS                           ║
║  2. ▶️  Start VPS                          ║
║  3. ⏹️  Stop VPS                           ║
║  4. 🔄 Restart VPS                         ║
║  5. 📊 VPS Info                            ║
║  6. ✏️  Rename VPS                         ║
║  7. 🧠 Change RAM                          ║
║  8. ⚡ Change CPU                          ║
║  9. 💾 Change Disk                         ║
║ 10. 📋 List VPS                            ║
║ 11. 🗑️  Delete VPS                         ║
║ 12. 🔓 Root Access                         ║
║                                            ║
║  0. ↩️  Back                               ║
╚════════════════════════════════════════════╝
""")

        choice = input("🌙 Nightu VPS > ").strip()

        if choice == "1":
            create_vps()

        elif choice == "2":
            start_vps()

        elif choice == "3":
            stop_vps()

        elif choice == "4":
            restart_vps()

        elif choice == "5":
            vps_info()

        elif choice == "6":
            rename_vps()

        elif choice == "7":
            change_ram()

        elif choice == "8":
            change_cpu()

        elif choice == "9":
            change_disk()

        elif choice == "10":
            list_vps()
            pause()

        elif choice == "11":
            delete_vps()

        elif choice == "12":
            root_access()

        elif choice == "0":
            break

        else:
            print("❌ Invalid option.")
            time.sleep(1)


# =========================
# SYSTEM INFO
# =========================


def system_info():
    clear()
    banner()

    print("🖥️ SYSTEM INFORMATION\n")

    res = safe_run(["uname", "-a"]) if shutil.which("uname") else None
    if res and res.returncode == 0:
        print(res.stdout)
    print()

    print(f"CPU cores: {os.cpu_count()}")

    try:
        total, used, free = shutil.disk_usage("/")
        print(f"Disk total: {total // (1024**3)} GB")
        print(f"Disk free : {free // (1024**3)} GB")
    except Exception:
        pass

    print(f"\nPython: {os.sys.version.split()[0]}")
    print(f"Container backend: {detect_backend() or 'none detected'}")

    pause()


# =========================
# MAIN
# =========================


def main():
    while True:
        clear()
        banner()

        print("""
╔════════════════════════════════════════════╗
║                                            ║
║  1. 🖥️  System Info                        ║
║  2. 🖥️  VPS Manager                        ║
║  3. 📦 Package Manager                     ║
║  4. ⛏️  Minecraft Manager                  ║
║  5. 🐳 Docker Manager                      ║
║  6. 💾 Backup Manager                      ║
║  7. 🛡️  Security                           ║
║  8. 📊 Monitor                             ║
║                                            ║
║  0. ❌ Exit                                ║
║                                            ║
╚════════════════════════════════════════════╝
""")

        choice = input("🌙 Nightu > ").strip()

        if choice == "1":
            system_info()

        elif choice == "2":
            vps_manager()

        elif choice == "0":
            clear()
            print("🌙 Nightu VPS Maker closed.")
            break

        else:
            print("\n🚧 This module is coming next!")
            time.sleep(1)


if __name__ == "__main__":
    main()
