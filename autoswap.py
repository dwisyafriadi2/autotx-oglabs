import time
from web3 import Web3, HTTPProvider
from web3.exceptions import TransactionNotFound

def print_banner():
    print("""
    ==== AUTO SWAP USDT to ETH ====
    Automation  : Auto Install Node and Bot
    Telegram    : @dasarpemulung | @parapemulung
    Buy Crypto  : @ecerankriptobot
    =================================
    """)

def wait_for_confirmation(web3, tx_hash, max_wait=1800, poll_interval=5):
    """Wait for transaction confirmation up to max_wait seconds."""
    print(f"⏳ Waiting for confirmation of transaction {web3.to_hex(tx_hash)} ...")
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            if receipt is not None:
                print(f"🔍 Transaction {web3.to_hex(tx_hash)} confirmed in block {receipt['blockNumber']}.")
                if receipt["status"] == 1:
                    print("✅ Transaction succeeded!")
                else:
                    print("❌ Transaction reverted!")
                return receipt
        except TransactionNotFound:
            pass
        time.sleep(poll_interval)
    print(f"⚠️ Transaction {web3.to_hex(tx_hash)} not confirmed in {max_wait} seconds.")
    return None

def send_transaction_with_retry(web3, signed_txn, max_retries=10, retry_delay=30):
    """Send a transaction with retry on 'mempool is full' errors."""
    for attempt in range(max_retries):
        try:
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"✅ Transaction sent! Hash: {web3.to_hex(tx_hash)}")
            return tx_hash
        except Exception as e:
            if "mempool is full" in str(e):
                print(f"⚠️ Mempool full. Waiting {retry_delay} seconds before retrying... (Attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                print(f"❌ Error sending transaction: {e}")
                break
    return None

def main():
    # Basic configuration
    RPC_URL = "https://og-testnet-evm.itrocket.net"
    CHAIN_ID = 16600
    MAX_RETRIES = 10
    RETRY_DELAY = 30  # seconds to wait on mempool full

    # Set gas parameters:
    # For both approve and swap, gas price = 0.000000005 Gneuron = 5,000,000,000 wei.
    GAS_PRICE = int(0.000000005 * 10**18)
    GAS_APPROVE = 39566
    GAS_SWAP = 8750000

    # Connect to RPC
    web3 = Web3(HTTPProvider(RPC_URL))
    if not web3.is_connected():
        print("❌ Failed to connect to 0G-Newton-Testnet.")
        return
    print(f"✅ Connected to 0G-Newton-Testnet (Chain ID: {CHAIN_ID})")

    # Read private key from file
    try:
        with open("privatekey.txt", "r") as f:
            PRIVATE_KEY = f.read().strip()
    except FileNotFoundError:
        print("❌ privatekey.txt not found!")
        return

    # Get sender address
    account = web3.eth.account.from_key(PRIVATE_KEY)
    sender = account.address
    print(f"🔑 Sender Address: {sender}")

    # Convert addresses to checksum
    usdt_address = web3.to_checksum_address("0x9A87C2412d500343c073E5Ae5394E3bE3874F76b")
    swap_contract_address = web3.to_checksum_address("0xD86b764618c6E3C078845BE3c3fCe50CE9535Da7")
    # Use the standard ETH magic address (checksum)
    eth_token_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

    # Minimal ABI for USDT approve
    usdt_abi = [
        {
            "constant": False,
            "inputs": [
                {"name": "_spender", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "approve",
            "outputs": [{"name": "success", "type": "bool"}],
            "type": "function"
        }
    ]

    # Minimal ABI for swap function
    swap_abi = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokenFrom", "type": "address"},
                {"internalType": "address", "name": "tokenTo", "type": "address"},
                {"internalType": "uint256", "name": "minReturn", "type": "uint256"},
                {"internalType": "address", "name": "sender", "type": "address"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
                {"internalType": "uint256", "name": "fee", "type": "uint256"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"}
            ],
            "name": "swap",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

    # Create contract instances
    usdt_contract = web3.eth.contract(address=usdt_address, abi=usdt_abi)
    swap_contract = web3.eth.contract(address=swap_contract_address, abi=swap_abi)

    # Ask user for input values
    tx_count = int(input("Enter number of auto swap transactions: "))
    amount_usdt_input = float(input("Enter amount of Tether to swap per transaction (e.g., 1): "))
    # Convert USDT to smallest unit (6 decimals)
    amount_usdt = int(amount_usdt_input * (10**6))
    eth_amount_input = float(input("Enter desired amount of ETH to receive per transaction (e.g., 0.000001): "))
    # Convert ETH to wei (18 decimals)
    amount_out = int(eth_amount_input * (10**18))

    # Set other parameters:
    # For a small swap, set minReturn to 90% of desired output.
    min_return = int(amount_out * 0.9)
    fee = 0
    deadline = int(time.time()) + 1800  # 30 minutes from now

    # Get starting nonce
    nonce = web3.eth.get_transaction_count(sender, "pending")

    # For each transaction, first perform approve, then swap
    for i in range(1, tx_count + 1):
        print(f"\n--- Transaction {i} ---")
        # Approve transaction with retry mechanism
        approve_success = False
        approve_attempt = 0
        while not approve_success and approve_attempt < MAX_RETRIES:
            approve_attempt += 1
            try:
                approve_txn = usdt_contract.functions.approve(
                    swap_contract_address,
                    amount_usdt
                ).build_transaction({
                    "chainId": CHAIN_ID,
                    "gas": GAS_APPROVE,
                    "gasPrice": GAS_PRICE,
                    "nonce": nonce
                })
                signed_approve = web3.eth.account.sign_transaction(approve_txn, PRIVATE_KEY)
                approve_tx_hash = send_transaction_with_retry(web3, signed_approve, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY)
                if approve_tx_hash is None:
                    print(f"❌ Approve transaction {i} failed to send.")
                    break
                print(f"[{i}] Approve sent: {web3.to_hex(approve_tx_hash)}")
                nonce += 1
                receipt = wait_for_confirmation(web3, approve_tx_hash, max_wait=300, poll_interval=5)
                if receipt and receipt["status"] == 1:
                    print(f"✅ Approve transaction {i} confirmed in block {receipt['blockNumber']}.")
                    approve_success = True
                else:
                    print(f"❌ Approve transaction {i} failed or timed out.")
                    break
            except Exception as e:
                print(f"❌ Error during approve transaction {i}: {e}")
                break

        if not approve_success:
            print(f"❌ Transaction {i} failed at the approve stage.")
            continue

        # Swap transaction with retry mechanism
        swap_success = False
        swap_attempt = 0
        while not swap_success and swap_attempt < MAX_RETRIES:
            swap_attempt += 1
            try:
                swap_txn = swap_contract.functions.swap(
                    usdt_address,
                    eth_token_address,
                    min_return,
                    sender,
                    amount_usdt,
                    amount_out,
                    fee,
                    deadline
                ).build_transaction({
                    "chainId": CHAIN_ID,
                    "gas": GAS_SWAP,
                    "gasPrice": GAS_PRICE,
                    "nonce": nonce
                })
                signed_swap = web3.eth.account.sign_transaction(swap_txn, PRIVATE_KEY)
                swap_tx_hash = send_transaction_with_retry(web3, signed_swap, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY)
                if swap_tx_hash is None:
                    print(f"❌ Swap transaction {i} failed to send.")
                    break
                print(f"[{i}] Swap sent: {web3.to_hex(swap_tx_hash)}")
                nonce += 1
                receipt = wait_for_confirmation(web3, swap_tx_hash, max_wait=1800, poll_interval=5)
                if receipt and receipt["status"] == 1:
                    print(f"✅ Swap transaction {i} confirmed in block {receipt['blockNumber']}.")
                    swap_success = True
                else:
                    print(f"❌ Swap transaction {i} failed or timed out.")
                    break
            except Exception as e:
                print(f"❌ Error during swap transaction {i}: {e}")
                break
        time.sleep(5)

if __name__ == "__main__":
    print_banner()
    main()
