from ape import accounts, project, networks
from ape_accounts import import_account_from_private_key
from pathlib import Path
from dotenv import load_dotenv
import os
import sys
from web3 import Web3
from decimal import Decimal

# Import contract config writer utility
sys.path.append(str(Path(__file__).parent))
from contract_config_writer import get_contract_address, update_contract_address

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

def get_optimized_gas_params(provider):
    """Get optimized gas parameters based on current network conditions"""
    latest_block = provider.get_block('latest')
    if 'baseFeePerGas' in latest_block:
        base_fee = latest_block['baseFeePerGas']
        max_fee_per_gas = int(base_fee * 1.1)
        print(f"Current base fee: {base_fee} wei")
        print(f"Setting maxFeePerGas to: {max_fee_per_gas} wei (base fee × 1.1)")
        max_priority_fee = int(2e9)  # 2 Gwei
        return {
            "max_fee": max_fee_per_gas,
            "max_priority_fee": max_priority_fee
        }
    else:
        print("EIP-1559 not supported on this network, using default gas settings")
        return {}

def deploy_l2_relay(deployer):
    """Deploy L2Relay contract on Arbitrum mainnet"""
    print("\n--- Deploying L2Relay on Arbitrum Mainnet ---")
    
    # Use the Arbitrum mainnet network
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        print(f"Connected to Arbitrum Mainnet (Chain ID: {provider.chain_id})")
        if provider.chain_id != ARBITRUM_MAINNET_CONFIG['chain_id']:
            raise ValueError(f"Provider chain ID {provider.chain_id} does not match expected {ARBITRUM_MAINNET_CONFIG['chain_id']}")
        
        # Get optimized gas parameters
        gas_params = get_optimized_gas_params(provider)
        
        # Deploy L2Relay contract
        print("Deploying L2Relay contract...")
        deploy_kwargs = {"required_confirmations": 1}
        if gas_params:
            deploy_kwargs.update({
                "max_fee": gas_params["max_fee"],
                "max_priority_fee": gas_params["max_priority_fee"]
            })
            
        l2_relay = deployer.deploy(
            project.L2Relay,
            **deploy_kwargs
        )
        
        # Print deployment information
        print("\nL2Relay Deployment Summary:")
        print(f"L2Relay Contract: {l2_relay.address}")
        print(f"Owner: {l2_relay.owner()}")
        print(f"L3 Inbox Address (Hardcoded): {L3_INBOX_ADDRESS}")
        
        # Save to config
        update_contract_address("mainnet", "l2", l2_relay.address, "L2Relay")
        
        return l2_relay

def deploy_commission_hub_template(deployer, network_type="mainnet"):
    """Deploy CommissionHub template on Animechain L3 or use existing one"""
    print("\n--- CommissionHub Template Setup ---")
    
    # Check if CommissionHub is already in the configuration
    existing_hub_address = get_contract_address(network_type, "commissionHub")
    
    if existing_hub_address:
        print(f"Found existing CommissionHub template in config: {existing_hub_address}")
        use_existing = input("Use existing CommissionHub template? (y/n) [y]: ").strip().lower() or "y"
        
        if use_existing == "y":
            return project.CommissionHub.at(existing_hub_address)
    
    print("Deploying new CommissionHub Template on Animechain L3...")
    
    # Use the custom network
    with networks.parse_network_choice("ethereum:animechain") as provider:
        print(f"Connected to L3 chain (Chain ID: {provider.chain_id})")
        if provider.chain_id != ANIMECHAIN_CONFIG['chain_id']:
            raise ValueError(f"Provider chain ID {provider.chain_id} does not match expected {ANIMECHAIN_CONFIG['chain_id']}")
        
        # Get optimized gas parameters
        gas_params = get_optimized_gas_params(provider)
        
        # Deploy CommissionHub template
        deploy_kwargs = {"required_confirmations": 0}
        if gas_params:
            deploy_kwargs.update({
                "max_fee": gas_params["max_fee"],
                "max_priority_fee": gas_params["max_priority_fee"]
            })
            
        commission_hub_template = deployer.deploy(
            project.CommissionHub,
            **deploy_kwargs
        )
        
        # Print deployment information
        print("\nCommissionHub Template Deployment Summary:")
        print(f"CommissionHub Template: {commission_hub_template.address}")
        
        # Save to config
        update_contract_address(network_type, "commissionHub", commission_hub_template.address, "CommissionHub")
        
        return commission_hub_template

