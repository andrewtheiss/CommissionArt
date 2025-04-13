from ape import accounts, project, networks
from ape_accounts import import_account_from_private_key
from dotenv import load_dotenv
from pathlib import Path
import os
import time
from datetime import datetime
from .contract_config_writer import update_contract_address, get_contract_address
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
        # For local and testnet, we'll also use Arbitrum Sepolia for L3
        l3_network = "arbitrum:sepolia:alchemy"
        config_network = "testnet"  # Use testnet config for local development
    elif network_choice == "testnet":
        l1_network = "ethereum:sepolia:alchemy"
        l2_network = "arbitrum:sepolia:alchemy"
        # Use Arbitrum Sepolia as L3 for testnet (temporarily)
        l3_network = "arbitrum:sepolia:alchemy"
        config_network = "testnet"
    elif network_choice == "production":
        l1_network = "ethereum:mainnet:alchemy"
        l2_network = "arbitrum:mainnet:alchemy"
        # For production, we'll use Animechain L3
        l3_network = "ethereum:custom"
        config_network = "mainnet"
    else:
        raise ValueError("Invalid network choice")

    # For production, use Animechain L3 by default
    if network_choice == "production":
        print("Using Animechain L3 for production deployment")
    else:
        print(f"Using {l3_network} as L3 (temporary for testnet/local)")
        
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
    l3_existing_address = get_contract_address(config_network, "l3")
    
    # Define separate variable for commission hub template since it doesn't have its own layer in the config
    commission_hub_template_existing_address = None
    
    # If L3 registry exists, we'll store its contract for reference
    # but for now let's just continue with the deployment to avoid further errors
    
    # Track deployed contracts
    l1_contract = None
    l2_contract = None
    l3_owner_registry = None
    commission_hub_template = None

    # Deploy or use existing CommissionHub template on L3
    # For testnet, we're using Arbitrum Sepolia as L3
    with networks.parse_network_choice(l3_network) as provider:
        # First check if we should deploy CommissionHub template
        if not full_redeploy and commission_hub_template_existing_address and input(f"Use existing CommissionHub template at {commission_hub_template_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing CommissionHub template at: {commission_hub_template_existing_address}")
            commission_hub_template = project.CommissionHub.at(commission_hub_template_existing_address)
        else:
            print(f"Deploying CommissionHub template on {l3_network}")
            try:
                # For Arbitrum deployments, we may need higher gas limits
                gas_limit = 3000000  # Higher gas limit
                commission_hub_template = deployer.deploy(
                    project.CommissionHub, 
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"CommissionHub template deployed at: {commission_hub_template.address}")
                
                # For now, we'll only store the owner registry address in the l3 field
                # We'll add a comment here about the CommissionHub template address
                print(f"Note: CommissionHub template address: {commission_hub_template.address}")
                print(f"Save this address for reference; it's not currently stored in the config")
            except Exception as e:
                print(f"Error deploying CommissionHub template: {e}")
                sys.exit(1)

    # Deploy or use existing L2 contract to connect with OwnerRegistry
    with networks.parse_network_choice(l2_network) as provider:
        if not full_redeploy and l2_existing_address and input(f"Use existing L2 contract at {l2_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing L2Relay at: {l2_existing_address}")
            l2_contract = project.L2Relay.at(l2_existing_address)
        else:
            # We'll temporarily create L2Relay with placeholders; we'll update it later
            print(f"Creating temporary L2Relay on {l2_network} (will be updated later)")
            try:
                # Use placeholder addresses initially - we'll update them later
                placeholder_address = "0x0000000000000000000000000000000000000000"
                
                # For L2 deployments, we often need custom gas settings
                gas_limit = 3000000  # Higher gas limit for L2
                
                l2_contract = deployer.deploy(
                    project.L2Relay,
                    placeholder_address,  # L1 placeholder
                    placeholder_address,  # L3 placeholder
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"Temporary L2Relay created at: {l2_contract.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "l2", l2_contract.address, "L2Relay")
            except Exception as e:
                print(f"Error creating temporary L2Relay: {e}")
                sys.exit(1)

    # Deploy or use existing OwnerRegistry on L3 (using Arbitrum Sepolia for testnet)
    with networks.parse_network_choice(l3_network) as provider:
        if not full_redeploy and l3_existing_address and input(f"Use existing OwnerRegistry at {l3_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing OwnerRegistry at: {l3_existing_address}")
            l3_owner_registry = project.OwnerRegistry.at(l3_existing_address)
        else:
            print(f"Deploying OwnerRegistry on {l3_network}")
            try:
                # For Arbitrum deployments, we may need higher gas limits
                gas_limit = 3000000  # Higher gas limit
                
                # Use L2Relay address that we've just deployed or retrieved
                l3_owner_registry = deployer.deploy(
                    project.OwnerRegistry,
                    l2_contract.address,  # L2Relay address
                    commission_hub_template.address,  # CommissionHub template address
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"OwnerRegistry deployed at: {l3_owner_registry.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "l3", l3_owner_registry.address, "OwnerRegistry")
            except Exception as e:
                print(f"Error deploying OwnerRegistry: {e}")
                sys.exit(1)

    # Now update the L2Relay contract with the L3 OwnerRegistry address
    with networks.parse_network_choice(l2_network) as provider:
        print(f"Updating L2Relay with L3 OwnerRegistry address: {l3_owner_registry.address}")
        try:
            tx = l2_contract.setL3Contract(l3_owner_registry.address)
            print(f"L2Relay updated with L3 OwnerRegistry address")
        except Exception as e:
            print(f"Error updating L2Relay with L3 OwnerRegistry address: {e}")
            print(f"Please manually set the L3 contract address on L2Relay later.")

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
                inbox_address = "0xaAe29B0366299461418F5324a79Afc425BE5ae21"  # Sepolia for retryable tickets
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

    # Now update L2Relay with the L1QueryOwner address
    with networks.parse_network_choice(l2_network) as provider:
        print(f"Updating L2Relay with L1QueryOwner address: {l1_contract.address}")
        try:
            tx = l2_contract.setL1Helper(l1_contract.address)
            print(f"L2Relay updated with L1QueryOwner address")
        except Exception as e:
            print(f"Error updating L2Relay with L1QueryOwner address: {e}")
            print(f"Please manually set the L1 helper contract address on L2Relay later.")

    # Print deployment summary
    print("\n=== Deployment Summary ===")
    print(f"Network: {network_choice}")
    print(f"L1 Contract (Ethereum): {l1_contract.address if l1_contract else 'Not deployed'}")
    print(f"L2 Contract (Arbitrum): {l2_contract.address if l2_contract else 'Not deployed'}")
    
    if network_choice == "production":
        print(f"L3 Contracts (Animechain L3) - PENDING DEPLOYMENT:")
        print(f"  Note: Contracts will need to be deployed to Animechain L3 later")
        print(f"  Save these addresses for reference when deploying to production")
    else:
        print(f"L3 Contracts (Arbitrum Sepolia - temporary for testnet):")
    
    print(f"  - OwnerRegistry: {l3_owner_registry.address if l3_owner_registry else 'Not deployed'}")
    print(f"  - CommissionHub Template: {commission_hub_template.address if commission_hub_template else 'Not deployed'}")
    
    # Check if the contracts were properly linked
    if l2_contract:
        try:
            l1_helper = l2_contract.l1_helper_contract()
            l3_contract = l2_contract.l3_contract()
            print(f"\nContract Links:")
            print(f"  - L2Relay -> L1QueryOwner: {l1_helper}")
            print(f"  - L2Relay -> OwnerRegistry: {l3_contract}")
        except Exception as e:
            print(f"Could not retrieve contract links: {e}")
    
    if l3_owner_registry:
        try:
            l2relay = l3_owner_registry.l2relay()
            hub_template = l3_owner_registry.commission_hub_template()
            print(f"  - OwnerRegistry -> L2Relay: {l2relay}")
            print(f"  - OwnerRegistry -> CommissionHub Template: {hub_template}")
        except Exception as e:
            print(f"Could not retrieve OwnerRegistry links: {e}")
    
    print("\nFrontend configuration has been updated.")
    
    if network_choice == "production":
        print("\nIMPORTANT: For production, you will need to:")
        print("1. Deploy the L3 contracts to Animechain L3 later when available")
        print("2. Update the L2Relay contract with the new L3 OwnerRegistry address")
        print("3. Update your frontend configuration with the final production addresses")
    
    print(f"\nMake sure to use these contract addresses in your application.\n")

    return l1_contract, l2_contract, l3_owner_registry, commission_hub_template

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