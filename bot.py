import os
import json
import time
import random
import asyncio
import requests
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from colorama import init, Fore
from typing import List
from rich.console import Console
from rich.panel import Panel

init(autoreset=True)
console = Console()

# ======= CONSTANTS DEX & CONTRACTS =======
EXPLORER = "https://testnet.pharosscan.xyz/tx/"
CHAIN_ID = 688688

WPHRS_ADDRESS = "0x76aaada469d23216be5f7c596fa25f282ff9b364"
USDC_ADDRESS = "0x4d21582f50Fb5D211fd69ABF065AD07E8738870D"
USDT_ADDRESS = "0x2eD344c586303C98FC3c6D5B42C5616ED42f9D9d"
SWAP_ROUTER_ADDRESS = "0x1a4de519154ae51200b0ad7c90f7fac75547888a"
STAKING_CONTRACT = "0x0000000000000000000000000000000000000000"

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    }
]

USDC_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

SWAP_ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "internalType": "struct IV3SwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple",
            },
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes", "name": "path", "type": "bytes"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                ],
                "internalType": "struct IV3SwapRouter.ExactInputParams",
                "name": "params",
                "type": "tuple",
            },
        ],
        "name": "exactInput",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes[]", "name": "data", "type": "bytes[]"}],
        "name": "multicall",
        "outputs": [{"internalType": "bytes[]", "name": "results", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function",
    },
]

STAKING_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}],
        "name": "stake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# ======= RANDOM ADDRESS FUNCTION (for random token transfers) =======
def random_address():
    return "0x" + ''.join(random.choices("0123456789abcdef", k=40))

# ======= INITIAL DISPLAY =======
def show_banner():
    banner = """[bold cyan]
███████╗ ██████╗ ██╗   ██╗██╗██╗   ██╗
██╔════╝██╔═══██╗██║   ██║██║╚██╗ ██╔╝
███████╗██║   ██║██║   ██║██║ ╚████╔╝ 
╚════██║██║   ██║██║   ██║██║  ╚██╔╝  
███████║╚██████╔╝╚██████╔╝██║   ██║   
╚══════╝ ╚═════╝  ╚═════╝ ╚═╝   ╚═╝   
[/bold cyan]"""
    console.print(Panel.fit(banner, title="[bold yellow]Testnet Tools - Pharos Testnet[/bold yellow]", subtitle="BY SOUIY"))
# ======= UTILITY FUNCTIONS =======
def print_text(text, type="info"):
    colors = {
        "info": Fore.BLUE,
        "success": Fore.GREEN,
        "error": Fore.RED,
        "warning": Fore.YELLOW,
        "special": Fore.MAGENTA,
    }
    print(colors.get(type, Fore.WHITE) + text)

def random_element(arr):
    return random.choice(arr)

def random_number(min_val, max_val, decimal=4):
    return round(random.uniform(min_val, max_val), decimal)

def random_wait(delay: List[int]):
    t = random.randint(delay[0], delay[1])
    print_text(f"Waiting {t} seconds...", "info")
    time.sleep(t)

def load_data(file):
    if not os.path.exists(file): return []
    with open(file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def save_json(name, data, file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
    else:
        all_data = {}
    all_data[name] = data
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2)

# ======= CONFIGURATION =======
def load_env(path=".env"):
    config = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.strip().split("=", 1)
            k, v = k.strip(), v.strip().strip('"')
            if v.lower() in ["true", "false"]:
                config[k] = v.lower() == "true"
            elif v.startswith("[") and v.endswith("]"):
                try:
                    config[k] = json.loads(v.replace("'", '"'))
                except:
                    config[k] = []
            elif v.isdigit():
                config[k] = int(v)
            else:
                config[k] = v
    return config

CONFIG = load_env()
BASE_URL = CONFIG.get("BASE_URL")
RPC_URL = CONFIG.get("RPC_URL")
CHAIN_ID = CONFIG.get("CHAIN_ID")
DELAY = CONFIG.get("DELAY_BETWEEN_REQUESTS", [3, 10])
USE_PROXY = CONFIG.get("USE_PROXY", False)
REF_CODE = CONFIG.get("REF_CODE", "")

AMOUNT_SWAP = CONFIG.get("AMOUNT_SWAP", [0.001, 0.002])
AMOUNT_SEND = CONFIG.get("AMOUNT_SEND", [0.001, 0.002])
PERCENT_STAKE = CONFIG.get("PERCENT_STAKE", [5, 10])

# ======= DEFAULT HEADERS =======
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Origin": "https://testnet.pharosnetwork.xyz",
    "Referer": "https://testnet.pharosnetwork.xyz/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
}