def deploy_owner_registry(deployer, l2_relay_address=None, commission_hub_template_address=None, network_type="mainnet"):
    """Deploy OwnerRegistry contract on Animechain L3"""
    print("\n--- Deploying OwnerRegistry on Animechain L3 ---")
    
    # Use the custom network
    with networks.parse_network_choice("ethereum:animechain") as provider:
        print(f"Connected to L3 chain (Chain ID: {provider.chain_id})")
        if provider.chain_id != ANIMECHAIN_CONFIG['chain_id']:
            raise ValueError(f"Provider chain ID {provider.chain_id} does not match expected {ANIMECHAIN_CONFIG['chain_id']}")
        
        # Get input for L2 relay address if not provided
        if not l2_relay_address:
            existing_l2_address = get_contract_address(network_type, "l2")
            if existing_l2_address:
                print(f"Found existing L2Relay in config: {existing_l2_address}")
                use_existing = input(f"Use existing L2Relay address? (y/n) [y]: ").strip().lower() or "y"
                if use_existing == "y":
                    l2_relay_address = existing_l2_address
                else:
                    l2_relay_address = input("Enter L2 relay address: ").strip()
            else:
                l2_relay_address = input("Enter L2 relay address: ").strip()
        
        # Get input for commission hub template if not provided
        if not commission_hub_template_address:
            existing_hub_address = get_contract_address(network_type, "commissionHub")
            if existing_hub_address:
                print(f"Found existing CommissionHub in config: {existing_hub_address}")
                use_existing = input(f"Use existing CommissionHub template address? (y/n) [y]: ").strip().lower() or "y"
                if use_existing == "y":
                    commission_hub_template_address = existing_hub_address
                else:
                    commission_hub_template_address = input("Enter commission hub template address: ").strip()
            else:
                commission_hub_template_address = input("Enter commission hub template address: ").strip()
        
        # Validate inputs
        if not l2_relay_address or not commission_hub_template_address:
            raise ValueError("Both L2 relay and commission hub template addresses are required")
        
        # Get optimized gas parameters
        gas_params = get_optimized_gas_params(provider)
        
        # Deploy OwnerRegistry contract
        print("\nDeploying OwnerRegistry contract...")
        deploy_kwargs = {
            "required_confirmations": 0
        }
        if gas_params:
            deploy_kwargs.update({
                "max_fee": gas_params["max_fee"],
                "max_priority_fee": gas_params["max_priority_fee"]
            })
            
        owner_registry = deployer.deploy(
            project.OwnerRegistry, 
            l2_relay_address, 
            commission_hub_template_address,
            **deploy_kwargs
        )
        
        # Print deployment information
        print("\nOwnerRegistry Deployment Summary:")
        print(f"OwnerRegistry Contract: {owner_registry.address}")
        print(f"L2 Relay: {owner_registry.l2Relay()}")
        print(f"Commission Hub Template: {owner_registry.commissionHubTemplate()}")
        print(f"Owner: {owner_registry.owner()}")
        
        # Save to config
        update_contract_address(network_type, "l3", owner_registry.address, "OwnerRegistry")
        
        return owner_registry

def update_l2_relay_with_l3_contract(l2_relay, owner_registry):
    """Update L2Relay with L3 OwnerRegistry address"""
    print("\n--- Updating L2Relay with L3 OwnerRegistry Address ---")
    
    # Use the Arbitrum mainnet network
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        print(f"Connected to Arbitrum Mainnet (Chain ID: {provider.chain_id})")
        
        # Get optimized gas parameters
        gas_params = get_optimized_gas_params(provider)
        
        # Update L2Relay with L3 OwnerRegistry address
        print(f"Setting L3 contract address to: {owner_registry.address}")
        
        tx_kwargs = {}
        if gas_params:
            tx_kwargs.update({
                "max_fee": gas_params["max_fee"],
                "max_priority_fee": gas_params["max_priority_fee"]
            })
            
        tx = l2_relay.setL3Contract(owner_registry.address, **tx_kwargs)
        
        print("L2Relay successfully updated with L3 OwnerRegistry address")

def main():
    # Choose deployment mode
    deploy_mode = input("Enter deployment mode (full, l2only, l3only): ").strip().lower()
    
    # Choose network type (mainnet/testnet)
    network_type = input("Enter network type (mainnet, testnet) [mainnet]: ").strip().lower() or "mainnet"
    
    # Setup deployer account
    deployer = setup_deployer()
    
    l2_relay = None
    owner_registry = None
    commission_hub_template = None
    
    # Deploy based on selected mode
    if deploy_mode in ["full", "l2only"]:
        # Deploy L2Relay on Arbitrum mainnet
        l2_relay = deploy_l2_relay(deployer)
    
    if deploy_mode in ["full", "l3only"]:
        # Deploy CommissionHub template first
        commission_hub_template = deploy_commission_hub_template(deployer, network_type)
        
        # If we're only deploying L3 but need L2 address
        if deploy_mode == "l3only" and not l2_relay:
            l2_relay_address = get_contract_address(network_type, "l2")
            if l2_relay_address:
                print(f"Found existing L2Relay in config: {l2_relay_address}")
                use_existing = input(f"Use existing L2Relay address? (y/n) [y]: ").strip().lower() or "y"
                if use_existing == "y":
                    l2_relay_address = l2_relay_address
                else:
                    l2_relay_address = input("Enter L2Relay address: ").strip()
            else:
                l2_relay_address = input("Enter existing L2Relay address: ").strip()
        else:
            l2_relay_address = l2_relay.address if l2_relay else None
            
        # Deploy OwnerRegistry with L2Relay address and CommissionHub template
        owner_registry = deploy_owner_registry(
            deployer, 
            l2_relay_address,
            commission_hub_template.address if commission_hub_template else None,
            network_type
        )
    
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
    print("Contract addresses have been saved to the configuration file")
    print("Make sure to save these addresses for your application")

if __name__ == "__main__":
    main()