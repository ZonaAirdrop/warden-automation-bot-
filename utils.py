from datetime import datetime
import os
from colorama import Fore, Style
import platform
import random # Pastikan ini ada

def clear_console():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def log_message(message):
    current_time = datetime.now().strftime('%H:%M:%S') # Format baru: HH:MM:SS
    print(f"{Fore.BLUE}[{current_time}]{Style.RESET_ALL} {message}")

def format_time_duration(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{int(hours):02}:{int(minutes):02}:{int(secs):02}"

def load_json_data(filename):
    try:
        import json # Pindahkan import json ke sini jika belum ada di file utils.py Anda
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{Fore.RED}Error: {filename} not found.{Style.RESET_ALL}")
        return None
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error: Invalid JSON in {filename}.{Style.RESET_ALL}")
        return None

def get_masked_address(key_entry: str):
    from eth_account import Account # Pindahkan import Account ke sini jika belum ada di file utils.py Anda
    try:
        # Asumsi key_entry adalah private key heksadesimal 64 karakter
        account = Account.from_key(key_entry)
        wallet_address = account.address
        return wallet_address, f"{wallet_address[:6]}...{wallet_address[-4:]}"
    except Exception:
        # Jika bukan private key yang valid, tampilkan sebagian dari string aslinya
        return None, f"{key_entry[:6]}...{key_entry[-4:]}" if len(key_entry) >= 10 else "Invalid Key"

def check_proxy_format(proxy_url: str):
    if not (proxy_url.startswith("http://") or proxy_url.startswith("https://") or proxy_url.startswith("socks5://")):
        raise ValueError("Invalid proxy format. Must start with http://, https://, or socks5://")
    return proxy_url

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/108.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/108.0",
    ]
    return random.choice(user_agents)