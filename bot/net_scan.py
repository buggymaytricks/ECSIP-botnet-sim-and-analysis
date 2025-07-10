import socket,subprocess,threading,random,ipaddress,os,re
from concurrent.futures import ThreadPoolExecutor,as_completed

class AccurateScanner:
    def __init__(self):
        self.hosts=set()
        self.verified_hosts=set()
        self.lock=threading.Lock()
        self.scan_results = {}  # Map IP → list of {'port', 'service'}
        
    def host_found(self,ip):
        with self.lock:
            if ip not in self.hosts and self.verify_host(ip):
                self.hosts.add(ip)
                self.verified_hosts.add(ip)
                
    def port_results(self, ip, ports):
        if not ports:
            return
        verified_ports = [p for p in ports if self.verify_port(ip, p['port'])]
        if verified_ports:
            self.scan_results[ip] = verified_ports

        
    def verify_host(self,ip):
        """Double-check if host is actually alive"""
        try:
            # Quick TCP probe to common ports
            for port in [80,443,22,445]:
                try:
                    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
                        s.settimeout(0.5)
                        if s.connect_ex((ip,port))==0:
                            return True
                except:
                    pass
            
            # Ping verification
            cmd=['ping','-n','1','-w','500',ip] if os.name=='nt' else ['ping','-c','1','-W','1',ip]
            flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            r=subprocess.run(cmd,capture_output=True,timeout=2,creationflags=flags)
            return r.returncode==0
        except:
            pass
        return False
    
    def verify_port(self,ip,port):
        """Verify port is actually open with multiple checks"""
        attempts=0
        success=0
        
        for _ in range(3):  # Triple check
            try:
                with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    result=s.connect_ex((ip,port))
                    attempts+=1
                    if result==0:
                        success+=1
                        # Additional verification - try to send/receive data
                        try:
                            s.send(b'\r\n')
                            s.recv(1)
                        except:pass
            except:pass
        
        return success>=2  # At least 2/3 attempts must succeed
    
    def get_active_interfaces(self):
        """Get only active network interfaces"""
        nets=set()
        
        # Get local IP first
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8",80))
                local_ip=s.getsockname()[0]
                if not local_ip.startswith(('0.','127.','169.254.','224.','240.')):
                    nets.add(f"{'.'.join(local_ip.split('.')[:-1])}.0/24")
        except:pass
        
        # Get interface networks
        try:
            if os.name=='nt':
                r=subprocess.run(['ipconfig'],capture_output=True,text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
                for line in r.stdout.split('\n'):
                    if 'IPv4 Address' in line:
                        m=re.search(r'(\d+\.\d+\.\d+\.\d+)',line)
                        if m and not m.group(1).startswith(('0.','127.','169.254.','224.','240.')):
                            nets.add(f"{'.'.join(m.group(1).split('.')[:-1])}.0/24")
            else:
                r=subprocess.run(['hostname','-I'],capture_output=True,text=True,timeout=5)
                for ip in r.stdout.split():
                    if re.match(r'\d+\.\d+\.\d+\.\d+',ip) and not ip.startswith(('0.','127.','169.254.','224.','240.')):
                        nets.add(f"{'.'.join(ip.split('.')[:-1])}.0/24")
        except:pass
        
        return list(nets) if nets else ["192.168.1.0/24","192.168.0.0/24","10.0.0.0/24"]
    
    def arp_scan(self):
        """Only get verified ARP entries"""
        try:
            if os.name=='nt':
                r=subprocess.run(['arp','-a'],capture_output=True,text=True,timeout=3,creationflags=subprocess.CREATE_NO_WINDOW)
                for line in r.stdout.split('\n'):
                    if 'dynamic' in line.lower():
                        m=re.search(r'(\d+\.\d+\.\d+\.\d+)',line)
                        if m and not m.group(1).startswith(('0.','127.','169.254.','224.','240.')):
                            self.host_found(m.group(1))
            else:
                try:
                    with open('/proc/net/arp') as f:
                        for line in f:
                            parts=line.split()
                            if len(parts)>=6 and parts[2]!='00:00:00:00:00:00' and re.match(r'\d+\.\d+\.\d+\.\d+',parts[0]):
                                if not parts[0].startswith(('0.','127.','169.254.','224.','240.')):
                                    self.host_found(parts[0])
                except:pass
        except:pass
    
    def ping_host(self,ip):
        """Reliable ping check"""
        try:
            cmd=['ping','-n','1','-w','1000',ip] if os.name=='nt' else ['ping','-c','1','-W','2',ip]
            flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            r=subprocess.run(cmd,capture_output=True,timeout=3,creationflags=flags)
            if r.returncode==0:
                # Verify with additional ping
                r2=subprocess.run(cmd,capture_output=True,timeout=3,creationflags=flags)
                if r2.returncode==0:
                    self.host_found(ip,"Ping")
                    return True
        except:pass
        return False
    
    def tcp_probe(self,ip):
        """Accurate TCP probe with verification"""
        high_confidence_ports=[22,80,443,445]  # Ports likely to be open on real systems
        for port in high_confidence_ports:
            try:
                with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    if s.connect_ex((ip,port))==0:
                        # Verify connection is real
                        try:
                            s.send(b'\r\n')
                            data=s.recv(1024)
                            if data or len(data)==0:  # Any response or clean closure
                                self.host_found(ip,f"TCP:{port}")
                                return True
                        except:
                            # Connection established but no data - still valid
                            self.host_found(ip,f"TCP:{port}")
                            return True
            except:pass
        return False
    
    def scan_host(self,ip):
        """Comprehensive host verification"""
        return self.ping_host(ip) or self.tcp_probe(ip)
    
    def discover_network(self,net_str):
        """Efficient network discovery"""
        try:
            net=ipaddress.IPv4Network(net_str,strict=False)
            hosts=[str(h) for h in net.hosts()]
            if len(hosts)>100:hosts=random.sample(hosts,100)  # Limit for accuracy
            
            with ThreadPoolExecutor(max_workers=min(50,len(hosts))) as executor:
                list(executor.map(self.scan_host,hosts))
        except:pass
    
    def scan_port(self,ip,port):
        """Highly accurate port scanning"""
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
                s.settimeout(2.0)  # Longer timeout for accuracy
                result=s.connect_ex((ip,port))
                if result==0:
                    # Verify it's really open
                    services={21:'ftp',22:'ssh',23:'telnet',25:'smtp',53:'dns',80:'http',110:'pop3',135:'rpc',139:'netbios',143:'imap',443:'https',445:'smb',993:'imaps',995:'pop3s',1433:'mssql',1521:'oracle',3306:'mysql',3389:'rdp',5432:'postgresql',5900:'vnc',6379:'redis',8080:'http-alt',8443:'https-alt',3000:'node',5000:'flask',8000:'http-dev',8888:'jupyter',1723:'pptp',3128:'squid',5060:'sip',27017:'mongodb'}
                    try:
                        # Try to interact with the service
                        if port in [80,8080,8000,8888]:
                            s.send(b"GET / HTTP/1.0\r\n\r\n")
                            response=s.recv(100)
                            if b'HTTP' in response or b'html' in response.lower():
                                
                                return {'port':port,'service':services.get(port,f'tcp-{port}')}
                        elif port==22:
                            response=s.recv(100)
                            if b'SSH' in response:
                                return {'port':port,'service':'ssh'}
                        elif port==21:
                            response=s.recv(100)
                            if b'FTP' in response or b'220' in response:
                                return {'port':port,'service':'ftp'}
                        else:
                            # For other ports, connection success is enough
                            return {'port':port,'service':services.get(port,f'tcp-{port}')}
                    except:
                        # Connection succeeded but no banner - still count as open
                        return {'port':port,'service':services.get(port,f'tcp-{port}')}
        except:pass
        return None
    
    def comprehensive_port_scan(self,ip):
        """Accurate port scanning with validation"""
        all_open=[]
        
        # First scan common ports thoroughly
        common_ports=[21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,3306,3389,5432,5900,8080,8443]
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures={executor.submit(self.scan_port,ip,p):p for p in common_ports}
            for future in as_completed(futures):
                result=future.result()
                if result:all_open.append(result)
        
        # If common ports found, scan extended range
        if all_open:
            extended_ports=list(range(1,1024))+list(range(1433,1434))+list(range(3000,3001))+list(range(5000,5001))+list(range(8000,8001))+list(range(8080,8081))+list(range(8443,8444))+list(range(8888,8889))
            extended_ports=[p for p in extended_ports if p not in common_ports]
            random.shuffle(extended_ports)
            
            with ThreadPoolExecutor(max_workers=30) as executor:
                futures={executor.submit(self.scan_port,ip,p):
                    p for p in extended_ports[:200]}  # Limit for accuracy
                
                for future in as_completed(futures):
                    result=future.result()
                    if result:
                        all_open.append(result)
        
        return all_open
    
    # changed run to store data into output string and return it
    def run(self):
        # Phase 1: Accurate host discovery
        self.arp_scan()

        networks = self.get_active_interfaces()
        for network in networks:
            self.discover_network(network)

        # Phase 2: Verified port scanning
        if self.verified_hosts:
            host_list = sorted(self.verified_hosts, key=lambda ip: tuple(map(int, ip.split('.'))))

            def scan_host_wrapper(host):
                open_ports = self.comprehensive_port_scan(host)
                if open_ports:
                    self.port_results(host, open_ports)

            with ThreadPoolExecutor(max_workers=min(5, len(host_list))) as executor:
                list(executor.map(scan_host_wrapper, host_list))

        # Construct and return the report
        report = []
        report.append(f"[+] Discovered Hosts: {len(self.scan_results)}\n")

        for ip in sorted(self.scan_results.keys(), key=lambda ip: tuple(map(int, ip.split('.')))):
            report.append(f"[*] Host: {ip}")
            report.append("[+] Open Ports:")
            report.append("Port       Service")
            report.append("-------------------------")
            for entry in sorted(self.scan_results[ip], key=lambda x: x['port']):
                report.append(f"{entry['port']:<10} {entry['service']}")
            report.append("")  # blank line between hosts

        return "\n".join(report)

        
        
if __name__ == "__main__":
    try:
        output = AccurateScanner().run()
        print(output)
    except Exception as e:
        print(f"Error: {e}")
