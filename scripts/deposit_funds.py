#!/usr/bin/env python3
# Script to deposit funds into an L2Relay contract

import argparse
import sys
import os
from decimal import Decimal

from ape import accounts, networks, Contract, convert
from dotenv import load_dotenv

def deposit_funds(network='testnet', l2_address=None, amount=None):
    """
    Deposit funds into an L2Relay contract
    
    Args:
        network: Network to use (local, testnet, production)
        l2_address: L2Relay contract address
        amount: Amount of ETH to deposit (in ETH, not wei)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Load environment variables
    load_dotenv()
    
    # Validate inputs
    if network not in ['local', 'testnet', 'production']:
        print(f"ERROR: Invalid network '{network}'. Choose 'local', 'testnet', or 'production'")
        return False
    
    if not l2_address:
        print("ERROR: L2Relay contract address is required")
        return False
    
    if not amount:
        print("ERROR: Amount to deposit is required")
        return False
    
    try:
        # Convert string amount to Decimal for precision
        amount_decimal = Decimal(str(amount))
        # Convert to wei (1 ETH = 10^18 wei)
        amount_wei = int(amount_decimal * Decimal('1e18'))
    except Exception as e:
        print(f"ERROR: Invalid amount format: {e}")
        return False
    
    # Connect to the network
    try:
        if network == 'local':
            networks.parse_network_choice('arbitrum:local')
        elif network == 'testnet':
            networks.parse_network_choice('arbitrum:sepolia')
        elif network == 'production':
            networks.parse_network_choice('arbitrum:mainnet')
        
        print(f"Connected to {networks.active_provider.network.name}")
    except Exception as e:
        print(f"ERROR: Failed to connect to network: {e}")
        return False
    
    # Get private key from environment variable
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("ERROR: PRIVATE_KEY environment variable not found")
        return False
    
    # Create account from private key
    try:
        account = accounts.from_key(private_key)
        print(f"Using account: {account.address}")
        
        # Check account balance
        balance = account.balance
        print(f"Account balance: {convert('wei', 'ether', balance)} ETH")
        
        if balance < amount_wei:
            print(f"ERROR: Insufficient balance. Need {amount} ETH, but only have {convert('wei', 'ether', balance)} ETH")
            return False
    except Exception as e:
        print(f"ERROR: Failed to create account: {e}")
        return False
    
    # Load L2Relay contract
    try:
        l2_relay = Contract(l2_address)
        print(f"L2Relay contract loaded at {l2_address}")
        
        # Perform deposit
        print(f"\nDepositing {amount} ETH to L2Relay contract...")
        
        # Check if there is a specific deposit function, otherwise use direct transfer
        try:
            if hasattr(l2_relay, 'deposit'):
                # Use deposit function if it exists
                tx = account.call(l2_relay.deposit, value=amount_wei)
                receipt = tx.wait_for_receipt()
            else:
                # Direct transfer if no deposit function
                tx = account.transfer(l2_address, amount_wei)
                receipt = tx.wait_for_receipt()
            
            print(f"Transaction successful!")
            print(f"Transaction hash: {receipt.txn_hash}")
            print(f"Gas used: {receipt.gas_used}")
            
            # Check new contract balance
            new_balance = networks.provider.get_balance(l2_address)
            print(f"New contract balance: {convert('wei', 'ether', new_balance)} ETH")
            
            return True
        except Exception as e:
            print(f"ERROR: Transaction failed: {e}")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to interact with L2Relay contract: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Deposit funds into an L2Relay contract")
    parser.add_argument('--network', type=str, choices=['local', 'testnet', 'production'], 
                        default='testnet', help='Network to use')
    parser.add_argument('--l2', type=str, help='L2Relay contract address')
    parser.add_argument('--amount', type=float, help='Amount of ETH to deposit')
    
    args = parser.parse_args()
    
    # Interactive mode if arguments are missing
    l2_address = args.l2
    if not l2_address:
        l2_address = input("Enter L2Relay contract address: ")
    
    amount = args.amount
    if not amount:
        amount = float(input("Enter amount to deposit (in ETH): "))
    
    # Run the deposit
    success = deposit_funds(args.network, l2_address, amount)
    
    if not success:
        print("Deposit failed")
        sys.exit(1)
    
    print("Deposit completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main() 