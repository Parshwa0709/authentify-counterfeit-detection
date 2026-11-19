#!/usr/bin/env python3
"""
Automated Contract Deployment Script for Footwear Anti-Counterfeit System.
Compiles 'contracts/ProductRegistry.sol' using py-solc-x and deploys to local Ganache testnet.
Exports contract address and ABI to 'contract_data.json' for Flask backend integration.
"""

import json
import os
import sys
import datetime
from web3 import Web3
import solcx

# Default Ganache RPC Endpoint (GUI defaults to 7545, CLI defaults to 8545)
GANACHE_URL = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
SOLC_VERSION = "0.8.19"
CONTRACT_PATH = os.path.join(os.path.dirname(__file__), "contracts", "ProductRegistry.sol")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "contract_data.json")


def setup_compiler():
    """Ensure solc 0.8.19 is installed and set as active compiler."""
    print(f"[*] Checking Solidity compiler solc v{SOLC_VERSION}...")
    installed_versions = [str(v) for v in solcx.get_installed_solc_versions()]
    if SOLC_VERSION not in installed_versions:
        print(f"[*] solc v{SOLC_VERSION} not found locally. Installing...")
        solcx.install_solc(SOLC_VERSION)
        print(f"[+] solc v{SOLC_VERSION} installed successfully.")
    else:
        print(f"[+] solc v{SOLC_VERSION} is already installed.")
    solcx.set_solc_version(SOLC_VERSION)


def compile_contract(contract_path):
    """Compile Solidity smart contract and return (abi, bytecode)."""
    print(f"[*] Compiling contract from: {contract_path}")
    if not os.path.exists(contract_path):
        raise FileNotFoundError(f"Contract file not found at: {contract_path}")

    compiled = solcx.compile_files(
        [contract_path],
        output_values=["abi", "bin"],
        solc_version=SOLC_VERSION
    )

    contract_id = f"{contract_path}:ProductRegistry"
    if contract_id not in compiled:
        # Fallback to key matching by name
        matches = [k for k in compiled.keys() if "ProductRegistry" in k]
        if not matches:
            raise KeyError("ProductRegistry contract not found in compilation output.")
        contract_id = matches[0]

    contract_interface = compiled[contract_id]
    abi = contract_interface["abi"]
    bytecode = contract_interface["bin"]
    print("[+] Contract compiled successfully.")
    return abi, bytecode


def deploy():
    """Deploy compiled contract to Ganache and export artifact."""
    setup_compiler()
    abi, bytecode = compile_contract(CONTRACT_PATH)

    print(f"[*] Connecting to Ganache at {GANACHE_URL}...")
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

    # Test fallback to port 8545 if 7545 is unreachable
    if not w3.is_connected():
        fallback_url = "http://127.0.0.1:8545"
        print(f"[!] Could not connect to {GANACHE_URL}. Trying {fallback_url}...")
        w3 = Web3(Web3.HTTPProvider(fallback_url))

    if not w3.is_connected():
        print("\n[ERROR] Unable to connect to Ganache!")
        print("Please ensure Ganache is running:")
        print("  1. Launch Ganache GUI on port 7545 (Quickstart Ethereum Workspace)")
        print("  2. OR run Ganache CLI: `npx ganache --port 7545` (or `ganache-cli`)")
        sys.exit(1)

    accounts = w3.eth.accounts
    if not accounts:
        print("[ERROR] No accounts found in Ganache testnet.")
        sys.exit(1)

    deployer = accounts[0]
    balance_wei = w3.eth.get_balance(deployer)
    balance_eth = w3.from_wei(balance_wei, "ether")
    print(f"[+] Connected to Ganache! Deployer Account: {deployer} (Balance: {balance_eth} ETH)")

    # Instantiate Contract factory
    product_registry = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Estimate Gas
    gas_estimate = product_registry.constructor().estimate_gas({"from": deployer})
    print(f"[*] Estimated deployment gas: {gas_estimate}")

    # Build and send transaction
    print("[*] Broadcasting deployment transaction...")
    tx_hash = product_registry.constructor().transact({
        "from": deployer,
        "gas": int(gas_estimate * 1.2)
    })

    print(f"[*] Tx Hash: {tx_hash.hex()}. Waiting for block confirmation...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    contract_address = tx_receipt.contractAddress
    print(f"\n========================================================")
    print(f"[SUCCESS] ProductRegistry Deployed Successfully!")
    print(f"Contract Address : {contract_address}")
    print(f"Block Number     : {tx_receipt.blockNumber}")
    print(f"Gas Used         : {tx_receipt.gasUsed}")
    print(f"========================================================\n")

    # Save to contract_data.json
    export_payload = {
        "address": contract_address,
        "abi": abi,
        "network_url": w3.provider.endpoint_uri,
        "deployer": deployer,
        "deployed_at": datetime.datetime.utcnow().isoformat() + "Z"
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=4)

    print(f"[+] Saved deployment details and ABI to: {OUTPUT_FILE}")
    return contract_address


if __name__ == "__main__":
    deploy()
