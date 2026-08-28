import os
import json
import re
import shutil
import subprocess
import time

VERSION = "2.0.0"
DATA_FILE = os.path.expanduser("~/.nightu_vps.json")


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
CYAN = "\033[96m"
PURPLE = "\033[95m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
WHITE = "\033[97m"
GRAY = "\033[90m"


# ============================================================
# BASIC
# ============================================================

def clear():
    os.system("clear")


def pause():
    input(f"\n{GRAY}Apasă ENTER pentru a continua...{RESET}")


def command_exists(command):
    return shutil.which(command) is not None


def run(command):
    return subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True
    )


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"vps": {}}

    try:
        with open(DATA_FILE, "r") as file:
            data = json.load(file)

        if "vps" not in data:
            data["vps"] = {}

        return data

    except Exception:
        return {"vps": {}}


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


# ============================================================
# BANNER
# ============================================================

def banner():
    print(PURPLE + r"""
╔══════════════════════════════════════════════╗
║                                              ║
║          🌙 NIGHTU VPS MAKER                 ║
║                v1.0.0                        ║
║                                              ║
║              VPS MANAGEMENT                  ║
║                 BY NIGHTU                    ║
║                                              ║
╚══════════════════════════════════════════════╝
""" + RESET)


# ============================================================
# ENVIRONMENT
# ============================================================

def detect_environment():
    if "com.termux" in os.environ.get("PREFIX", ""):
        return "TERMUX"

    if os.path.exists("/data/data/com.termux"):
        return "TERMUX"

    if command_exists("docker"):
        return "LINUX + DOCKER"

    return "LINUX"


# ============================================================
# PROOT CHECK
# ============================================================

def check_proot():
    if not command_exists("proot-distro"):
        print(RED + "❌ proot-distro nu este instalat." + RESET)
        print()
        print("Instalează-l cu:")
        print("pkg update -y")
        print("pkg install proot-distro -y")
        pause()
        return False

    return True


# ============================================================
# VPS ID
# ============================================================

def make_id():
    data = load_data()

    number = 1

    while True:
        vps_id = f"nightu-vps-{number}"

        if vps_id not in data["vps"]:
            return vps_id

        number += 1


# ============================================================
# VALID NAME
# ============================================================

def clean_name(name):
    name = name.strip()

    name = re.sub(
        r"[^a-zA-Z0-9 _-]",
        "",
        name
    )

    return name[:32]


# ============================================================
# VPS STATUS
# ============================================================

def get_status(vps_id):
    if not check_proot_quiet():
        return "UNKNOWN"

    result = run("proot-distro ps")

    if result.returncode != 0:
        return "UNKNOWN"

    output = result.stdout.lower()

    if vps_id.lower() in output:
        return "🟢 RUNNING"

    return "⚪ STOPPED"


def check_proot_quiet():
    return command_exists("proot-distro")


# ============================================================
# CREATE VPS
# ============================================================

