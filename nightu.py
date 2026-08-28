import os
import platform
import shutil
import subprocess
import time


VERSION = "1.0.0"


def clear():
    os.system("clear" if os.name != "nt" else "cls")


def run(command):
    try:
        subprocess.run(command, shell=True, check=False)
    except Exception as e:
        print(f"\n[!] Error: {e}")


def banner():
    print(r"""
╔══════════════════════════════════════════╗
║        🌙 NIGHTU VPS MAKER              ║
║              v1.0.0                     ║
╠══════════════════════════════════════════╣
║       VPS MANAGEMENT TOOL               ║
║             By Nightu                   ║
╚══════════════════════════════════════════╝
""")


def system_info():
    clear()
    banner()

    print("🖥️  SYSTEM INFORMATION\n")

    print(f"OS       : {platform.system()} {platform.release()}")
    print(f"Machine  : {platform.machine()}")
    print(f"Python   : {platform.python_version()}")

    cpu = os.cpu_count()
    print(f"CPU      : {cpu} cores")

    try:
        total, used, free = shutil.disk_usage("/")
        print(f"Disk     : {total // (1024**3)} GB")
        print(f"Free     : {free // (1024**3)} GB")
    except Exception:
        print("Disk     : unavailable")

    print("\nPress ENTER to return...")
    input()


def package_manager():
    clear()
    banner()

    print("""
📦 PACKAGE MANAGER

1. Update system
2. Install Git
3. Install Python
4. Install Node.js
5. Install Java
6. Install Nginx
0. Back
""")

    choice = input("Nightu > ")

    if choice == "1":
        run("pkg update -y 2>/dev/null || sudo apt update -y")
        run("pkg upgrade -y 2>/dev/null || sudo apt upgrade -y")

    elif choice == "2":
        run("pkg install git -y 2>/dev/null || sudo apt install git -y")

    elif choice == "3":
        run("pkg install python -y 2>/dev/null || sudo apt install python3 -y")

    elif choice == "4":
        run("pkg install nodejs -y 2>/dev/null || sudo apt install nodejs npm -y")

    elif choice == "5":
        run("pkg install openjdk-21 -y 2>/dev/null || sudo apt install openjdk-21-jre -y")

    elif choice == "6":
        run("sudo apt install nginx -y")

    input("\nPress ENTER...")


def minecraft_manager():
    clear()
    banner()

    print("""
⛏️ MINECRAFT MANAGER

1. Create server folder
2. Check Java
3. Start server
0. Back
""")

    choice = input("Nightu > ")

    if choice == "1":
        folder = input("Server folder name: ").strip()

        if not folder:
            print("Invalid folder name.")
        else:
            os.makedirs(folder, exist_ok=True)
            print(f"\n✅ Created: {folder}")

    elif choice == "2":
        run("java -version")

    elif choice == "3":
        folder = input("Server folder: ").strip()

        if os.path.isdir(folder):
            jar = input("Server JAR filename: ").strip()

            if os.path.isfile(os.path.join(folder, jar)):
                os.chdir(folder)
                run(f"java -Xms1G -Xmx2G -jar '{jar}' nogui")
            else:
                print("❌ JAR not found.")

    input("\nPress ENTER...")


def docker_manager():
    clear()
    banner()

    print("""
🐳 DOCKER MANAGER

1. Check Docker
2. Docker version
0. Back
""")

    choice = input("Nightu > ")

    if choice == "1":
        run("docker info")

    elif choice == "2":
        run("docker --version")

    input("\nPress ENTER...")


def backup_manager():
    clear()
    banner()

    print("""
💾 BACKUP MANAGER

1. Backup folder
0. Back
""")

    choice = input("Nightu > ")

    if choice == "1":
        source = input("Folder to backup: ").strip()

        if os.path.isdir(source):
            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            destination = f"{source}_backup_{timestamp}"

            shutil.copytree(source, destination)

            print(f"\n✅ Backup created:")
            print(destination)
        else:
            print("❌ Folder not found.")

    input("\nPress ENTER...")


def security():
    clear()
    banner()

    print("""
🛡️ SECURITY

1. Show current user
2. Show network information
0. Back
""")

    choice = input("Nightu > ")

    if choice == "1":
        run("whoami")

    elif choice == "2":
        run("ip addr 2>/dev/null || ifconfig")

    input("\nPress ENTER...")


def monitor():
    clear()
    banner()

    print("📊 VPS MONITOR\n")

    print("CPU:")
    run("uptime")

    print("\nMemory:")
    run("free -h 2>/dev/null || vm_stat")

    print("\nDisk:")
    run("df -h")

    input("\nPress ENTER...")


def main():
    while True:
        clear()
        banner()

        print("""
╔══════════════════════════════════════════╗
║                                          ║
║  1. 🖥️  System Info                     ║
║  2. 📦 Package Manager                   ║
║  3. ⛏️  Minecraft Manager                ║
║  4. 🐳 Docker Manager                    ║
║  5. 💾 Backup Manager                    ║
║  6. 🛡️  Security                        ║
║  7. 📊 VPS Monitor                       ║
║                                          ║
║  0. ❌ Exit                              ║
║                                          ║
╚══════════════════════════════════════════╝
""")

        choice = input("🌙 Nightu > ").strip()

        if choice == "1":
            system_info()

        elif choice == "2":
            package_manager()

        elif choice == "3":
            minecraft_manager()

        elif choice == "4":
            docker_manager()

        elif choice == "5":
            backup_manager()

        elif choice == "6":
            security()

        elif choice == "7":
            monitor()

        elif choice == "0":
            clear()
            print("🌙 Nightu VPS Maker closed.")
            break

        else:
            print("\n❌ Invalid option.")
            time.sleep(1)


if __name__ == "__main__":
    main()
