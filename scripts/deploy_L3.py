from ape import accounts, project, networks
from ape_accounts import import_account_from_private_key
from pathlib import Path
from dotenv import load_dotenv
import os

ANIMECHAIN_CONFIG = {
    "name": "animechain",
    "chain_id": 69000,
    "rpc_url": "https://rpc-animechain-39xf6m45e3.t.conduit.xyz"
}

ARBITRUM_MAINNET_CONFIG = {
    "name": "arbitrum",
    "chain_id": 42161,
    "network": "arbitrum:mainnet:alchemy"
}

# Hardcoded L3 Inbox address for L2->L3 transactions
L3_INBOX_ADDRESS = "0xA203252940839c8482dD4b938b4178f842E343D7"

def setup_deployer():
    """Sets up and returns the deployer account"""
    # Load .env file from project root
    dotenv_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=dotenv_path)

    # Get private key and passphrase
    private_key = os.environ.get("PRIVATE_KEY", "").strip()
    if not private_key:
        raise ValueError("PRIVATE_KEY not found or empty in .env file")
    
    passphrase = os.environ.get("DEPLOYER_PASSPHRASE", "").strip()
    if not passphrase:
        raise ValueError("DEPLOYER_PASSPHRASE not found or empty in .env file")

    # Try to load existing account, import if it doesn't exist
    try:
        deployer = accounts.load("animechain_deployer")
    except:
        deployer = import_account_from_private_key("animechain_deployer", passphrase, private_key)

    # Enable auto-signing for the deployer account
    deployer.set_autosign(True, passphrase=passphrase)
    
    return deployer

def deploy_l2_relay(deployer):
    """Deploy L2Relay contract on Arbitrum mainnet"""
    print("\n--- Deploying L2Relay on Arbitrum Mainnet ---")
    
    # Use the Arbitrum mainnet network
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        print(f"Connected to Arbitrum Mainnet (Chain ID: {provider.chain_id})")
        if provider.chain_id != ARBITRUM_MAINNET_CONFIG['chain_id']:
            raise ValueError(f"Provider chain ID {provider.chain_id} does not match expected {ARBITRUM_MAINNET_CONFIG['chain_id']}")
        
        # Deploy L2Relay contract
        print("Deploying L2Relay contract...")
        l2_relay = deployer.deploy(
            project.L2Relay,
            required_confirmations=1
        )
        
        # Print deployment information
        print("\nL2Relay Deployment Summary:")
        print(f"L2Relay Contract: {l2_relay.address}")
        print(f"Owner: {l2_relay.owner()}")
        print(f"L3 Inbox Address (Hardcoded): {L3_INBOX_ADDRESS}")
        
        return l2_relay

def deploy_owner_registry(deployer, l2_relay_address=None):
    """Deploy OwnerRegistry contract on Animechain L3"""
    print("\n--- Deploying OwnerRegistry on Animechain L3 ---")
    
    # Use the custom network
    with networks.parse_network_choice("ethereum:animechain") as provider:
        print(f"Connected to L3 chain (Chain ID: {provider.chain_id})")
        if provider.chain_id != ANIMECHAIN_CONFIG['chain_id']:
            raise ValueError(f"Provider chain ID {provider.chain_id} does not match expected {ANIMECHAIN_CONFIG['chain_id']}")
        
        # Get input for L2 relay address if not provided
        if not l2_relay_address:
            l2_relay_address = input("Enter L2 relay address: ").strip()
        
        # Get input for commission hub template
        commission_hub_template = input("Enter commission hub template address: ").strip()
        
        # Validate inputs
        if not l2_relay_address or not commission_hub_template:
            raise ValueError("Both L2 relay and commission hub template addresses are required")
        
        # Deploy OwnerRegistry contract
        print("\nDeploying OwnerRegistry contract...")
        owner_registry = deployer.deploy(
            project.OwnerRegistry, 
            l2_relay_address, 
            commission_hub_template,
            required_confirmations=0
        )
        
        # Print deployment information
        print("\nOwnerRegistry Deployment Summary:")
        print(f"OwnerRegistry Contract: {owner_registry.address}")
        print(f"L2 Relay: {owner_registry.l2Relay()}")
        print(f"Commission Hub Template: {owner_registry.commissionHubTemplate()}")
        print(f"Owner: {owner_registry.owner()}")
        
        return owner_registry

