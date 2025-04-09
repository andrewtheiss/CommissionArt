from ape import accounts, networks, Contract
import click
from typing import Optional

@click.command()
@click.option("--network", default="sepolia", help="Network to use: sepolia or mainnet")
@click.option("--layer", default="l1", help="Layer to send from: l1 or l2")
@click.option("--contract", required=True, help="Contract address to interact with")
@click.option("--message", required=True, help="Message to send")
@click.option("--abi-path", help="Path to ABI JSON file (optional)")
@click.option("--private-key", help="Private key to use (optional, otherwise uses account from ape)")
def bridge_message(
    network: str,
    layer: str, 
    contract: str, 
    message: str, 
    abi_path: Optional[str] = None,
    private_key: Optional[str] = None
):
    """
    Send a message across the bridge between L1 and L2
    """
    # Validate inputs
    if network not in ["sepolia", "mainnet"]:
        raise ValueError("Network must be either 'sepolia' or 'mainnet'")
    
    if layer not in ["l1", "l2"]:
        raise ValueError("Layer must be either 'l1' or 'l2'")
    
    # Set up the network connection
    if layer == "l1":
        if network == "sepolia":
            network_choice = "ethereum:sepolia"
        else:
            network_choice = "ethereum:mainnet"
    else:  # l2
        if network == "sepolia":
            network_choice = "arbitrum:sepolia"
        else:
            network_choice = "arbitrum:mainnet"
    
    # Connect to the network
    with networks.parse_network_choice(network_choice) as provider:
        print(f"Connected to {network_choice}")
        
        # Set up the account
        if private_key:
            account = accounts.containers["test"].add_account(private_key=private_key)
        else:
            try:
                account = accounts.load("default")
                print(f"Using account: {account.address}")
            except:
                raise ValueError("No account found. Please provide a private key or set up an account in ape")
        
        # Set up the contract
        if abi_path:
            # Load ABI from file
            contract_instance = Contract(contract, abi_path)
        else:
            # Use explorer to get ABI
            contract_instance = Contract(contract)
        
        # Determine function to call based on layer
        if layer == "l1":
            # For L1 -> L2 messaging (example for Arbitrum)
            if hasattr(contract_instance, "queryNFTAndSendBack"):
                # This is specifically for the L1QueryOwner contract
                print(f"Sending message from L1 -> L2: {message}")
                # Parse the message for token contract and ID
                try:
                    parts = message.split(",")
                    nft_contract = parts[0].strip()
                    token_id = int(parts[1].strip())
                    l2_receiver = parts[2].strip() if len(parts) > 2 else contract_instance.l2_contract()
                    
                    # Execute the transaction
                    tx = contract_instance.queryNFTAndSendBack(
                        nft_contract, 
                        token_id, 
                        l2_receiver, 
                        sender=account,
                        value="0.01 ether"  # For covering L2 gas
                    )
                    print(f"Transaction sent: {tx.txn_hash}")
                    
                except Exception as e:
                    print(f"Error parsing message. Expected format: 'nft_contract_address, token_id, l2_receiver_address'")
                    print(f"Error: {str(e)}")
            else:
                print(f"Contract does not have expected methods for L1->L2 messaging")
                
        else:  # l2
            # For L2 -> L1 messaging
            if hasattr(contract_instance, "requestNFTOwner"):
                # This is specifically for the L2Relay contract
                print(f"Sending message from L2 -> L1: {message}")
                try:
                    parts = message.split(",")
                    nft_contract = parts[0].strip()
                    token_id = int(parts[1].strip())
                    
                    # Execute the transaction
                    tx = contract_instance.requestNFTOwner(
                        nft_contract,
                        token_id,
                        sender=account,
                        value="0.001 ether"  # For covering cross-chain fees
                    )
                    print(f"Transaction sent: {tx.txn_hash}")
                except Exception as e:
                    print(f"Error parsing message. Expected format: 'nft_contract_address, token_id'")
                    print(f"Error: {str(e)}")
            else:
                print(f"Contract does not have expected methods for L2->L1 messaging")

if __name__ == "__main__":
    bridge_message() 