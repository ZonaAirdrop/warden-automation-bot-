from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout
)
from aiohttp_socks import ProxyConnector
from eth_account.messages import encode_defunct
from eth_utils import to_hex
from eth_account import Account
from datetime import datetime, timezone
from colorama import *
import asyncio, uuid, json, os
import time
import random

from utils import (
    clear_console,
    log_message,
    format_time_duration,
    load_json_data,
    get_masked_address,
    check_proxy_format,
    get_random_user_agent
)

class WardenAutomation:
    def __init__(self) -> None:
        self.PRIVY_API_ENDPOINT = "https://auth.privy.io"
        self.CORE_API_ENDPOINT = "https://api.app.wardenprotocol.org/api"
        self.AI_AGENTS_API_ENDPOINT = "https://warden-app-agents-prod-new-d1025b697dc25df9a5654bc047bbe875.us.langgraph.app"
        
        self.privy_headers_map = {}
        self.core_headers_map = {}
        self.agents_headers_map = {}
        
        self.proxy_list = []
        self.current_proxy_index = 0
        self.account_proxy_assignments = {} # Menyimpan proxy yang ditugaskan per akun
        self.auth_tokens = {}
        
        self.use_private_proxy = False
        self.should_rotate_proxies = False
        self.initial_proxy_assignment_done = False # Bendera untuk menandai penugasan proxy awal

    def display_welcome_screen(self):
        clear_console()
        now = datetime.now()
        date_str = now.strftime('%d.%m.%y')
        time_str = now.strftime('%H:%M:%S')
        
        print(f"{Fore.GREEN + Style.BRIGHT}")
        print("  ┌─────────────────────────────────┐")
        print("  │    [ W A R D E N  B O T ]     │")
        print(f"  │                                 │")
        print(f"  │    {Fore.YELLOW}{time_str} {date_str}{Fore.GREEN}      │")
        print(f"  │                                 │")
        print("  │   Automated Protocol Utility    │")
        print(f"  │ {Fore.WHITE}   by ZonaAirdrop {Fore.GREEN}(@ZonaAirdr0p){Style.RESET_ALL} │")
        print("  └─────────────────────────────────┘\n")
        time.sleep(1)

    async def load_proxies_from_file(self):
        filename = "proxy.txt"
        try:
            if not os.path.exists(filename):
                log_message(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                return
            with open(filename, 'r') as f:
                self.proxy_list = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxy_list:
                log_message(f"{Fore.RED + Style.BRIGHT}No Proxies Found. Running without proxy.{Style.RESET_ALL}")
                return

            log_message(
                f"{Fore.YELLOW + Style.BRIGHT}Loaded Proxies: {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxy_list)}{Style.RESET_ALL}"
            )
            
        except Exception as e:
            log_message(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxy_list = []

    def get_assigned_proxy(self, account_address):
        """Mendapatkan proxy yang sudah ditugaskan untuk akun tertentu."""
        return self.account_proxy_assignments.get(account_address)

    def assign_initial_proxy(self, account_address):
        """Menugaskan proxy awal untuk akun jika belum ada."""
        if not self.use_private_proxy or not self.proxy_list:
            return None # Tidak menggunakan proxy atau tidak ada proxy
        
        if account_address not in self.account_proxy_assignments:
            if not self.proxy_list: # Periksa lagi jika list proxy kosong setelah pilihan
                return None

            proxy_url = check_proxy_format(self.proxy_list[self.current_proxy_index])
            self.account_proxy_assignments[account_address] = proxy_url
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
            log_message(f"{Fore.WHITE}Assigned initial proxy {Fore.YELLOW}{proxy_url}{Fore.WHITE} to account {get_masked_address(account_address)[1]}{Style.RESET_ALL}")
        
        return self.account_proxy_assignments[account_address]


    def rotate_assigned_proxy(self, account_address):
        """Merotasi proxy yang ditugaskan untuk akun tertentu."""
        if not self.use_private_proxy or not self.proxy_list:
            return None
        
        # Dapatkan indeks proxy berikutnya
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        new_proxy_url = check_proxy_format(self.proxy_list[self.current_proxy_index])
        self.account_proxy_assignments[account_address] = new_proxy_url # Assign proxy baru
        log_message(f"{Fore.YELLOW}Rotated proxy for {get_masked_address(account_address)[1]} to {new_proxy_url}{Style.RESET_ALL}")
        return new_proxy_url
        
    def generate_siwe_payload(self, eth_account_key: str, wallet_address: str, nonce_value: str):
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            message = f"app.wardenprotocol.org wants you to sign in with your Ethereum account:\n{wallet_address}\n\nBy signing, you are proving you own this wallet and logging in. This does not initiate a transaction or cost any fees.\n\nURI: https://app.wardenprotocol.org\nVersion: 1\nChain ID: 1\nNonce: {nonce_value}\nIssued At: {timestamp}\nResources:\n- https://privy.io"
            encoded_message = encode_defunct(text=message)
            signed_message = Account.sign_message(encoded_message, private_key=eth_account_key)
            signature = to_hex(signed_message.signature)

            payload = {
                "message":message,
                "signature":signature,
                "chainId":"eip155:1",
                "walletClientType":"metamask",
                "connectorType":"injected",
                "mode":"login-or-sign-up"
            }

            return payload
        except Exception as e:
            raise Exception(f"Failed to generate authentication payload: {str(e)}")

    def generate_chat_stream_payload(self, user_message: str):
        try:
            payload = {
                "input":{
                    "messages":[{
                        "id":str(uuid.uuid4()),
                        "type":"human",
                        "content":user_message
                    }]
                },
                "metadata":{
                    "addresses":[]
                },
                "stream_mode":[
                    "values",
                    "messages-tuple",
                    "custom"
                ],
                "stream_resumable":True,
                "assistant_id":"agent",
                "on_disconnect":"continue"
            }

            return payload
        except Exception as e:
            return None
            
    def get_user_choice_for_proxy(self):
        while True:
            try:
                log_message(f"{Fore.CYAN + Style.BRIGHT}─" * 40)
                log_message(f"{Fore.WHITE}[1]{Fore.CYAN} Run with Private Proxy")
                log_message(f"{Fore.WHITE}[2]{Fore.CYAN} Run without Proxy")
                log_message(f"{Fore.CYAN + Style.BRIGHT}─" * 40)
                choice_input = int(input(f"{Fore.GREEN + Style.BRIGHT}Choose an option (1 or 2): {Style.RESET_ALL}").strip())

                if choice_input in [1, 2]:
                    proxy_type_display = (
                        "Private Proxy" if choice_input == 1 else 
                        "No Proxy"
                    )
                    log_message(f"{Fore.GREEN + Style.BRIGHT}Mode selected: {proxy_type_display}{Style.RESET_ALL}")
                    break
                else:
                    log_message(f"{Fore.RED + Style.BRIGHT}Invalid input. Please enter 1 or 2.{Style.RESET_ALL}")
            except ValueError:
                log_message(f"{Fore.RED + Style.BRIGHT}Invalid input. Please enter a number (1 or 2).{Style.RESET_ALL}")

        should_rotate = False
        if choice_input == 1:
            while True:
                rotate_input_str = input(f"{Fore.GREEN + Style.BRIGHT}Rotate Invalid Proxy? (y/n): {Style.RESET_ALL}").strip().lower()

                if rotate_input_str in ["y", "n"]:
                    should_rotate = (rotate_input_str == "y")
                    break
                else:
                    log_message(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter 'y' or 'n'.{Style.RESET_ALL}")
        
        self.use_private_proxy = (choice_input == 1)
        self.should_rotate_proxies = should_rotate

        return self.use_private_proxy, self.should_rotate_proxies
        
    async def verify_connection(self, proxy_addr=None):
        connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(url="https://api.ipify.org?format=json", ssl=False) as response:
                    response.raise_for_status()
                    # log_message(f"{Fore.GREEN}Connection Status: Success! (IP: {(await response.json()).get('ip')}){Style.RESET_ALL}")
                    return True
        except (Exception, ClientResponseError) as e:
            log_message(
                f"{Fore.RED}Connection Status: Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
            )
            return None
            
    async def make_request(self, method, url, wallet_address, headers, data=None, retries=5, is_privy_auth=False):
        """Fungsi pembantu untuk menangani permintaan HTTP dengan retry, proxy, dan deteksi 429/CAPTCHA."""
        
        for attempt in range(retries):
            current_proxy = self.get_assigned_proxy(wallet_address) if self.use_private_proxy else None
            display_proxy_info = current_proxy if current_proxy else "None (Direct)"
            log_message(f"{Fore.WHITE}Attempt {attempt + 1}/{retries} to {url.split('/')[2]} using Proxy: {Fore.YELLOW}{display_proxy_info}{Style.RESET_ALL}")

            # Penundaan acak yang lebih agresif
            sleep_time = random.randint(30, 90) if is_privy_auth else random.randint(15, 45)
            log_message(f"{Fore.CYAN}Waiting {sleep_time} seconds before request...{Style.RESET_ALL}")
            await asyncio.sleep(sleep_time)

            connector = ProxyConnector.from_url(current_proxy) if current_proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=90)) as session: # Timeout lebih panjang
                    if method == "POST":
                        async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                            return await self._handle_response(response, wallet_address, url, is_privy_auth)
                    else: # GET
                        async with session.get(url=url, headers=headers, ssl=False) as response:
                            return await self._handle_response(response, wallet_address, url, is_privy_auth)
            except ClientResponseError as e:
                log_message(f"{Fore.RED}Request to {url.split('/')[2]} Failed {Style.RESET_ALL}({Fore.YELLOW}Status: {e.status}, Message: {str(e)}{Style.RESET_ALL})")
                if self.should_rotate_proxies and self.use_private_proxy and self.proxy_list:
                    log_message(f"{Fore.YELLOW}Rotating proxy after error...{Style.RESET_ALL}")
                    self.rotate_assigned_proxy(wallet_address)
                await asyncio.sleep(random.randint(20, 60)) # Jeda lebih lama setelah error umum
                continue
            except Exception as e:
                log_message(f"{Fore.RED}Request to {url.split('/')[2]} Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})")
                if self.should_rotate_proxies and self.use_private_proxy and self.proxy_list:
                    log_message(f"{Fore.YELLOW}Rotating proxy after error...{Style.RESET_ALL}")
                    self.rotate_assigned_proxy(wallet_address)
                await asyncio.sleep(random.randint(20, 60)) # Jeda lebih lama setelah error umum
                continue

        log_message(f"{Fore.RED}Failed to complete request to {url.split('/')[2]} after {retries} attempts. Skipping account/activity.{Style.RESET_ALL}")
        return None

    async def _handle_response(self, response, wallet_address, url, is_privy_auth):
        """Menangani respons HTTP, termasuk deteksi 429 dan CAPTCHA."""
        if response.status == 429:
            log_message(f"{Fore.YELLOW}{url.split('/')[2]}: Too Many Requests (429) detected. Rotating proxy...{Style.RESET_ALL}")
            if self.should_rotate_proxies and self.use_private_proxy and self.proxy_list:
                self.rotate_assigned_proxy(wallet_address)
            raise ClientResponseError(request_info=response.request_info, history=response.history, status=429) # Re-raise untuk memicu retry loop

        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            html_content = await response.text()
            if "Checking that you are a human..." in html_content or "captcha" in html_content.lower():
                log_message(f"{Fore.RED}CAPTCHA detected for {url.split('/')[2]}! Manual intervention or CAPTCHA solving service needed. Skipping account/activity.{Style.RESET_ALL}")
                # Anda bisa menambahkan logika untuk memanggil layanan pemecah CAPTCHA di sini
                return None # Gagal untuk akun/aktivitas ini

        response.raise_for_status()
        return await response.json() if 'application/json' in content_type else await response.text()

    async def request_privy_nonce(self, wallet_address: str):
        url = f"{self.PRIVY_API_ENDPOINT}/api/v1/siwe/init"
        data = json.dumps({"address":wallet_address})
        
        headers = {
            "Accept": "application/json",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.wardenprotocol.org",
            "Privy-App-Id": "cm7f00k5c02tibel0m4o9tdy1",
            "Privy-Ca-Id": str(uuid.uuid4()),
            "Privy-Client": "react-auth:2.13.8",
            "Referer": "https://app.wardenprotocol.org/", 
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Storage-Access": "active",
            "User-Agent": get_random_user_agent(),
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        
        return await self.make_request("POST", url, wallet_address, headers, data=data, is_privy_auth=True)
            
    async def authenticate_with_privy(self, eth_account_key: str, wallet_address: str, nonce_value: str):
        url = f"{self.PRIVY_API_ENDPOINT}/api/v1/siwe/authenticate"
        payload = self.generate_siwe_payload(eth_account_key, wallet_address, nonce_value)
        if payload is None:
            log_message(f"{Fore.RED}Failed to generate SIWE payload.{Style.RESET_ALL}")
            return None
        data = json.dumps(payload)
        
        headers = {
            "Accept": "application/json",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.wardenprotocol.org",
            "Privy-App-Id": "cm7f00k5c02tibel0m4o9tdy1",
            "Privy-Ca-Id": str(uuid.uuid4()),
            "Privy-Client": "react-auth:2.13.8",
            "Referer": "https://app.wardenprotocol.org/", 
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Storage-Access": "active",
            "User-Agent": get_random_user_agent(),
            "Content-Type": "application/json",
            "Content-Length": str(len(data))
        }
        
        return await self.make_request("POST", url, wallet_address, headers, data=data, is_privy_auth=True)
            
    async def fetch_user_token_data(self, wallet_address: str):
        url = f"{self.CORE_API_ENDPOINT}/tokens/user/me"
        
        headers = {
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.wardenprotocol.org",
            "Referer": "https://app.wardenprotocol.org/", 
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": get_random_user_agent(),
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}"
        }
        
        return await self.make_request("GET", url, wallet_address, headers)
            
    async def submit_checkin_activity(self, wallet_address: str):
        url = f"{self.CORE_API_ENDPOINT}/tokens/activity"
        data = json.dumps({
            "activityType":"LOGIN",
            "metadata":{
                "action":"user_login",
                "timestamp":datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            }
        })
        
        headers = {
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.wardenprotocol.org",
            "Referer": "https://app.wardenprotocol.org/", 
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": get_random_user_agent(),
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        
        return await self.make_request("POST", url, wallet_address, headers, data=data)
            
    async def submit_game_activity(self, wallet_address: str):
        url = f"{self.CORE_API_ENDPOINT}/tokens/activity"
        data = json.dumps({
            "activityType":"GAME_PLAY",
            "metadata":{
                "action":"user_game",
                "timestamp":datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            }
        })
        
        headers = {
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.wardenprotocol.org",
            "Referer": "https://app.wardenprotocol.org/", 
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": get_random_user_agent(),
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        
        return await self.make_request("POST", url, wallet_address, headers, data=data)
            
    async def initialize_agent_thread(self, wallet_address: str):
        url = f"{self.AI_AGENTS_API_ENDPOINT}/threads"
        data = json.dumps({"metadata":{}})
        
        headers = {
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.wardenprotocol.org",
            "Referer": "https://app.wardenprotocol.org/", 
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": get_random_user_agent(),
            "X-Api-Key": "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",
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        
        return await self.make_request("POST", url, wallet_address, headers, data=data)

    async def execute_agent_stream(self, wallet_address: str, thread_id: str, message_content: str):
        url = f"{self.AI_AGENTS_API_ENDPOINT}/threads/{thread_id}/runs/stream"
        data = json.dumps(self.generate_chat_stream_payload(message_content))
        
        headers = {
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.wardenprotocol.org",
            "Referer": "https://app.wardenprotocol.org/", 
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": get_random_user_agent(),
            "X-Api-Key": "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",
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }

        # Menggunakan make_request untuk stream memerlukan sedikit penyesuaian karena _handle_response
        # akan mengasumsikan respons JSON atau teks penuh, bukan stream.
        # Kita akan tetap menggunakan make_request untuk logic retry/proxy, tapi custom handle response
        current_proxy = self.get_assigned_proxy(wallet_address) if self.use_private_proxy else None
        display_proxy_info = current_proxy if current_proxy else "None (Direct)"
        
        for attempt in range(5): # Menggunakan retries default dari make_request
            log_message(f"{Fore.WHITE}Attempt {attempt + 1}/5 for AI Chat Response using Proxy: {Fore.YELLOW}{display_proxy_info}{Style.RESET_ALL}")
            sleep_time = random.randint(15, 45) # Jeda lebih lama untuk AI chat
            log_message(f"{Fore.CYAN}Waiting {sleep_time} seconds before AI chat response request...{Style.RESET_ALL}")
            await asyncio.sleep(sleep_time)

            connector = ProxyConnector.from_url(current_proxy) if current_proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=120)) as session: # Timeout lebih panjang untuk stream
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        if response.status == 429:
                            log_message(f"{Fore.YELLOW}AI Chat Response: Too Many Requests (429) detected. Rotating proxy...{Style.RESET_ALL}")
                            if self.should_rotate_proxies and self.use_private_proxy and self.proxy_list:
                                self.rotate_assigned_proxy(wallet_address)
                            await asyncio.sleep(random.randint(60, 180)) # Jeda sangat lama setelah 429 pada stream
                            continue
                        
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type:
                            html_content = await response.text()
                            if "Checking that you are a human..." in html_content or "captcha" in html_content.lower():
                                log_message(f"{Fore.RED}CAPTCHA detected for AI Chat Response! Manual intervention or CAPTCHA solving service needed. Skipping account.{Style.RESET_ALL}")
                                return None

                        response.raise_for_status()
                        result_content = ""
                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if not line or line.startswith(":"):
                                continue
                            if line.startswith("data: "):
                                try:
                                    json_data = json.loads(line[6:])
                                    messages = json_data.get("messages", [])
                                    for msg in messages:
                                        if msg.get("type") == "ai":
                                            result_content += msg.get("content", "")
                                except json.JSONDecodeError:
                                    continue
                        return result_content if result_content else None
            except ClientResponseError as e:
                log_message(f"{Fore.YELLOW}[AI Chat Response]: {Fore.RED}Failed {Style.RESET_ALL}({Fore.YELLOW}Status: {e.status}, Message: {str(e)}{Style.RESET_ALL})")
                if self.should_rotate_proxies and self.use_private_proxy and self.proxy_list:
                    self.rotate_assigned_proxy(wallet_address)
                await asyncio.sleep(random.randint(30, 90))
                continue
            except Exception as e:
                log_message(f"{Fore.YELLOW}[AI Chat Response]: {Fore.RED}Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})")
                if self.should_rotate_proxies and self.use_private_proxy and self.proxy_list:
                    self.rotate_assigned_proxy(wallet_address)
                await asyncio.sleep(random.randint(30, 90))
                continue
        return None
            
    async def submit_chat_activity(self, wallet_address: str, message_length: int):
        url = f"{self.CORE_API_ENDPOINT}/tokens/activity"
        data = json.dumps({
            "activityType":"CHAT_INTERACTION",
            "metadata":{
                "action":"user_chat",
                "message_length":message_length,
                "timestamp":datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            }
        })
        
        headers = {
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://app.wardenprotocol.org",
            "Referer": "https://app.wardenprotocol.org/", 
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": get_random_user_agent(),
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        
        return await self.make_request("POST", url, wallet_address, headers, data=data)
                
    async def handle_proxy_check(self, account_address: str):
        # Pastikan proxy sudah ditugaskan sebelum memeriksa koneksi
        self.assign_initial_proxy(account_address) 

        while True:
            active_proxy = self.get_assigned_proxy(account_address)
            display_proxy_info = active_proxy if active_proxy else "None (Direct)"
            log_message(
                f"{Fore.WHITE}Proxy Used: {Fore.YELLOW}{display_proxy_info}{Style.RESET_ALL}"
            )

            if active_proxy: # Hanya cek koneksi jika ada proxy yang ditugaskan
                is_proxy_valid = await self.verify_connection(active_proxy)
                if not is_proxy_valid:
                    if self.should_rotate_proxies and self.use_private_proxy and self.proxy_list:
                        log_message(f"{Fore.YELLOW}Proxy {active_proxy} is invalid. Rotating proxy for {get_masked_address(account_address)[1]}...{Style.RESET_ALL}")
                        self.rotate_assigned_proxy(account_address)
                        await asyncio.sleep(5) # Jeda singkat setelah rotasi
                        continue # Coba lagi dengan proxy baru
                    else:
                        log_message(f"{Fore.RED}Proxy {active_proxy} is invalid and rotation is disabled or no more proxies. Proceeding without proxy or skipping.{Style.RESET_ALL}")
                        self.use_private_proxy = False # Matikan penggunaan proxy jika ada masalah
                        return True # Lanjutkan tanpa proxy
                else:
                    return True # Proxy valid
            else: # Tidak ada proxy yang digunakan
                log_message(f"{Fore.YELLOW}No proxy configured or available. Proceeding without proxy.{Style.RESET_ALL}")
                return True # Lanjutkan tanpa proxy

    async def perform_user_login(self, private_key: str, wallet_address: str):
        # handle_proxy_check akan memastikan proxy ditugaskan/diperiksa
        is_connected = await self.handle_proxy_check(wallet_address)
        if not is_connected:
            log_message(f"{Fore.RED}Could not establish a working connection for {get_masked_address(wallet_address)[1]}. Skipping login.{Style.RESET_ALL}")
            return False

        nonce_response = await self.request_privy_nonce(wallet_address)
        if nonce_response and "nonce" in nonce_response:
            retrieved_nonce = nonce_response["nonce"]

            login_response = await self.authenticate_with_privy(private_key, wallet_address, retrieved_nonce)
            if login_response and "token" in login_response:
                self.auth_tokens[wallet_address] = login_response["token"]
                log_message(f"{Fore.GREEN}Login Status: Success!{Style.RESET_ALL}")
                return True
            else:
                log_message(f"{Fore.RED}Login failed for {get_masked_address(wallet_address)[1]}. No token received.{Style.RESET_ALL}")
        else:
            log_message(f"{Fore.RED}Failed to retrieve nonce for {get_masked_address(wallet_address)[1]}. Skipping login.{Style.RESET_ALL}")
        return False

    async def process_wallet_activities(self, private_key: str, wallet_address: str, chat_questions: list):
        login_successful = await self.perform_user_login(private_key, wallet_address)
        if not login_successful:
            log_message(f"{Fore.RED}Skipping activities for {get_masked_address(wallet_address)[1]} due to login failure.{Style.RESET_ALL}")
            return

        user_data = await self.fetch_user_token_data(wallet_address)
        if user_data:
            current_balance = user_data.get("token", {}).get("pointsTotal", 0)
            log_message(f"{Fore.WHITE}Current Balance: {Fore.YELLOW}{current_balance} PUMPs{Style.RESET_ALL}")
        else:
            log_message(f"{Fore.YELLOW}Could not fetch user token data for {get_masked_address(wallet_address)[1]}.{Style.RESET_ALL}")

        checkin_result = await self.submit_checkin_activity(wallet_address)
        if checkin_result:
            activity_id_checkin = checkin_result.get("activityId", None)
            if activity_id_checkin:
                log_message(f"{Fore.GREEN}Daily Check-In: Activity Recorded.{Style.RESET_ALL}")
            else:
                message_checkin = checkin_result.get("message", "Unknown Status")
                log_message(f"{Fore.YELLOW}Daily Check-In: {message_checkin}{Style.RESET_ALL}")
        else:
            log_message(f"{Fore.RED}Failed to submit Daily Check-In for {get_masked_address(wallet_address)[1]}.{Style.RESET_ALL}")

        game_result = await self.submit_game_activity(wallet_address)
        if game_result:
            activity_id_game = game_result.get("activityId", None)
            if activity_id_game:
                log_message(f"{Fore.GREEN}Game Play: Activity Recorded.{Style.RESET_ALL}")
            else:
                message_game = game_result.get("message", "Unknown Status")
                log_message(f"{Fore.YELLOW}Game Play: {message_game}{Style.RESET_ALL}")
        else:
            log_message(f"{Fore.RED}Failed to submit Game Play activity for {get_masked_address(wallet_address)[1]}.{Style.RESET_ALL}")

        log_message(f"{Fore.CYAN}Initiating AI Chat...{Style.RESET_ALL}")
        ai_chat_completed = False
        for i in range(3): # Coba 3 kali untuk AI chat
            log_message(f"{Fore.CYAN}AI Chat attempt {i+1}/3 for {get_masked_address(wallet_address)[1]}...{Style.RESET_ALL}")
            thread_info = await self.initialize_agent_thread(wallet_address)
            if thread_info and "thread_id" in thread_info:
                thread_identifier = thread_info["thread_id"]
                chosen_message = random.choice(chat_questions)
                message_len = len(chosen_message)

                log_message(f"{Fore.BLUE}  [Q]: {Fore.WHITE}{chosen_message}{Style.RESET_ALL}")

                chat_response = await self.execute_agent_stream(wallet_address, thread_identifier, chosen_message)
                if chat_response:
                    log_message(f"{Fore.MAGENTA}  [A]: {Fore.WHITE}{chat_response[:100]}...{Style.RESET_ALL}") # Tampilkan sebagian respons

                    submit_chat_result = await self.submit_chat_activity(wallet_address, message_len)
                    if submit_chat_result:
                        activity_id_chat = submit_chat_result.get("activityId", None)
                        if activity_id_chat:
                            log_message(f"{Fore.GREEN}  Chat Activity: Sent Successfully.{Style.RESET_ALL}")
                            ai_chat_completed = True
                            break # Berhasil, keluar dari loop chat retry
                        else:
                            message_chat = submit_chat_result.get("message", "Unknown Status")
                            log_message(f"{Fore.YELLOW}  Chat Activity: {message_chat}{Style.RESET_ALL}")
                    else:
                        log_message(f"{Fore.RED}  Failed to submit Chat Activity for {get_masked_address(wallet_address)[1]}.{Style.RESET_ALL}")
                else:
                    log_message(f"{Fore.RED}  Failed to get AI Chat response for {get_masked_address(wallet_address)[1]}.{Style.RESET_ALL}")
            else:
                log_message(f"{Fore.RED}  Failed to initialize AI Agent thread for {get_masked_address(wallet_address)[1]}.{Style.RESET_ALL}")
            
            if not ai_chat_completed and i < 2: # Jangan jeda setelah percobaan terakhir jika gagal
                log_message(f"{Fore.YELLOW}  Retrying AI Chat for {get_masked_address(wallet_address)[1]}...{Style.RESET_ALL}")
                await asyncio.sleep(random.randint(20, 60)) # Jeda lebih lama sebelum retry AI chat
        
        if not ai_chat_completed:
            log_message(f"{Fore.RED}Failed to complete AI Chat activity after multiple attempts for {get_masked_address(wallet_address)[1]}.{Style.RESET_ALL}")
                        
    async def run_bot_main_loop(self):
        init(autoreset=True)

        try:
            with open('accounts.txt', 'r') as file:
                account_keys = [line.strip() for line in file if line.strip()]
            
            self.display_welcome_screen()
            
            self.use_private_proxy, self.should_rotate_proxies = self.get_user_choice_for_proxy()

            chat_questions_list = load_json_data("question_lists.json")
            if not chat_questions_list:
                log_message(f"{Fore.RED}No Questions Loaded. Please check 'question_lists.json'.{Style.RESET_ALL}")
                return

            if self.use_private_proxy:
                await self.load_proxies_from_file()
                if not self.proxy_list:
                    log_message(f"{Fore.YELLOW}Warning: Private proxy selected, but no proxies found in proxy.txt. Running without proxy.{Style.RESET_ALL}")
                    self.use_private_proxy = False

            while True:
                self.display_welcome_screen()
                log_message(f"{Fore.WHITE}Total Accounts: {Fore.CYAN}{len(account_keys)}{Style.RESET_ALL}")
                log_message(f"{Fore.WHITE}Proxy Rotation: {Fore.CYAN}{'Enabled' if self.should_rotate_proxies and self.use_private_proxy else 'Disabled'}{Style.RESET_ALL}\n")

                for key_entry in account_keys:
                    if key_entry:
                        try:
                            wallet_address, masked_address = get_masked_address(key_entry)
                            
                            log_message(f"{Fore.BLUE}=== Processing Account [{masked_address}] ==={Style.RESET_ALL}")

                            if not wallet_address:
                                log_message(f"{Fore.RED}Status: Invalid Private Key or Library Version Not Supported.{Style.RESET_ALL}")
                                log_message(f"{Fore.BLUE}======================================={Style.RESET_ALL}\n")
                                continue

                            # Pastikan setiap akun memiliki proxy yang ditugaskan di awal setiap siklus
                            if self.use_private_proxy:
                                self.assign_initial_proxy(wallet_address)

                            await self.process_wallet_activities(key_entry, wallet_address, chat_questions_list)
                            log_message(f"{Fore.BLUE}=== Account Processing Finished ==={Style.RESET_ALL}\n")
                            await asyncio.sleep(random.randint(10, 30)) # Jeda acak antar akun (lebih lama)
                        except Exception as e:
                            log_message(f"{Fore.RED}Error processing account {get_masked_address(key_entry)[1]}: {e}{Style.RESET_ALL}")
                            await asyncio.sleep(random.randint(5, 15)) # Jeda singkat setelah error akun

                log_message(f"{Fore.GREEN}All accounts processed. Entering cooldown phase...{Style.RESET_ALL}")
                cooldown_seconds = 24 * 60 * 60 # 24 jam
                while cooldown_seconds > 0:
                    formatted_cooldown = format_time_duration(cooldown_seconds)
                    print(
                        f"{Fore.CYAN}Next cycle in: {Fore.YELLOW}[{formatted_cooldown}]{Style.RESET_ALL}"
                        f"{Fore.WHITE} | {Fore.BLUE}Press CTRL+C to quit.{Style.RESET_ALL}",
                        end="\r"
                    )
                    await asyncio.sleep(1)
                    cooldown_seconds -= 1
                log_message(f"\n{Fore.GREEN}Initiating next processing cycle...{Style.RESET_ALL}")

        except FileNotFoundError:
            log_message(f"{Fore.RED}Error: 'accounts.txt' file not found. Please create the file and add your private keys.{Style.RESET_ALL}")
        except KeyboardInterrupt:
            log_message(f"\n{Fore.YELLOW}Bot stopped by user.{Style.RESET_ALL}")
        except Exception as e:
            log_message(f"{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")

# Contoh cara menjalankan bot (jika ini adalah file utama Anda)
# if __name__ == "__main__":
#     bot = WardenAutomation()
#     asyncio.run(bot.run_bot_main_loop())
