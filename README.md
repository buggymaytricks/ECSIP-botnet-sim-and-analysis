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
- Explore malware modules (keylogger, scanner, DDoS)
- Monitor traffic using Wireshark
- Ensure complete ethical containment in a virtual lab

---

## 🛠 Tech Stack

| Component       | Technology              |
|----------------|--------------------------|
| Bots           | Python (requests, subprocess) |
| C2 Server      | Flask + SQLite           |
| Target Server  | Ubuntu + Flask           |
| Persistence    | Cronjobs (Linux), Startup folder (Windows) |
| Monitoring     | Wireshark                |
| VMs            | VirtualBox (host-only)   |

---

## 📁 Project Structure

```
modular-botnet-simulation/
├── bots/                # Linux and Windows bot clients
│   ├── linux_bot/
│   └── windows_bot/
├── c2_dashboard/        # Flask-based C2 interface
├── target_server/       # Flask server to simulate DDoS attack
├── analysis/            # Wireshark logs, screenshots
├── docs/                # Scope, Report, Presentation (PDF)
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run

### 1. Set Up the Virtual Lab
- Configure host-only network in VirtualBox
- Create VMs for:
  - Kali Linux (C2)
  - Debian/Ubuntu (Linux bots)
  - Windows VM (optional Windows bot)
  - Ubuntu server (target)

### 2. Start the C2 Server
```bash
cd c2_dashboard
python3 app.py
```

### 3. Launch Bot Clients
```bash
cd bots/linux_bot
python3 main.py
```
(Repeat on each bot VM)

### 4. Use C2 Dashboard
- Access dashboard via browser (`http://<C2-IP>:5000`)
- View connected bots, send commands, and monitor responses

### 5. Analyze Traffic (Wireshark)
- Filter packets by IP or protocol:
  - `http.request`
  - `ip.addr == <bot-ip>`
- Observe command traffic and DDoS flood patterns

---

## 🔍 Implemented Modules

- `keylogger`: Captures keystrokes (Linux only)
- `ddos`: HTTP flood on target server
- `scan_ports`: Scans common ports on target
- `brute_force` (optional): SSH credential attempts
- `info`: System/user information collection

---

## 📸 Screenshots (Add these)

- C2 Dashboard interface with bots listed
- Terminal output from bots (e.g., `whoami`, `uname`)
- Wireshark HTTP polling traffic
- Target server logs during simulated attack

---

## ⚠️ Known Limitations

- Communication not encrypted (no HTTPS)
- Limited Windows testing (AV interference)
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