def deploy_commission_hub_template(deployer):
    """Deploy CommissionHub template on Animechain L3"""
    print("\n--- Deploying CommissionHub Template on Animechain L3 ---")
    
    # Use the custom network
    with networks.parse_network_choice("ethereum:animechain") as provider:
        print(f"Connected to L3 chain (Chain ID: {provider.chain_id})")
        if provider.chain_id != ANIMECHAIN_CONFIG['chain_id']:
            raise ValueError(f"Provider chain ID {provider.chain_id} does not match expected {ANIMECHAIN_CONFIG['chain_id']}")
        
        # Deploy CommissionHub template
        print("Deploying CommissionHub template...")
        commission_hub_template = deployer.deploy(
            project.CommissionHub,
            required_confirmations=0
        )
        
        # Print deployment information
        print("\nCommissionHub Template Deployment Summary:")
        print(f"CommissionHub Template: {commission_hub_template.address}")
        
        return commission_hub_template

def update_l2_relay_with_l3_contract(l2_relay, owner_registry):
    """Update L2Relay with L3 OwnerRegistry address"""
    print("\n--- Updating L2Relay with L3 OwnerRegistry Address ---")
    
    # Use the Arbitrum mainnet network
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        print(f"Connected to Arbitrum Mainnet (Chain ID: {provider.chain_id})")
        
        # Update L2Relay with L3 OwnerRegistry address
        print(f"Setting L3 contract address to: {owner_registry.address}")
        tx = l2_relay.setL3Contract(owner_registry.address)
        
        print("L2Relay successfully updated with L3 OwnerRegistry address")

def main():
    # Choose deployment mode
    deploy_mode = input("Enter deployment mode (full, l2only, l3only): ").strip().lower()
    
    # Setup deployer account
    deployer = setup_deployer()
    
    l2_relay = None
    owner_registry = None
    
    # Deploy based on selected mode
    if deploy_mode in ["full", "l2only"]:
        # Deploy L2Relay on Arbitrum mainnet
        l2_relay = deploy_l2_relay(deployer)
    
    if deploy_mode in ["full", "l3only"]:
        # If we're only deploying L3 but need L2 address
        if deploy_mode == "l3only" and not l2_relay:
            l2_relay_address = input("Enter existing L2Relay address: ").strip()
        else:
            l2_relay_address = l2_relay.address if l2_relay else None
            
        # Deploy CommissionHub template
        commission_hub_template = deploy_commission_hub_template(deployer)
        
        # Deploy OwnerRegistry with L2Relay address
        owner_registry = deploy_owner_registry(deployer, l2_relay_address)
    
    # Update L2Relay with L3 OwnerRegistry address if both were deployed or provided
    if deploy_mode == "full" and l2_relay and owner_registry:
        update_l2_relay_with_l3_contract(l2_relay, owner_registry)
    elif deploy_mode != "full" and input("Update L2Relay with L3 OwnerRegistry address? (y/n): ").strip().lower() == 'y':
        # For non-full deployments, ask if update is needed
        if not l2_relay:
            l2_relay_address = input("Enter L2Relay address: ").strip()
            l2_relay = project.L2Relay.at(l2_relay_address)
        
        if not owner_registry:
            owner_registry_address = input("Enter OwnerRegistry address: ").strip()
            owner_registry = project.OwnerRegistry.at(owner_registry_address)
        
        update_l2_relay_with_l3_contract(l2_relay, owner_registry)
    
    print("\n=== Deployment Complete ===")
    print("Make sure to save these addresses for your application")

if __name__ == "__main__":
    main()