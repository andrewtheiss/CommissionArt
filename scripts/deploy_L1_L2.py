from ape import accounts, project, networks
from ape_accounts import import_account_from_private_key
from dotenv import load_dotenv
from pathlib import Path
import os
import time
from datetime import datetime
from contract_config_writer import update_contract_address, get_contract_address
import sys

# Maximum number of retries for L2 transactions
MAX_RETRIES = 3
# Wait time between retries (in seconds)
RETRY_WAIT = 10

def deploy_contracts():
    # Load .env file
    dotenv_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=dotenv_path)

    # Choose network
    network_choice = input("Enter network (local, testnet, production): ").strip().lower()
    if network_choice == "local":
        l1_network = "ethereum:local"
        l2_network = "arbitrum:local"
        config_network = "testnet"  # Use testnet config for local development
    elif network_choice == "testnet":
        l1_network = "ethereum:sepolia:alchemy"
        l2_network = "arbitrum:sepolia:alchemy"
        config_network = "testnet"
    elif network_choice == "production":
        l1_network = "ethereum:mainnet:alchemy"
        l2_network = "arbitrum:mainnet:alchemy"
        config_network = "mainnet"
    else:
        raise ValueError("Invalid network choice")

    # Load or import deployer account
    private_key = os.environ.get("PRIVATE_KEY")
    passphrase = os.environ.get("DEPLOYER_PASSPHRASE")
    if not private_key or not passphrase:
        raise ValueError("PRIVATE_KEY and DEPLOYER_PASSPHRASE must be set in .env")

    try:
        deployer = accounts.load("deployer")
    except:
        deployer = import_account_from_private_key("deployer", passphrase, private_key)
    deployer.set_autosign(True, passphrase=passphrase)

    # Check if the user wants to do a full redeployment
    full_redeploy = input("Do a full redeployment? (y/N): ").strip().lower() == 'y'
    
    # Get existing addresses from config
    l1_existing_address = get_contract_address(config_network, "l1")
    l2_existing_address = get_contract_address(config_network, "l2")

    # Track deployed contracts
    l1_contract = None
    l2_contract = None

    # Deploy or use existing L1 contract on Ethereum
    with networks.parse_network_choice(l1_network) as provider:
        if not full_redeploy and l1_existing_address and input(f"Use existing L1 contract at {l1_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing L1QueryOwner at: {l1_existing_address}")
            l1_contract = project.L1QueryOwner.at(l1_existing_address)
        else:
            print(f"Deploying L1QueryOwner on {l1_network}")
            # Get the Sequencer inbox address for the L1QueryOwner constructor
            if network_choice == "local":
                inbox_address = "0x0000000000000000000000000000000000000000"  # Default for local
            elif network_choice == "testnet":
                inbox_address = "0x6c97864CE4bEf387dE0b3310A44230f7E3F1be0D"  # Sepolia
            else:
                inbox_address = "0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6"  # Mainnet
            
            # Allow customizing the inbox address
            inbox_input = input(f"Enter Arbitrum Inbox address (default: {inbox_address}): ").strip()
            if inbox_input:
                inbox_address = inbox_input
            
            try:    
                l1_contract = deployer.deploy(project.L1QueryOwner, inbox_address, required_confirmations=1)
                print(f"L1QueryOwner deployed at: {l1_contract.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "l1", l1_contract.address, "L1QueryOwner")
            except Exception as e:
                print(f"Error deploying L1QueryOwner: {e}")
                sys.exit(1)

    # Deploy or use existing L2 contract on Arbitrum
    should_deploy_l2 = True
    
    # Determine if we should use existing L2 contract
    if not full_redeploy and l2_existing_address:
        use_existing_l2 = input(f"Use existing L2 contract at {l2_existing_address}? (Y/n): ").strip().lower() != 'n'
        if use_existing_l2:
            should_deploy_l2 = False
            print(f"Using existing L2Relay at: {l2_existing_address}")
            try:
                with networks.parse_network_choice(l2_network) as provider:
                    l2_contract = project.L2Relay.at(l2_existing_address)
            except Exception as e:
                print(f"Error connecting to existing L2 contract: {e}")
                print("Will attempt to deploy a new L2 contract.")
                should_deploy_l2 = True
    
    # Prepare for L2 deployment
    if should_deploy_l2:
        # Prompt for initial_l3_contract for L2
        initial_l3_contract = "0x0000000000000000000000000000000000000000"
        l3_existing_address = get_contract_address(config_network, "l3")
        
        if l3_existing_address:
            initial_l3_contract = l3_existing_address
            print(f"Using L3 address from config: {initial_l3_contract}")
        
        l3_input = input(f"Enter initial_l3_contract address (default: {initial_l3_contract}): ").strip()
        if l3_input:
            initial_l3_contract = l3_input
            # Also update the L3 address in the config
            update_contract_address(config_network, "l3", initial_l3_contract)
        
        # Deploy L2 contract with retry logic
        retry_count = 0
        l2_contract_address = None
        
        while retry_count < MAX_RETRIES and not l2_contract_address:
            try:
                print(f"Deploying L2Relay on {l2_network} (attempt {retry_count + 1}/{MAX_RETRIES})")
                with networks.parse_network_choice(l2_network) as provider:
                    # Set higher gas limits and confirmations for L2
                    if not l1_contract:
                        print("Error: L1 contract is not available.")
                        sys.exit(1)
                    
                    # For L2 deployments, we often need custom gas settings
                    gas_limit = 3000000  # Higher gas limit for L2
                    gas_price = None  # Let the network decide
                    
                    if retry_count > 0:
                        print(f"Retry attempt {retry_count + 1}, increasing gas parameters...")
                        gas_limit = 4000000 + (retry_count * 500000)  # Increase with each retry
                    
                    print(f"Using gas limit: {gas_limit}")
                    
                    # Update contract deployment parameters for L2
                    l2_contract = deployer.deploy(
                        project.L2Relay, 
                        l1_contract.address, 
                        initial_l3_contract,
                        gas_limit=gas_limit,
                        required_confirmations=0  # Set to 0 for L2, we'll manually wait
                    )
                    l2_contract_address = l2_contract.address
                    
                    # Wait for confirmation manually
                    print(f"Transaction sent. Waiting for confirmation...")
                    time.sleep(10)  # Give some time for the transaction to be mined
                    
                    # Verify the contract was actually deployed
                    verify_deployed = project.L2Relay.at(l2_contract_address)
                    print(f"L2Relay deployed and verified at: {l2_contract_address}")
                    
                    # Update the frontend config
                    update_contract_address(config_network, "l2", l2_contract_address, "L2Relay")
                    
                    break  # Exit loop if successful
            except Exception as e:
                retry_count += 1
                print(f"Error deploying L2Relay (attempt {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    print(f"Waiting {RETRY_WAIT} seconds before retrying...")
                    time.sleep(RETRY_WAIT)
                else:
                    print("Maximum retry attempts reached. L2 deployment failed.")
                    update_contract_address(config_network, "l2", "", "L2Relay")  # Clear the address
                    l2_contract = None  # Mark as not deployed
                    
        if not l2_contract_address:
            print("WARNING: L2 contract was not deployed successfully.")
            proceed = input("Do you want to continue with the deployment summary? (Y/n): ").strip().lower()
            if proceed == 'n':
                sys.exit(1)
    
    # Print deployment summary
    print("\n=== Deployment Summary ===")
    print(f"Network: {network_choice}")
    print(f"L1 Contract (L1QueryOwner): {l1_contract.address if l1_contract else 'Not deployed'}")
    
    if l2_contract:
        print(f"L2 Contract (L2Relay): {l2_contract.address}")
        print(f"L1 Helper configured in L2: {l1_contract.address if l1_contract else 'Not available'}")
        
        try:
            l3_address = l2_contract.l3_contract()
            print(f"L3 Contract configured in L2: {l3_address}")
            # If we have a real L3 address, update the config
            if l3_address and l3_address != "0x0000000000000000000000000000000000000000":
                update_contract_address(config_network, "l3", l3_address)
        except Exception as e:
            print(f"Could not retrieve L3 contract address: {e}")
    else:
        print("L2 Contract (L2Relay): Not deployed")
    
    print("\nFrontend configuration has been updated.")
    print(f"Make sure to use these contract addresses in your application.\n")

    return l1_contract, l2_contract

def main():
    try:
        deploy_contracts()
    except KeyboardInterrupt:
        print("\nDeployment canceled by user.")
    except Exception as e:
        print(f"\nUnexpected error during deployment: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()