# ======= MAIN BOT CLASS =======
class PharosBot:
    def __init__(self, private_key: str):
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.web3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.token = None

        # Convert addresses to checksum once
        self.swap_router_address = self.web3.to_checksum_address(SWAP_ROUTER_ADDRESS)
        self.token_address = self.web3.to_checksum_address(WPHRS_ADDRESS)
        self.usdc_address = self.web3.to_checksum_address(USDC_ADDRESS)
        self.staking_address = self.web3.to_checksum_address(STAKING_CONTRACT)

    def log(self, message, type="info"):
        print_text(f"[{self.address[:8]}] {message}", type)

    def sign_message(self, message="pharos"):
        message = encode_defunct(text=message)
        signed = self.account.sign_message(message)
        return signed.signature.hex()

    def auth(self):
        signature = self.sign_message()
        url = f"{BASE_URL}/user/login?address={self.address}&signature={signature}&invite_code={REF_CODE}"
        res = self.session.post(url)

        try:
            data = res.json()
        except Exception:
            self.log(f"Failed to parse JSON from server: {res.text}", "error")
            return

        if res.ok and "data" in data and "jwt" in data["data"]:
            self.token = data["data"]["jwt"]
            self.session.headers.update({"authorization": f"Bearer {self.token}"})
            save_json(self.address, {"jwt": self.token}, "localStorage.json")
            self.log("Login successful", "success")
        else:
            self.log(f"Login failed. Status: {res.status_code}, Message: {data}", "error")

    def get_profile(self):
        url = f"{BASE_URL}/user/profile?address={self.address}"
        res = self.session.get(url)
        if res.ok:
            data = res.json()
            points = data.get('data', {}).get('user_info', {}).get('TaskPoints', 0)
            self.log(f"Points: {points}", "special")
        else:
            self.log("Failed to get profile", "warning")

    def checkin(self):
        url_status = f"{BASE_URL}/sign/status?address={self.address}"
        res = self.session.get(url_status)
        if res.ok and res.json().get("data", {}).get("status") == "1111222":
            url = f"{BASE_URL}/sign/in?address={self.address}"
            res_checkin = self.session.post(url)
            if res_checkin.ok:
                self.log("Checkin successful!", "success")
            else:
                self.log("Checkin failed.", "warning")
        else:
            self.log("Already checked in today.", "info")

    def faucet(self):
        url = f"{BASE_URL}/faucet/daily?address={self.address}"
        res = self.session.post(url)
        if res.ok:
            self.log("Faucet claimed successfully!", "success")
        else:
            self.log("Failed to claim faucet.", "warning")

    def swap_token(self):
        amount = random_number(AMOUNT_SWAP[0], AMOUNT_SWAP[1])
        amount_in_wei = self.web3.to_wei(amount, 'ether')

        router = self.web3.eth.contract(
            address=self.swap_router_address,
            abi=SWAP_ROUTER_ABI
        )
        token = self.web3.eth.contract(
            address=self.token_address,
            abi=ERC20_ABI
        )

        # Get nonce once for two transactions
        nonce = self.web3.eth.get_transaction_count(self.address)

        # ===== APPROVE =====
        approve_tx = token.functions.approve(
            self.swap_router_address,
            amount_in_wei
        ).build_transaction({
            'from': self.address,
            'nonce': nonce,
            'gas': 60000,
            'gasPrice': self.web3.eth.gas_price,
            'chainId': CHAIN_ID
        })
        signed_approve = self.web3.eth.account.sign_transaction(approve_tx, self.private_key)
        self.web3.eth.send_raw_transaction(signed_approve.raw_transaction)
        self.log("✅ Token approve successful", "success")

        # Add small delay for approve to process
        time.sleep(5)

        # ===== SWAP =====
        deadline = int(time.time()) + 300
        params = {
            "tokenIn": self.token_address,
            "tokenOut": self.usdc_address,
            "fee": 500,
            "recipient": self.address,
            "amountIn": amount_in_wei,
            "amountOutMinimum": 0,
            "sqrtPriceLimitX96": 0
        }

        tx = router.functions.exactInputSingle(params).build_transaction({
            'from': self.address,
            'nonce': nonce + 1,  # Next nonce!
            'gas': 300000,
            'gasPrice': self.web3.eth.gas_price,
            'chainId': CHAIN_ID
        })
        signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        self.log(f"✅ Swap successful! TX: {EXPLORER}{tx_hash.hex()}", "success")

    def send_token(self):
        amount = random_number(AMOUNT_SEND[0], AMOUNT_SEND[1])
        amount_wei = self.web3.to_wei(amount, 'ether')
        destination = self.web3.to_checksum_address(random_address())

        token = self.web3.eth.contract(address=self.token_address, abi=ERC20_ABI)

        tx = token.functions.transfer(destination, amount_wei).build_transaction({
            'from': self.address,
            'nonce': self.web3.eth.get_transaction_count(self.address),
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price,
            'chainId': CHAIN_ID
        })
        signed = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        self.log(f"✅ Token sent successfully to {destination}, TX: {EXPLORER}{tx_hash.hex()}", "success")

    def staking(self):
        percent = random_number(PERCENT_STAKE[0], PERCENT_STAKE[1])
        token = self.web3.eth.contract(address=self.token_address, abi=ERC20_ABI)
        staking = self.web3.eth.contract(address=self.staking_address, abi=STAKING_ABI)

        balance = token.functions.balanceOf(self.address).call()
        stake_amount = int(balance * percent / 100)

        approve_tx = token.functions.approve(self.staking_address, stake_amount).build_transaction({
            'from': self.address,
            'nonce': self.web3.eth.get_transaction_count(self.address),
            'gas': 60000,
            'gasPrice': self.web3.eth.gas_price,
            'chainId': CHAIN_ID
        })
        signed_approve = self.web3.eth.account.sign_transaction(approve_tx, self.private_key)
        self.web3.eth.send_raw_transaction(signed_approve.raw_transaction)
        self.log(f"✅ Staking approve {stake_amount} successful", "success")

        stake_tx = staking.functions.stake(stake_amount).build_transaction({
            'from': self.address,
            'nonce': self.web3.eth.get_transaction_count(self.address),
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price,
            'chainId': CHAIN_ID
        })
        signed_stake = self.web3.eth.account.sign_transaction(stake_tx, self.private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_stake.raw_transaction)
        self.log(f"✅ Staking successful TX: {EXPLORER}{tx_hash.hex()}", "success")

    def run_all(self):
        self.auth()
        if not self.token:
            return
        random_wait(DELAY)
        self.get_profile()
        random_wait(DELAY)
        if CONFIG.get("AUTO_CHECKIN", True):
            self.checkin()
            time.sleep(5)
        random_wait(DELAY)
        if CONFIG.get("AUTO_FAUCET", True):
            self.faucet()
            time.sleep(5)
        random_wait(DELAY)
        if CONFIG.get("AUTO_SWAP", False):
            self.swap_token()
            time.sleep(5)
        random_wait(DELAY)
        if CONFIG.get("AUTO_SEND", False):
            self.send_token()
            time.sleep(5)
        random_wait(DELAY)
        if CONFIG.get("AUTO_STAKE", False):
            self.staking()

def main():
    show_banner()  
    print(Fore.YELLOW + "Pharos bot yaqn mulai...\n")
    private_keys = load_data("privateKeys.txt")
    if not private_keys:
        print_text("privateKeys.txt isiq iyaqh belehm!", "error")
        return

    for i, pk in enumerate(private_keys):
        print_text(f"\n🔄 Running account {i + 1}...")
        bot = PharosBot(pk if pk.startswith("0x") else "0x" + pk)
        bot.run_all()
        random_wait(CONFIG.get("DELAY_START_BOT", [1, 5]))

    print_text("\n✅ All accounts processed successfully.\n", "success")
    if TIME_SLEEP := CONFIG.get("TIME_SLEEP"):
        print_text(f"Sleeping for {TIME_SLEEP} minutes before restart...", "info")
        time.sleep(TIME_SLEEP * 60)

if __name__ == "__main__":
    main()