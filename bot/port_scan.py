import socket
import psutil
import threading
import queue
import time
import platform
import subprocess

def whoami():
    try:
        return subprocess.getoutput("whoami").strip()
    except Exception as e:
        return f"[!] Error running whoami: {e}"

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def get_mac_for_ip(target_ip):
    for iface_name, iface_addrs in psutil.net_if_addrs().items():
        stats = psutil.net_if_stats().get(iface_name)
        if not stats or not stats.isup:
            continue

        ip_found = False
        mac = None
        for addr in iface_addrs:
            if addr.family == socket.AF_INET and addr.address == target_ip:
                ip_found = True
            elif addr.family == psutil.AF_LINK or (hasattr(socket, 'AF_PACKET') and addr.family == socket.AF_PACKET):
                mac = addr.address

        if ip_found and mac:
            if any(v in iface_name.lower() for v in ['virtual', 'vmware', 'loopback', 'docker', 'pseudo']):
                continue
            return mac
    return None

def worker(ip, timeout, port_queue, results, lock):
    while not port_queue.empty():
        port = port_queue.get()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                if sock.connect_ex((ip, port)) == 0:
                    try:
                        service = socket.getservbyport(port)
                    except:
                        service = "unknown"
                    with lock:
                        results.append((port, service))
        except:
            pass
        finally:
            port_queue.task_done()

def scan_all_ports(ip, num_threads=100, timeout=0.01):
    port_queue = queue.Queue()
    results = []
    lock = threading.Lock()

    for port in range(1, 65536):
        port_queue.put(port)

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker, args=(ip, timeout, port_queue, results, lock))
        t.start()
        threads.append(t)

    port_queue.join()
    for t in threads:
        t.join()

    return sorted(results)


def main():
    try:
        start_time = time.time()

        ip = get_ip()
        mac = get_mac_for_ip(ip)

        if not ip or not mac:
            return "[-] Could not detect a valid external IP/MAC address."

        results = scan_all_ports(ip)

        info = {
            "IP": ip,
            "MAC": mac,
            "Hostname": socket.gethostname(),
            "System": platform.system(),
            "Release": platform.release()
        }

        output = "[+] Port Scan Report\n"
        output += f"Local IP: {ip}\nMAC Address: {mac}\n"
        output += f"System: {info['System']} {info['Release']}\n"
        output += f"Hostname: {info['Hostname']}\n"
        output += f"Scan Duration: {time.time() - start_time:.2f} seconds\n\n"

        if results:
            output += "[+] Open Ports:\n"
            output += f"{'Port':<10} {'Service'}\n"
            output += "-" * 25 + "\n"
            for port, service in results:
                output += f"{port:<10} {service}\n"
        else:
            output += "[-] No open ports found.\n"

        return output

    except Exception as e:
        return f"[!] Error during port_scan: {str(e)}"

# Keep this block if you want to test manually
if __name__ == "__main__":
    print(main())
