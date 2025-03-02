import random
import time
from web3 import Web3, HTTPProvider
from requests.exceptions import ConnectionError

# Konfigurasi jaringan RPC
RPC_URL = "https://evmrpc-testnet.0g.ai"
CHAIN_ID = 16600
MAX_RETRIES = 5         # Maksimum percobaan pengiriman ulang transaksi
WAIT_TIME = 10          # Waktu tunggu untuk cek ulang konfirmasi transaksi (dalam detik)
MAX_WAIT_CONFIRM = 300  # Maksimum waktu tunggu konfirmasi transaksi (5 menit)

# Koneksi ke RPC
web3 = Web3(HTTPProvider(RPC_URL))
if not web3.is_connected():
    raise ConnectionError("❌ Gagal terhubung ke jaringan 0G-Newton-Testnet. Coba lagi nanti.")
print(f"✅ Terhubung ke jaringan 0G-Newton-Testnet (Chain ID: {CHAIN_ID})")

# Baca private key dari file
try:
    with open("privatekey.txt", "r") as file:
        PRIVATE_KEY = file.read().strip()
except FileNotFoundError:
    raise FileNotFoundError("❌ File privatekey.txt tidak ditemukan!")

# Dapatkan alamat pengirim dari private key
account = web3.eth.account.from_key(PRIVATE_KEY)
SENDER_ADDRESS = account.address
print(f"🔑 Alamat Pengirim: {SENDER_ADDRESS}")

# Minta alamat tujuan dari user
RECIPIENT_ADDRESS = input("Masukkan alamat tujuan (0x...): ").strip()

# Konfigurasi jumlah transfer (random antara minimal & maksimal)
AMOUNT_MIN = float(input("Masukkan jumlah minimum A0GI yang akan dikirim: "))
AMOUNT_MAX = float(input("Masukkan jumlah maksimum A0GI yang akan dikirim: "))

if AMOUNT_MIN > AMOUNT_MAX:
    raise ValueError("❌ Jumlah minimum tidak boleh lebih besar dari jumlah maksimum!")

# Minta jumlah transaksi yang akan dikirim
repeat_count = int(input("Masukkan jumlah transaksi yang ingin dilakukan (contoh: 100): "))
print(f"🔄 Akan mengirim {repeat_count} transaksi ke {RECIPIENT_ADDRESS}")

# Dapatkan nonce awal (gunakan "pending" untuk menghindari nonce error)
nonce = web3.eth.get_transaction_count(SENDER_ADDRESS, "pending")

# Loop untuk mengirim transaksi secara berulang
for i in range(1, repeat_count + 1):
    # Pilih jumlah token secara random
    amount_to_send = round(random.uniform(AMOUNT_MIN, AMOUNT_MAX), 6)
    amount_wei = web3.to_wei(amount_to_send, "ether")

    # Dapatkan gas price dan tingkatkan agar transaksi lebih cepat
    gas_price = web3.eth.gas_price * 2

    # Bangun transaksi
    txn = {
        "to": RECIPIENT_ADDRESS,
        "value": amount_wei,
        "gas": 28000,   # Sesuaikan nilai gas jika diperlukan
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": CHAIN_ID,
    }

    # Tanda tangani transaksi
    signed_txn = web3.eth.account.sign_transaction(txn, PRIVATE_KEY)

    # Inisialisasi retry
    attempt = 0
    sent = False
    while not sent and attempt < MAX_RETRIES:
        attempt += 1
        try:
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hex = web3.to_hex(tx_hash)
            print(f"✅ [{i}/{repeat_count}] Transaksi berhasil dikirim! Hash: {tx_hex}")
            sent = True
        except Exception as e:
            if "mempool is full" in str(e):
                print("⚠️ Mempool penuh, menunggu 30 detik sebelum mencoba lagi...")
                time.sleep(30)
            else:
                print(f"❌ Error tidak terduga: {e}")
                break  # Keluar dari loop jika error tidak dapat ditangani

    if sent:
        # Perbarui nonce untuk transaksi berikutnya
        nonce += 1

        # Menunggu hingga transaksi dikonfirmasi
        wait_time = 0
        while wait_time < MAX_WAIT_CONFIRM:
            try:
                receipt = web3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    if receipt["status"] == 1:
                        print(f"✅ Transaksi {tx_hex} dikonfirmasi di blok {receipt['blockNumber']}.")
                    else:
                        print(f"❌ Transaksi {tx_hex} gagal.")
                    break
            except Exception:
                print(f"⏳ Menunggu konfirmasi transaksi {tx_hex}...")
            time.sleep(WAIT_TIME)
            wait_time += WAIT_TIME

        # Jeda singkat sebelum mengirim transaksi berikutnya
        time.sleep(5)
    else:
        print(f"❌ Transaksi ke-{i} gagal setelah {MAX_RETRIES} percobaan.")
