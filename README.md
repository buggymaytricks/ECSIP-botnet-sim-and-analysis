# 🕷️ Modular Botnet Simulation and Analysis

This project simulates a **custom botnet** in a secure and fully isolated VirtualBox environment. It includes:

- A **Flask-based Command and Control (C2) dashboard**
- **Python-based malware agents** (bots) for Linux and Windows
- A **target server** to demonstrate DDoS and scanning modules
- Basic **Wireshark-based traffic analysis**

> ⚠️ This project is strictly for educational and research purposes. All simulations were conducted in a closed, offline environment.

---

## 🎯 Project Objectives

- Simulate botnet behavior using modular bots
- Implement C2 dashboard for remote task control
- Explore malware modules (keylogger, scanner, DDoS, etc)
- Monitor traffic using Wireshark
- Ensure complete ethical containment in a virtual lab

---

## 🛠 Tech Stack

| Component       | Technology              |
|----------------|--------------------------|
| Bots           | Python                   |
| C2 Server      | Flask                    |
| Target Server  | Ubuntu + Flask           |
| Monitoring     | Wireshark                |
| VMs            | VirtualBox/VMWare/VPN   |

---

## 📁 Project Structure

```
modular-botnet-simulation/
├── bot/                # Linux and Windows bot clients
│   ├── bot.py
│   ├── bot.exe         # Windows binary file for bot
│   ├── bot             # Linux binary file for bot
│   ├── wordlist.txt    # Test wordlist for bruteforce attack on Test Website
│   ├── <all_modules>.py
│   └── requirements.txt
├── c2_server/           # Flask-based C2 interface
├── dos_target/          # Flask server to simulate DDoS attack
├── analysis/            # Wireshark logs, screenshots
├── docs/                # Scope, Report, Presentation (PDF)
├── requirements.txt
└── README.md
```

---

## 🔍 Implemented Modules

- `Keylogger`: Captures keystrokes
- `DoS`: HTTP flood on target server
- `net_scan`: Scans the network in which the bot is connected and sends the hosts that are up. (Not accurate)
- `port_scan`: Scans common ports on hosts that are up
- `brute_force`: Can perform bruteforce operations on SSH/FTP/HTTP-LOGIN
- `stealer`: Steals known secrets/credentials from Linux-(Fails to steal browser creds), on Windows only steals browser creds (only for chromium based browsers)
- `spyware`: Gets clipboard as well as captures screenshots

---

## 🚀 How to Run

### 1. Set Up the Virtual Lab
- Configure Virtual Environment using Virtualization or a VPN
- Create VMs for:
  - Kali Linux (C2)
  - Debian/Ubuntu (Linux bots)
  - Windows VM (optional Windows bot)
  - Ubuntu server (target)

Make sure all virtual machines are on the same local area network (LAN).

### 2. On kali Linux (C2)
```bash
git clone https://github.com/buggymaytricks/ECSIP-botnet-sim-and-analysis.git
cd ECSIP-botnet-sim-and-analysis
cd c2_server
pip3 install -r requirements.txt
python3 server.py
```

Now you can send the binaries on the desired VMs

### 3. On Windows Bot
```
Run the bot.exe file
#It will ask for the servers IP enter the IP and hit enter
```

### 4. On Linux Bot
```bash
./bot
#It will ask for the servers IP enter the IP and hit enter
```

### 5. Use C2 Dashboard
- Access dashboard via browser (`http://<C2-IP>:5000`)
- View connected bots, run modules and monitor responses

### 6. Analyze Traffic (Wireshark) IN PROGRESS
- Filter packets by IP or protocol:
  - `http.request`
  - `ip.addr == <bot-ip>`
- Observe command traffic and DDoS flood patterns

---
## 📸 Screenshots
<p align="center">
  <img src="https://drive.google.com/uc?export=view&id=1bknS9FmQbVhIeekbxAMuIQnWVjK0pSih" width="200"/>
  <img src="https://drive.google.com/uc?export=view&id=1I5RtTPza4Cp6XEOOO8RUnfY68FF0dvGZ" width="200"/>
  <img src="https://drive.google.com/uc?export=view&id=1LHzVpx3VslSSypq079y0wGhzuSE4Utmt" width="200"/>
  <img src="https://drive.google.com/uc?export=view&id=1tUHEIjn0Whsn-kE1ZWzXNMs47Obaye_j" width="200"/>
</p>

---

## ⚠️ Known Limitations

- Communication not encrypted (no HTTPS)
- Static polling interval (no randomized beaconing)
- No real propagation

---

## 🧠 Future Work (Optional Improvements)

- Implement AES encryption for bot-C2 traffic
- Build a graphical dashboard with real-time bot telemetry
- Add ML-based traffic anomaly detection
- Simulate DNS or covert-channel based communication

---

## 📜 License / Ethics

This simulation is intended **only for ethical learning and cybersecurity education.**
All components were run on internal, offline VMs. Do not deploy in real or online environments.
