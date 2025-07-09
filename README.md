# 🕷️ Modular Botnet Simulation in a Virtual Lab

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
| Target Server  | Ubuntu + HTML           |
| Monitoring     | Wireshark                |
| VMs            | VirtualBox/VMWare (host-only)   |

---

## 📁 Project Structure

```
modular-botnet-simulation/
├── bot/                # Linux and Windows bot clients
│   ├── bot.py
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

## 🚀 How to Run

### 1. Set Up the Virtual Lab
- Configure host-only network in Virtual Environment
- Create VMs for:
  - Kali Linux (C2)
  - Debian/Ubuntu (Linux bots)
  - Windows VM (optional Windows bot)
  - Ubuntu server (target)

## 2. On kali
```bash
git clone https://github.com/buggymaytricks/ECSIP-botnet-sim-and-analysis.git
cd ECSIP-botnet-sim-and-analysis
cd c2_server
pip3 install requirements.txt
python3 server.py
# In other terminal
nano bot/bot.py
# Edit the C2_URL and change the ip to your servers ip

```

### 2. On Windows Bot
```bash
git clone https://github.com/buggymaytricks/ECSIP-botnet-sim-and-analysis.git
cd ECSIP-botnet-sim-and-analysis

python3 server.py
```

### 3. Launch Bot Clients
```bash
cd bot/
python3 bot.py
```
(Repeat on each bot VM)

### 4. Use C2 Dashboard
- Access dashboard via browser (`http://<C2-IP>:5000`)
- View connected bots, send commands, run modules and monitor responses

### 5. Analyze Traffic (Wireshark) IN PROGRESS
- Filter packets by IP or protocol:
  - `http.request`
  - `ip.addr == <bot-ip>`
- Observe command traffic and DDoS flood patterns

---

## 🔍 Implemented Modules

- `Keylogger`: Captures keystrokes
- `DoS`: HTTP flood on target server
- `net_scan`: Scans the network in which the bot is connected and sends the hosts that are up. (Not accurate)
- `port_scan`: Scans common ports on hosts that are up
- `brute_force`: Can perform bruteforce operations on SSH/FTP/HTTP
- `stealer`: Steals known credentials from Linux-(Fails to steal browser creds), on Windows only steals browser creds only for chromium based browserss
- `spyware`: Gets clipboard as well as captures screenshots

---

## 📸 Screenshots (Add these) IN PROGRESS

- C2 Dashboard interface with bots listed
- Terminal output from bots (e.g., `whoami`, `uname`)
- Wireshark HTTP polling traffic
- Target server logs during simulated attack

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
