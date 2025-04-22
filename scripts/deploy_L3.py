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

def deploy_owner_registry():
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

    # Use the custom network
    with networks.parse_network_choice("ethereum:animechain") as provider:
        print(f"Connected to L3 chain (Chain ID: {provider.chain_id})")
        if provider.chain_id != ANIMECHAIN_CONFIG['chain_id']:
            raise ValueError(f"Provider chain ID {provider.chain_id} does not match expected {ANIMECHAIN_CONFIG['chain_id']}")
        
        # Get input for required constructor parameters
        l2_relay = input("Enter L2 relay address: ").strip()
        commission_hub_template = input("Enter commission hub template address: ").strip()
        
        # Validate inputs
        if not l2_relay or not commission_hub_template:
            raise ValueError("Both L2 relay and commission hub template addresses are required")
        
        # Deploy OwnerRegistry contract
        print("\nDeploying OwnerRegistry contract...")
        owner_registry = deployer.deploy(
            project.OwnerRegistry, 
            l2_relay, 
            commission_hub_template,
            required_confirmations=0
        )
        
        # Print deployment information
        print("\nDeployment Summary:")
        print(f"OwnerRegistry Contract: {owner_registry.address}")
        print(f"L2 Relay: {owner_registry.l2Relay()}")
        print(f"Commission Hub Template: {owner_registry.commissionHubTemplate()}")
        print(f"Owner: {owner_registry.owner()}")
        
        return owner_registry

def main():
    deploy_owner_registry()

if __name__ == "__main__":
    main()