def create_vps():
    clear()
    banner()

    if not check_proot():
        return

    data = load_data()

    print(CYAN + "➕ CREATE NEW VPS\n" + RESET)

    name = input("🌙 VPS Name: ")
    name = clean_name(name)

    if not name:
        print(RED + "❌ Nume invalid." + RESET)
        pause()
        return

    print("""
Alege sistemul:

1. Ubuntu
2. Debian
3. Alpine
""")

    choice = input("🖥️ OS > ").strip()

    systems = {
        "1": "ubuntu",
        "2": "debian",
        "3": "alpine"
    }

    if choice not in systems:
        print(RED + "❌ OS invalid." + RESET)
        pause()
        return

    image = systems[choice]

    ram = input("🧠 RAM profil [2048 MB]: ").strip() or "2048"
    cpu = input("⚡ CPU profil [2 cores]: ").strip() or "2"
    disk = input("💾 Disk profil [10 GB]: ").strip() or "10"

    try:
        ram = int(ram)
        cpu = int(cpu)
        disk = int(disk)

        if ram <= 0 or cpu <= 0 or disk <= 0:
            raise ValueError

    except ValueError:
        print(RED + "❌ Resurse invalide." + RESET)
        pause()
        return

    vps_id = make_id()

    print()
    print(PURPLE + "🌙 Creating VPS..." + RESET)
    print(f"ID: {vps_id}")
    print(f"OS: {image}")

    command = (
        f"proot-distro install "
        f"--override-alias {vps_id} {image}"
    )

    result = subprocess.run(
        command,
        shell=True
    )

    if result.returncode != 0:
        print(RED + "\n❌ VPS creation failed." + RESET)
        pause()
        return

    data["vps"][vps_id] = {
        "name": name,
        "os": image,
        "ram": ram,
        "cpu": cpu,
        "disk": disk,
        "created": time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    save_data(data)

    print()
    print(GREEN + "╔════════════════════════════════════╗")
    print("║       ✅ VPS CREATED!              ║")
    print("╚════════════════════════════════════╝" + RESET)

    print(f"\n🌙 Name : {name}")
    print(f"🆔 ID   : {vps_id}")
    print(f"🖥️ OS   : {image}")
    print(f"🧠 RAM  : {ram} MB")
    print(f"⚡ CPU  : {cpu} cores")
    print(f"💾 Disk : {disk} GB")

    pause()


# ============================================================
# LIST VPS
# ============================================================

def list_vps():
    clear()
    banner()

    data = load_data()

    if not data["vps"]:
        print(YELLOW + "📭 Nu există VPS-uri." + RESET)
        pause()
        return

    print(CYAN + "📋 YOUR VPS SERVERS\n" + RESET)

    for number, (vps_id, info) in enumerate(
        data["vps"].items(),
        1
    ):
        status = get_status(vps_id)

        print(
            f"{PURPLE}{number}.{RESET} "
            f"{WHITE}{info['name']}{RESET}"
        )

        print(f"   ID     : {vps_id}")
        print(f"   Status : {status}")
        print(f"   OS     : {info['os']}")
        print(f"   CPU    : {info['cpu']} cores")
        print(f"   RAM    : {info['ram']} MB")
        print(f"   Disk   : {info['disk']} GB")
        print()

    pause()


# ============================================================
# SELECT VPS
# ============================================================

def select_vps():
    data = load_data()

    if not data["vps"]:
        print(YELLOW + "📭 Nu există VPS-uri." + RESET)
        pause()
        return None

    items = list(data["vps"].items())

    print()

    for i, (vps_id, info) in enumerate(items, 1):
        print(
            f"{i}. {info['name']} "
            f"({vps_id})"
        )

    choice = input("\n🌙 Select VPS > ").strip()

    try:
        index = int(choice) - 1

        if index < 0 or index >= len(items):
            raise ValueError

        return items[index][0]

    except ValueError:
        print(RED + "❌ Selecție invalidă." + RESET)
        pause()
        return None


# ============================================================
# START VPS
# ============================================================

def start_vps():
    clear()
    banner()

    if not check_proot():
        return

    data = load_data()

    vps_id = select_vps()

    if not vps_id:
        return

    info = data["vps"][vps_id]

    clear()
    banner()

    print(
        f"▶️ Pornesc {WHITE}{info['name']}{RESET}...\n"
    )

    print(
        GRAY +
        "Pentru PRoot, 'Start' deschide o sesiune Linux."
        + RESET
    )

    print()

    subprocess.run(
        f"proot-distro login {vps_id}",
        shell=True
    )


# ============================================================
# STOP VPS
# ============================================================

def stop_vps():
    clear()
    banner()

    if not check_proot():
        return

    print(CYAN + "⏹️ STOP VPS\n" + RESET)

    print(
        "PRoot nu este o VM clasică.\n"
        "Nightu poate opri sesiunile PRoot active.\n"
    )

    result = run("proot-distro ps")

    if result.stdout.strip():
        print(result.stdout)
    else:
        print("Nu există sesiuni active.")

    print()

    pid = input(
        "PID-ul sesiunii de oprit "
        "(ENTER pentru anulare): "
    ).strip()

    if not pid:
        return

    if not pid.isdigit():
        print(RED
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_vps(vps):
    with open(DATA_FILE, "w") as f:
        json.dump(vps, f, indent=4)


def docker_available():
    return command_exists("docker")


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
        print(f"   CPU    : {data['cpu']} cores")
        print(f"   RAM    : {data['ram']} MB")
        print(f"   Disk   : {data['disk']} GB")
        print()


# =========================
# STATUS
# =========================

def get_status(name):
    if not docker_available():
        return "⚪ Docker unavailable"

    result = subprocess.run(
        f"docker inspect -f '{{{{.State.Status}}}}' '{name}'",
        shell=True,
        capture_output=True,
        text=True
    )

    status = result.stdout.strip()

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

    if not docker_available():
        print("❌ Docker is not installed or unavailable.")
        print("Install Docker on a supported Linux VPS first.")
        pause()
        return

    vps = load_vps()

    print("➕ CREATE VPS\n")

    name = input("VPS name: ").strip()

    if not name:
        print("❌ Invalid name.")
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

    # Ubuntu container
    command = (
        f"docker run -d "
        f"--name '{name}' "
        f"--memory '{ram}m' "
        f"--cpus '{cpu}' "
        f"--hostname '{name}' "
        f"ubuntu:24.04 "
        f"sleep infinity"
    )

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("\n❌ Failed to create VPS.")
        print(result.stderr)
        pause()
        return

    vps[name] = {
        "ram": ram,
        "cpu": cpu,
        "disk": disk,
        "created": time.strftime("%Y-%m-%d %H:%M:%S")
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
    run(f"docker start '{name}'")
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
    run(f"docker stop '{name}'")
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
    run(f"docker restart '{name}'")
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
    data = vps[name]

    clear()
    banner()

    print(f"""
🌙 VPS INFORMATION

Name       : {name}
Status     : {get_status(name)}
CPU        : {data['cpu']} cores
RAM        : {data['ram']} MB
Disk       : {data['disk']} GB
Created    : {data['created']}
""")

    if docker_available():
        print("📊 Docker stats:\n")
        run(
            f"docker stats '{name}' --no-stream "
            "--format 'CPU: {{.CPUPerc}} | RAM: {{.MemUsage}}'"
        )

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

    if not new_name:
        print("❌ Invalid name.")
        pause()
        return

    if new_name in vps:
        print("❌ That name already exists.")
        pause()
        return

    result = subprocess.run(
        f"docker rename '{old_name}' '{new_name}'",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ Rename failed.")
        print(result.stderr)
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
    result = subprocess.run(
        f"docker update --memory '{new_ram}m' '{name}'",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ Failed to change RAM.")
        print(result.stderr)
        pause()
        return

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

    result = subprocess.run(
        f"docker update --cpus '{new_cpu}' '{name}'",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ Failed to change CPU.")
        print(result.stderr)
        pause()
        return

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

    vps[name]["disk"] = new_disk
    save_vps(vps)

    print(f"✅ Disk configuration changed to {new_disk} GB.")
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

    run(f"docker rm -f '{name}'")

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

    run("uname -a")
    print()

    print(f"CPU cores: {os.cpu_count()}")

    try:
        total, used, free = shutil.disk_usage("/")
        print(f"Disk total: {total // (1024**3)} GB")
        print(f"Disk free : {free // (1024**3)} GB")
    except:
        pass

    print(f"\nPython: {os.sys.version.split()[0]}")
    print(f"Docker: {'Installed' if docker_available() else 'Not installed'}")

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
