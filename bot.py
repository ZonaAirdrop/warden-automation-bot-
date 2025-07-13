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
        self.account_proxy_assignments = {}
        self.auth_tokens = {}

    def display_welcome_screen(self):
        clear_console()
        now = datetime.now()
        date_str = now.strftime('%d.%m.%y')
        time_str = now.strftime('%H:%M:%S')
        
        print(f"{Fore.GREEN + Style.BRIGHT}")
        print("  ┌─────────────────────────────────┐")
        print("  │     [ W A R D E N  B O T ]      │")
        print(f"  │                                 │")
        print(f"  │     {Fore.YELLOW}{time_str} {date_str}{Fore.GREEN}      │")
        print("  │                                 │")
        print("  │   Automated Protocol Utility    │")
        print(f"  │ {Fore.WHITE}   by ZonaAirdrop {Fore.GREEN}(@ZonaAirdr0p){Style.RESET_ALL} │")
        print("  └─────────────────────────────────┘\n")
        time.sleep(1)


    async def load_proxies_from_file(self, use_proxy_mode: bool):
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

    def get_next_available_proxy(self, account_address):
        if account_address not in self.account_proxy_assignments:
            if not self.proxy_list:
                return None
            proxy_url = check_proxy_format(self.proxy_list[self.current_proxy_index])
            self.account_proxy_assignments[account_address] = proxy_url
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return self.account_proxy_assignments[account_address]

    def rotate_assigned_proxy(self, account_address):
        if not self.proxy_list:
            return None
        proxy_url = check_proxy_format(self.proxy_list[self.current_proxy_index])
        self.account_proxy_assignments[account_address] = proxy_url
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy_url
        
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

        return choice_input, should_rotate
    
    async def verify_connection(self, proxy_addr=None):
        connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(url="https://api.ipify.org?format=json", ssl=False) as response:
                    response.raise_for_status()
                    return True
        except (Exception, ClientResponseError) as e:
            log_message(
                f"{Fore.RED}Connection Status: Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
            )
            return None
    
    async def request_privy_nonce(self, wallet_address: str, proxy_addr=None, retries=5):
        url = f"{self.PRIVY_API_ENDPOINT}/api/v1/siwe/init"
        data = json.dumps({"address":wallet_address})
        headers = {
            **self.privy_headers_map[wallet_address],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                log_message(
                    f"{Fore.RED}Nonce Retrieval Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
                )

        return None
    
    async def authenticate_with_privy(self, eth_account_key: str, wallet_address: str, nonce_value: str, proxy_addr=None, retries=5):
        url = f"{self.PRIVY_API_ENDPOINT}/api/v1/siwe/authenticate"
        data = json.dumps(self.generate_siwe_payload(eth_account_key, wallet_address, nonce_value))
        headers = {
            **self.privy_headers_map[wallet_address],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                log_message(
                    f"{Fore.RED}Authentication Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
                )

        return None
    
    async def fetch_user_token_data(self, wallet_address: str, proxy_addr=None, retries=5):
        url = f"{self.CORE_API_ENDPOINT}/tokens/user/me"
        headers = {
            **self.core_headers_map[wallet_address],
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                log_message(
                    f"{Fore.RED}Balance Fetch Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
                )

        return None
    
    async def submit_checkin_activity(self, wallet_address: str, proxy_addr=None, retries=5):
        url = f"{self.CORE_API_ENDPOINT}/tokens/activity"
        data = json.dumps({
            "activityType":"LOGIN",
            "metadata":{
                "action":"user_login",
                "timestamp":datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            }
        })
        headers = {
            **self.core_headers_map[wallet_address],
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                log_message(
                    f"{Fore.RED}Check-in Activity Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
                )

        return None
    
    async def submit_game_activity(self, wallet_address: str, proxy_addr=None, retries=5):
        url = f"{self.CORE_API_ENDPOINT}/tokens/activity"
        data = json.dumps({
            "activityType":"GAME_PLAY",
            "metadata":{
                "action":"user_game",
                "timestamp":datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            }
        })
        headers = {
            **self.core_headers_map[wallet_address],
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                log_message(
                    f"{Fore.RED}Game Activity Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
                )

        return None
    
    async def initialize_agent_thread(self, wallet_address: str, proxy_addr=None, retries=5):
        url = f"{self.AI_AGENTS_API_ENDPOINT}/threads"
        data = json.dumps({"metadata":{}})
        headers = {
            **self.agents_headers_map[wallet_address],
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                log_message(
                    f"{Fore.YELLOW}[AI Chat Init]: {Fore.RED}Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
                )

        return None

    async def execute_agent_stream(self, wallet_address: str, thread_id: str, message_content: str, proxy_addr=None, retries=5):
        url = f"{self.AI_AGENTS_API_ENDPOINT}/threads/{thread_id}/runs/stream"
        data = json.dumps(self.generate_chat_stream_payload(message_content))
        headers = {
            **self.agents_headers_map[wallet_address],
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }

        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
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

            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                log_message(
                    f"{Fore.YELLOW}[AI Chat Response]: {Fore.RED}Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
                )

        return None
    
    async def submit_chat_activity(self, wallet_address: str, message_length: int, proxy_addr=None, retries=5):
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
            **self.core_headers_map[wallet_address],
            "Authorization": f"Bearer {self.auth_tokens[wallet_address]}",
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        await asyncio.sleep(3)
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy_addr) if proxy_addr else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                        response.raise_for_status()
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                log_message(
                    f"{Fore.YELLOW}[AI Chat Send]: {Fore.RED}Failed {Style.RESET_ALL}({Fore.YELLOW}{str(e)}{Style.RESET_ALL})"
                )

        return None
            
    async def handle_proxy_check(self, account_address: str, use_proxy_option: bool, rotate_proxy_option: bool):
        while True:
            active_proxy = self.get_next_available_proxy(account_address) if use_proxy_option and self.proxy_list else None
            display_proxy_info = active_proxy if active_proxy else "None (Direct)"
            log_message(
                f"{Fore.WHITE}Proxy Used: {Fore.YELLOW}{display_proxy_info}{Style.RESET_ALL}"
            )

            is_proxy_valid = await self.verify_connection(active_proxy)
            if not is_proxy_valid:
                if rotate_proxy_option and use_proxy_option and self.proxy_list:
                    active_proxy = self.rotate_assigned_proxy(account_address)
                    log_message(f"{Fore.YELLOW}Switching proxy for {get_masked_address(account_address)[1]}...{Style.RESET_ALL}")
                    await asyncio.sleep(5)
                    continue
                elif use_proxy_option and not self.proxy_list:
                    log_message(f"{Fore.RED}No proxies available, proceeding without proxy.{Style.RESET_ALL}")
                    return True
                else:
                    return False
            
            return True

    async def perform_user_login(self, private_key: str, wallet_address: str, use_proxy_option: bool, rotate_proxy_option: bool):
        is_connected = await self.handle_proxy_check(wallet_address, use_proxy_option, rotate_proxy_option)
        if is_connected:
            assigned_proxy = self.get_next_available_proxy(wallet_address) if use_proxy_option else None

            nonce_response = await self.request_privy_nonce(wallet_address, assigned_proxy)
            if nonce_response:
                retrieved_nonce = nonce_response["nonce"]

                login_response = await self.authenticate_with_privy(private_key, wallet_address, retrieved_nonce, assigned_proxy)
                if login_response:
                    self.auth_tokens[wallet_address] = login_response["token"]

                    log_message(
                        f"{Fore.GREEN}Login Status: Success!{Style.RESET_ALL}"
                    )
                    return True

        return False

    async def process_wallet_activities(self, private_key: str, wallet_address: str, chat_questions: list, use_proxy_option: bool, rotate_proxy_option: bool):
        login_successful = await self.perform_user_login(private_key, wallet_address, use_proxy_option, rotate_proxy_option)
        if login_successful:
            assigned_proxy = self.get_next_available_proxy(wallet_address) if use_proxy_option else None

            user_data = await self.fetch_user_token_data(wallet_address, assigned_proxy)
            if user_data:
                current_balance = user_data.get("token", {}).get("pointsTotal", 0)

                log_message(
                    f"{Fore.WHITE}Current Balance: {Fore.YELLOW}{current_balance} PUMPs{Style.RESET_ALL}"
                )

            checkin_result = await self.submit_checkin_activity(wallet_address, assigned_proxy)
            if checkin_result:
                activity_id_checkin = checkin_result.get("activityId", None)

                if activity_id_checkin:
                    log_message(
                        f"{Fore.GREEN}Daily Check-In: Activity Recorded.{Style.RESET_ALL}"
                    )
                else:
                    message_checkin = checkin_result.get("message", "Unknown Status")
                    log_message(
                        f"{Fore.YELLOW}Daily Check-In: {message_checkin}{Style.RESET_ALL}"
                    )

            game_result = await self.submit_game_activity(wallet_address, assigned_proxy)
            if game_result:
                activity_id_game = game_result.get("activityId", None)
                if activity_id_game:
                    log_message(
                        f"{Fore.GREEN}Game Play: Activity Recorded.{Style.RESET_ALL}"
                    )
                else:
                    message_game = game_result.get("message", "Unknown Status")
                    log_message(
                        f"{Fore.YELLOW}Game Play: {message_game}{Style.RESET_ALL}"
                    )

            log_message(f"{Fore.CYAN}Initiating AI Chat...{Style.RESET_ALL}")

            ai_chat_completed = False
            for _ in range(3):
                thread_info = await self.initialize_agent_thread(wallet_address, assigned_proxy)
                if thread_info:
                    thread_identifier = thread_info.get("thread_id")
                    chosen_message = random.choice(chat_questions)
                    message_len = int(len(chosen_message))

                    log_message(
                        f"{Fore.BLUE}  [Q]: {Fore.WHITE}{chosen_message}{Style.RESET_ALL}"
                    )

                    chat_response = await self.execute_agent_stream(wallet_address, thread_identifier, chosen_message, assigned_proxy)
                    if chat_response:
                        log_message(
                            f"{Fore.MAGENTA}  [A]: {Fore.WHITE}{chat_response}{Style.RESET_ALL}"
                        )

                        submit_chat_result = await self.submit_chat_activity(wallet_address, message_len, assigned_proxy)
                        if submit_chat_result:
                            activity_id_chat = submit_chat_result.get("activityId", None)
                            if activity_id_chat:
                                log_message(
                                    f"{Fore.GREEN}  Chat Activity: Sent Successfully.{Style.RESET_ALL}"
                                )
                                ai_chat_completed = True
                                break
                            else:
                                message_chat = submit_chat_result.get("message", "Unknown Status")
                                log_message(
                                    f"{Fore.YELLOW}  Chat Activity: {message_chat}{Style.RESET_ALL}"
                                )
                if not ai_chat_completed:
                    log_message(f"{Fore.YELLOW}  Retrying AI Chat...{Style.RESET_ALL}")
                    await asyncio.sleep(5)

            if not ai_chat_completed:
                log_message(f"{Fore.RED}Failed to complete AI Chat activity after multiple attempts.{Style.RESET_ALL}")
                    
    async def run_bot_main_loop(self):
        init(autoreset=True)

        try:
            with open('accounts.txt', 'r') as file:
                account_keys = [line.strip() for line in file if line.strip()]
            
            self.display_welcome_screen()
            
            proxy_mode_choice, should_rotate_proxies = self.get_user_choice_for_proxy()
            use_private_proxy = (proxy_mode_choice == 1)

            chat_questions_list = load_json_data("question_lists.json")
            if not chat_questions_list:
                log_message(f"{Fore.RED}No Questions Loaded. Please check 'question_lists.json'.{Style.RESET_ALL}")
                return

            if use_private_proxy:
                await self.load_proxies_from_file(use_private_proxy)
                if not self.proxy_list and use_private_proxy:
                    log_message(f"{Fore.YELLOW}Warning: Private proxy selected, but no proxies found in proxy.txt. Running without proxy.{Style.RESET_ALL}")
                    use_private_proxy = False

            while True:
                self.display_welcome_screen()
                log_message(f"{Fore.WHITE}Total Accounts: {Fore.CYAN}{len(account_keys)}{Style.RESET_ALL}")
                log_message(f"{Fore.WHITE}Proxy Rotation: {Fore.CYAN}{'Enabled' if should_rotate_proxies and use_private_proxy else 'Disabled'}{Style.RESET_ALL}\n")

                for key_entry in account_keys:
                    if key_entry:
                        wallet_address, masked_address = get_masked_address(key_entry)
                        
                        log_message(f"{Fore.BLUE}=== Processing Account [{masked_address}] ==={Style.RESET_ALL}")

                        if not wallet_address:
                            log_message(
                                f"{Fore.RED}Status: Invalid Private Key or Library Version Not Supported.{Style.RESET_ALL}"
                            )
                            log_message(f"{Fore.BLUE}======================================={Style.RESET_ALL}\n")
                            continue

                        random_user_agent = get_random_user_agent()

                        self.privy_headers_map[wallet_address] = {
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
                            "User-Agent": random_user_agent
                        }

                        self.core_headers_map[wallet_address] = {
                            "Accept": "*/*",
                            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                            "Origin": "https://app.wardenprotocol.org",
                            "Referer": "https://app.wardenprotocol.org/", 
                            "Sec-Fetch-Dest": "empty",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "same-site",
                            "User-Agent": random_user_agent
                        }

                        self.agents_headers_map[wallet_address] = {
                            "Accept": "*/*",
                            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                            "Origin": "https://app.wardenprotocol.org",
                            "Referer": "https://app.wardenprotocol.org/", 
                            "Sec-Fetch-Dest": "empty",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "cross-site",
                            "User-Agent": random_user_agent,
                            "X-Api-Key": "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"
                        }

                        await self.process_wallet_activities(key_entry, wallet_address, chat_questions_list, use_private_proxy, should_rotate_proxies)
                        log_message(f"{Fore.BLUE}=== Account Processing Finished ==={Style.RESET_ALL}\n")
                        await asyncio.sleep(5)

                log_message(f"{Fore.GREEN}All accounts processed. Entering cooldown phase...{Style.RESET_ALL}")
                cooldown_seconds = 24 * 60 * 60
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
            log_message(f"{Fore.RED}Error: 'accounts.txt' file not found. Please create this file with your private keys.{Style.RESET_ALL}")
            return
        except Exception as e:
            log_message(f"{Fore.RED}An unexpected error occurred in main loop: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    init(autoreset=True)

    try:
        bot_instance = WardenAutomation()
        asyncio.run(bot_instance.run_bot_main_loop())
    except KeyboardInterrupt:
        print(
            f"\n{Fore.RED}>> Bot Terminated by User.{Style.RESET_ALL}                                       "                              
        )
    except Exception as e:
        print(
            f"\n{Fore.RED}>> An unhandled error occurred: {e}{Style.RESET_ALL}                                       "                              
        )