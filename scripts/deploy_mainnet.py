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

def deploy_l1_query_owner(deployer, network_type="mainnet"):
    print("\n--- L1QueryOwner Setup ---")
    
    l1_network = "ethereum:mainnet:alchemy"
    inbox_address = "0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6"  # Mainnet Inbox
    
    existing_l1_address = get_contract_address(network_type, "l1")
    if existing_l1_address:
        print(f"Found existing L1QueryOwner in config: {existing_l1_address}")
        use_existing = input("Use existing L1QueryOwner? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.L1QueryOwner.at(existing_l1_address)
    
    print(f"Deploying new L1QueryOwner on {l1_network}...")
    
    with networks.parse_network_choice(l1_network) as provider:
        l1_contract = deployer.deploy(project.L1QueryOwner, inbox_address, required_confirmations=1)
        print(f"L1QueryOwner deployed at: {l1_contract.address}")
        update_contract_address(network_type, "l1", l1_contract.address, "L1QueryOwner")
        return l1_contract

def deploy_l2_relay(deployer, network_type="mainnet"):
    print("\n--- L2Relay Setup ---")
    
    existing_l2_address = get_contract_address(network_type, "l2")
    if existing_l2_address:
        print(f"Found existing L2Relay in config: {existing_l2_address}")
        use_existing = input("Use existing L2Relay? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.L2Relay.at(existing_l2_address)
    
    print("Deploying new L2Relay on Arbitrum Mainnet...")
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 1}
        if gas_params:
            deploy_kwargs.update({
                "max_fee": gas_params["max_fee"],
                "max_priority_fee": gas_params["max_priority_fee"]
            })
        l2_relay = deployer.deploy(project.L2Relay, **deploy_kwargs)
        print(f"L2Relay deployed at: {l2_relay.address}")
        update_contract_address(network_type, "l2", l2_relay.address, "L2Relay")
        return l2_relay

def deploy_commission_hub_template(deployer, network_type="mainnet"):
    print("\n--- CommissionHub Template Setup ---")
    
    existing_hub_address = get_contract_address(network_type, "commissionHub")
    if existing_hub_address:
        print(f"Found existing CommissionHub template in config: {existing_hub_address}")
        use_existing = input("Use existing CommissionHub template? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.CommissionHub.at(existing_hub_address)
    
    print("Deploying new CommissionHub Template on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        if gas_params:
            deploy_kwargs.update({
                "max_fee": gas_params["max_fee"],
                "max_priority_fee": gas_params["max_priority_fee"]
            })
        commission_hub_template = deployer.deploy(project.CommissionHub, **deploy_kwargs)
        print(f"CommissionHub Template deployed at: {commission_hub_template.address}")
        update_contract_address(network_type, "commissionHub", commission_hub_template.address, "CommissionHub")
        return commission_hub_template

def deploy_owner_registry(deployer, l2_relay_address, commission_hub_template_address, network_type="mainnet"):
    print("\n--- OwnerRegistry Setup ---")
    
    existing_l3_address = get_contract_address(network_type, "l3")
    if existing_l3_address:
        print(f"Found existing OwnerRegistry in config: {existing_l3_address}")
        use_existing = input("Use existing OwnerRegistry? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.OwnerRegistry.at(existing_l3_address)
    
    print("Deploying new OwnerRegistry on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        if gas_params:
            deploy_kwargs.update({
                "max_fee": gas_params["max_fee"],
                "max_priority_fee": gas_params["max_priority_fee"]
            })
        owner_registry = deployer.deploy(project.OwnerRegistry, l2_relay_address, commission_hub_template_address, **deploy_kwargs)
        print(f"OwnerRegistry deployed at: {owner_registry.address}")
        update_contract_address(network_type, "l3", owner_registry.address, "OwnerRegistry")
        return owner_registry

def update_l2_relay_with_l3_contract(deployer, l2_relay, owner_registry):
    print("\n--- Updating L2Relay with L3 OwnerRegistry Address ---")
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        gas_params = get_optimized_gas_params(provider)
        tx_kwargs = {}
        if gas_params:
            tx_kwargs.update({
                "max_fee": gas_params["max_fee"],
                "max_priority_fee": gas_params["max_priority_fee"]
            })
        tx = l2_relay.setL3Contract(owner_registry.address, sender=deployer, **tx_kwargs)
        print("L2Relay successfully updated with L3 OwnerRegistry address")

def main():
    network_type = "mainnet"  # Always use mainnet
    deploy_mode = input("Enter deployment mode (full, l2only, l3only): ").strip().lower()
    
    deployer = setup_deployer()
    
    l1_contract = None
    l2_relay = None
    owner_registry = None
    commission_hub_template = None
    
    if deploy_mode == "full":
        l1_contract = deploy_l1_query_owner(deployer, network_type)
        l2_relay = deploy_l2_relay(deployer, network_type)
        commission_hub_template = deploy_commission_hub_template(deployer, network_type)
        owner_registry = deploy_owner_registry(deployer, l2_relay.address, commission_hub_template.address, network_type)
        update_l2_relay_with_l3_contract(deployer, l2_relay, owner_registry)
        with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
            l1_chain_id = 1  # For mainnet
            tx = l2_relay.updateCrossChainQueryOwnerContract(l1_contract.address, l1_chain_id)
            print(f"L1QueryOwner registered in L2Relay for chain ID {l1_chain_id}")
    
    elif deploy_mode == "l2only":
        l2_relay = deploy_l2_relay(deployer, network_type)
    
    elif deploy_mode == "l3only":
        commission_hub_template = deploy_commission_hub_template(deployer, network_type)
        l2_address = get_contract_address(network_type, "l2")
        if l2_address:
            use_existing = input(f"Use existing L2Relay at {l2_address}? (y/n) [y]: ").strip().lower() or "y"
            if use_existing != "y":
                l2_address = input("Enter L2 relay address: ").strip()
        else:
            l2_address = input("Enter L2 relay address: ").strip()
        ch_address = commission_hub_template.address if commission_hub_template else get_contract_address(network_type, "commissionHub")
        if not ch_address:
            ch_address = input("Enter CommissionHub template address: ").strip()
        owner_registry = deploy_owner_registry(deployer, l2_address, ch_address, network_type)
    
    if deploy_mode != "full" and input("Update L2Relay with L3 OwnerRegistry address? (y/n): ").strip().lower() == 'y':
        if not l2_relay:
            l2_address = input("Enter L2Relay address: ").strip()
            l2_relay = project.L2Relay.at(l2_address)
        if not owner_registry:
            owner_registry_address = input("Enter OwnerRegistry address: ").strip()
            owner_registry = project.OwnerRegistry.at(owner_registry_address)
        update_l2_relay_with_l3_contract(deployer, l2_relay, owner_registry)
    
    print("\n=== Deployment Complete ===")
    print("Contract addresses have been saved to the configuration file")
    print("Make sure to save these addresses for your application")

if __name__ == "__main__":
    main()