#!/usr/bin/env python3
# Script to withdraw funds from an L2Relay contract

import argparse
import sys
import os
from decimal import Decimal

from ape import accounts, networks, Contract, convert
from dotenv import load_dotenv

def withdraw_funds(network='testnet', l2_address=None, amount=None, recipient=None):
    """
    Withdraw funds from an L2Relay contract
    
    Args:
        network: Network to use (local, testnet, production)
        l2_address: L2Relay contract address
        amount: Amount of ETH to withdraw (in ETH, not wei)
        recipient: Address to receive the withdrawn funds (defaults to sender)
    
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
        print("ERROR: Amount to withdraw is required")
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
        
        # Set recipient to sender if not specified
        if not recipient:
            recipient = account.address
            print(f"No recipient specified, using sender address: {recipient}")
        
        print(f"Funds will be sent to: {recipient}")
    except Exception as e:
        print(f"ERROR: Failed to create account: {e}")
        return False
    
    # Load L2Relay contract
    try:
        l2_relay = Contract(l2_address)
        print(f"L2Relay contract loaded at {l2_address}")
        
        # Check contract balance
        contract_balance = networks.provider.get_balance(l2_address)
        print(f"Contract balance: {convert('wei', 'ether', contract_balance)} ETH")
        
        if contract_balance < amount_wei:
            print(f"ERROR: Insufficient contract balance. Requested {amount} ETH, but contract only has {convert('wei', 'ether', contract_balance)} ETH")
            return False
        
        # Check if caller is the owner
        try:
            owner = l2_relay.owner()
            if owner.lower() != account.address.lower():
                print(f"ERROR: Only the contract owner can withdraw funds")
                print(f"Current owner: {owner}")
                print(f"Your address: {account.address}")
                return False
        except Exception:
            print("WARNING: Could not verify contract ownership. Proceeding anyway...")
        
        # Perform withdrawal
        print(f"\nWithdrawing {amount} ETH from L2Relay contract...")
        
        # Look for different withdrawal function names
        withdraw_function = None
        possible_functions = ['withdraw', 'withdrawFunds', 'withdrawETH', 'withdrawBalance']
        
        for func_name in possible_functions:
            if hasattr(l2_relay, func_name):
                withdraw_function = getattr(l2_relay, func_name)
                print(f"Found withdrawal function: {func_name}")
                break
        
        if not withdraw_function:
            print("ERROR: Could not find a suitable withdrawal function in the contract")
            return False
        
        # Try different parameter combinations for the withdrawal function
        try:
            # Try with amount and recipient
            tx = account.call(withdraw_function, amount_wei, recipient)
            receipt = tx.wait_for_receipt()
        except Exception as e1:
            try:
                # Try with just amount
                tx = account.call(withdraw_function, amount_wei)
                receipt = tx.wait_for_receipt()
            except Exception as e2:
                try:
                    # Try with just recipient
                    tx = account.call(withdraw_function, recipient)
                    receipt = tx.wait_for_receipt()
                except Exception as e3:
                    try:
                        # Try with no parameters
                        tx = account.call(withdraw_function)
                        receipt = tx.wait_for_receipt()
                    except Exception as e4:
                        print(f"ERROR: All withdrawal attempts failed")
                        print(f"Error with amount and recipient: {e1}")
                        print(f"Error with just amount: {e2}")
                        print(f"Error with just recipient: {e3}")
                        print(f"Error with no parameters: {e4}")
                        return False
        
        print(f"Transaction successful!")
        print(f"Transaction hash: {receipt.txn_hash}")
        print(f"Gas used: {receipt.gas_used}")
        
        # Check new contract balance
        new_balance = networks.provider.get_balance(l2_address)
        print(f"New contract balance: {convert('wei', 'ether', new_balance)} ETH")
        
        return True
            
    except Exception as e:
        print(f"ERROR: Failed to interact with L2Relay contract: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Withdraw funds from an L2Relay contract")
    parser.add_argument('--network', type=str, choices=['local', 'testnet', 'production'], 
                        default='testnet', help='Network to use')
    parser.add_argument('--l2', type=str, help='L2Relay contract address')
    parser.add_argument('--amount', type=float, help='Amount of ETH to withdraw')
    parser.add_argument('--recipient', type=str, help='Address to receive the withdrawn funds (defaults to sender)')
    
    args = parser.parse_args()
    
    # Interactive mode if arguments are missing
    l2_address = args.l2
    if not l2_address:
        l2_address = input("Enter L2Relay contract address: ")
    
    amount = args.amount
    if not amount:
        amount = float(input("Enter amount to withdraw (in ETH): "))
    
    recipient = args.recipient
    if not recipient and input("Do you want to specify a recipient address? (y/n): ").lower() == 'y':
        recipient = input("Enter recipient address: ")
    
    # Run the withdrawal
    success = withdraw_funds(args.network, l2_address, amount, recipient)
    
    if not success:
        print("Withdrawal failed")
        sys.exit(1)
    
    print("Withdrawal completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main() 