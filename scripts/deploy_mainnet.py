from ape import accounts, project, networks
from ape_accounts import import_account_from_private_key
from pathlib import Path
from dotenv import load_dotenv
import os
import sys
import time
from datetime import datetime
from web3 import Web3
from decimal import Decimal

# Import contract config writer utility
sys.path.append(str(Path(__file__).parent))
from contract_config_writer import get_contract_address, update_contract_address

# Alias addition constant
ALIAS_ADDITION = "0x1111000000000000000000000000000000001111"

ANIMECHAIN_CONFIG = {
    "name": "animechain",
    "chain_id": 69000,
    "rpc_url": "[invalid url, do not cite]"
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
        # Use a higher multiplier (1.5 instead of 1.1) for a larger buffer
        max_fee_per_gas = int(base_fee * 1.5)
        
        # Ensure minimum buffer of at least 1 gwei over base fee
        min_buffer = int(1e9)  # 1 Gwei
        if max_fee_per_gas - base_fee < min_buffer:
            max_fee_per_gas = base_fee + min_buffer
            
        print(f"Current base fee: {base_fee} wei")
        print(f"Setting maxFeePerGas to: {max_fee_per_gas} wei (buffer: {max_fee_per_gas - base_fee} wei)")
        
        # Increase priority fee to 5 Gwei for faster inclusion
        max_priority_fee = int(5e9)  # 5 Gwei
        return {
            "max_fee": max_fee_per_gas,
            "max_priority_fee": max_priority_fee
        }
    else:
        print("EIP-1559 not supported on this network, using default gas settings")
        
        # For networks without EIP-1559, provide explicit gas price with 50% buffer
        try:
            gas_price = provider.gas_price
            buffered_gas_price = int(gas_price * 1.5)
            print(f"Using gas price: {buffered_gas_price} wei (network: {gas_price} wei)")
            return {"gas_price": buffered_gas_price}
        except:
            # If gas price can't be fetched, return empty dict (default settings)
            return {}

def deploy_l1_query_owner(deployer, network_type="mainnet"):
    print("\n--- L1QueryOwnership Setup ---")
    
    l1_network = "ethereum:mainnet:alchemy"
    inbox_address = "0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f"  # Mainnet Inbox
    
    existing_l1_address = get_contract_address(network_type, "l1")
    if existing_l1_address:
        print(f"Found existing L1QueryOwnership in config: {existing_l1_address}")
        use_existing = input("Use existing L1QueryOwnership? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.L1QueryOwnership.at(existing_l1_address)
    
    print(f"Deploying new L1QueryOwnership on {l1_network}...")
    
    with networks.parse_network_choice(l1_network) as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 1}
        deploy_kwargs.update(gas_params)
        l1_contract = deployer.deploy(project.L1QueryOwnership, inbox_address, **deploy_kwargs)
        print(f"L1QueryOwnership deployed at: {l1_contract.address}")
        update_contract_address(network_type, "l1", l1_contract.address, "L1QueryOwnership")
        return l1_contract

def deploy_l2_relay(deployer, network_type="mainnet"):
    print("\n--- L2OwnershipRelay Setup ---")
    
    existing_l2_address = get_contract_address(network_type, "l2")
    if existing_l2_address:
        print(f"Found existing L2OwnershipRelay in config: {existing_l2_address}")
        use_existing = input("Use existing L2OwnershipRelay? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.L2OwnershipRelay.at(existing_l2_address)
    
    print("Deploying new L2OwnershipRelay on Arbitrum Mainnet...")
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 1}
        deploy_kwargs.update(gas_params)
        l2_relay = deployer.deploy(project.L2OwnershipRelay, **deploy_kwargs)
        print(f"L2OwnershipRelay deployed at: {l2_relay.address}")
        update_contract_address(network_type, "l2", l2_relay.address, "L2OwnershipRelay")
        return l2_relay

def deploy_art_piece_stencil(deployer, network_type="mainnet"):
    print("\n--- ArtPiece Stencil Setup ---")
    
    existing_art_piece_address = get_contract_address(network_type, "artPiece")
    if existing_art_piece_address:
        print(f"Found existing ArtPiece stencil in config: {existing_art_piece_address}")
        use_existing = input("Use existing ArtPiece stencil? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ArtPiece.at(existing_art_piece_address)
    
    print("Deploying new ArtPiece Stencil on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        
        # Deploy with empty constructor
        art_piece_stencil = deployer.deploy(
            project.ArtPiece,
            **deploy_kwargs
        )
        
        print(f"ArtPiece Stencil deployed at: {art_piece_stencil.address}")
        update_contract_address(network_type, "artPiece", art_piece_stencil.address, "ArtPiece")
        
        print("=" * 50)  # Delimiter after ArtPiece stencil deployment
        print("ArtPiece stencil deployment completed")
        print("=" * 50)
        
        return art_piece_stencil

def deploy_commission_hub_template(deployer, network_type="mainnet"):
    print("\n--- ArtCommissionHub Template Setup ---")
    
    existing_hub_address = get_contract_address(network_type, "artCommissionHub")
    if existing_hub_address:
        print(f"Found existing ArtCommissionHub template in config: {existing_hub_address}")
        use_existing = input("Use existing ArtCommissionHub template? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ArtCommissionHub.at(existing_hub_address)
    
    print("Deploying new ArtCommissionHub Template on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        commission_hub_template = deployer.deploy(project.ArtCommissionHub, **deploy_kwargs)
        print(f"ArtCommissionHub Template deployed at: {commission_hub_template.address}")
        print(f"Note: This ArtCommissionHub template is ONLY for reference in ArtCommissionHubOwners")
        print(f"      Actual ArtCommissionHub instances will be created through ArtCommissionHubOwners")
        
        update_contract_address(network_type, "artCommissionHub", commission_hub_template.address, "ArtCommissionHub")
        
        print("=" * 50)  # Delimiter after ArtCommissionHub template deployment
        print("ArtCommissionHub template deployment completed")
        print("=" * 50)
        
        return commission_hub_template

def deploy_profile_template(deployer, network_type="mainnet"):
    print("\n--- Profile Template Setup ---")
    
    existing_profile_template_address = get_contract_address(network_type, "profileTemplate")
    if existing_profile_template_address:
        print(f"Found existing Profile template in config: {existing_profile_template_address}")
        use_existing = input("Use existing Profile template? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.Profile.at(existing_profile_template_address)
    
    print("Deploying new Profile template on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        
        # Deploy profile template with correct constructor
        profile_template = deployer.deploy(project.Profile, **deploy_kwargs)
        print(f"Profile template deployed at: {profile_template.address}")
        
        # Update the contract address in the configuration
        update_contract_address(network_type, "profileTemplate", profile_template.address, "Profile")
        
        print("=" * 50)  # Delimiter after Profile template deployment
        print("Profile template deployment completed")
        print("=" * 50)
        
        return profile_template

def deploy_profile_social_template(deployer, network_type="mainnet"):
    print("\n--- ProfileSocial Template Setup ---")
    
    existing_profile_social_template_address = get_contract_address(network_type, "profileSocialTemplate")
    if existing_profile_social_template_address:
        print(f"Found existing ProfileSocial template in config: {existing_profile_social_template_address}")
        use_existing = input("Use existing ProfileSocial template? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ProfileSocial.at(existing_profile_social_template_address)
    
    print("Deploying new ProfileSocial template on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        
        # Deploy profile social template
        profile_social_template = deployer.deploy(project.ProfileSocial, **deploy_kwargs)
        print(f"ProfileSocial template deployed at: {profile_social_template.address}")
        
        # Update the contract address in the configuration
        update_contract_address(network_type, "profileSocialTemplate", profile_social_template.address, "ProfileSocial")
        
        print("=" * 50)  # Delimiter after ProfileSocial template deployment
        print("ProfileSocial template deployment completed")
        print("=" * 50)
        
        return profile_social_template

def deploy_art_edition_1155_template(deployer, network_type="mainnet"):
    print("\n--- ArtEdition1155 Template Setup ---")
    
    existing_art_edition_1155_template_address = get_contract_address(network_type, "artEdition1155Template")
    if existing_art_edition_1155_template_address:
        print(f"Found existing ArtEdition1155 template in config: {existing_art_edition_1155_template_address}")
        use_existing = input("Use existing ArtEdition1155 template? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ArtEdition1155.at(existing_art_edition_1155_template_address)
    
    print("Deploying new ArtEdition1155 template on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        
        # Deploy ArtEdition1155 template
        art_edition_1155_template = deployer.deploy(project.ArtEdition1155, **deploy_kwargs)
        print(f"ArtEdition1155 template deployed at: {art_edition_1155_template.address}")
        
        # Update the contract address in the configuration
        update_contract_address(network_type, "artEdition1155Template", art_edition_1155_template.address, "ArtEdition1155")
        
        print("=" * 50)  # Delimiter after ArtEdition1155 template deployment
        print("ArtEdition1155 template deployment completed")
        print("=" * 50)
        
        return art_edition_1155_template

def deploy_art_sales_1155_template(deployer, network_type="mainnet"):
    print("\n--- ArtSales1155 Template Setup ---")
    
    existing_art_sales_1155_template_address = get_contract_address(network_type, "artSales1155Template")
    if existing_art_sales_1155_template_address:
        print(f"Found existing ArtSales1155 template in config: {existing_art_sales_1155_template_address}")
        use_existing = input("Use existing ArtSales1155 template? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ArtSales1155.at(existing_art_sales_1155_template_address)
    
    print("Deploying new ArtSales1155 template on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        
        # Deploy ArtSales1155 template
        art_sales_1155_template = deployer.deploy(project.ArtSales1155, **deploy_kwargs)
        print(f"ArtSales1155 template deployed at: {art_sales_1155_template.address}")
        
        # Update the contract address in the configuration
        update_contract_address(network_type, "artSales1155Template", art_sales_1155_template.address, "ArtSales1155")
        
        print("=" * 50)  # Delimiter after ArtSales1155 template deployment
        print("ArtSales1155 template deployment completed")
        print("=" * 50)
        
        return art_sales_1155_template

def deploy_profile_factory_and_registry(deployer, profile_template_address, profile_social_template_address, commission_hub_template_address, art_edition_1155_template_address, art_sales_1155_template_address, network_type="mainnet"):
    print("\n--- ProfileFactoryAndRegistry Setup ---")
    
    existing_profile_factory_and_registry_address = get_contract_address(network_type, "profileFactoryAndRegistry")
    if existing_profile_factory_and_registry_address:
        print(f"Found existing ProfileFactoryAndRegistry in config: {existing_profile_factory_and_registry_address}")
        use_existing = input("Use existing ProfileFactoryAndRegistry? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ProfileFactoryAndRegistry.at(existing_profile_factory_and_registry_address)
    
    print("Deploying new ProfileFactoryAndRegistry on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        profile_factory_and_registry = deployer.deploy(
            project.ProfileFactoryAndRegistry, 
            profile_template_address,  # Profile template address
            profile_social_template_address,  # ProfileSocial template address
            commission_hub_template_address,  # ArtCommissionHub template address
            art_edition_1155_template_address,  # ArtEdition1155 template address
            art_sales_1155_template_address,  # ArtSales1155 template address
            **deploy_kwargs
        )
        print(f"ProfileFactoryAndRegistry deployed at: {profile_factory_and_registry.address}")
        
        # Update the contract address in the configuration
        update_contract_address(network_type, "profileFactoryAndRegistry", profile_factory_and_registry.address, "ProfileFactoryAndRegistry")
        
        print("=" * 50)  # Delimiter after ProfileFactoryAndRegistry deployment
        print("ProfileFactoryAndRegistry deployment completed")
        print("=" * 50)
        
        return profile_factory_and_registry

def deploy_art_commission_hub_owners(deployer, l2_relay_address, commission_hub_template_address, art_piece_stencil_address, network_type="mainnet"):
    print("\n--- ArtCommissionHubOwners Setup ---")
    
    existing_l3_address = get_contract_address(network_type, "l3")
    if existing_l3_address:
        print(f"Found existing ArtCommissionHubOwners in config: {existing_l3_address}")
        use_existing = input("Use existing ArtCommissionHubOwners? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ArtCommissionHubOwners.at(existing_l3_address)
    
    # Validate all required parameters
    if not l2_relay_address or l2_relay_address.strip() == "":
        raise ValueError("L2 relay address is required but was empty")
    if not commission_hub_template_address or commission_hub_template_address.strip() == "":
        raise ValueError("ArtCommissionHub template address is required but was empty")
    if not art_piece_stencil_address or art_piece_stencil_address.strip() == "":
        raise ValueError("ArtPiece stencil address is required but was empty")
    
    # Validate address format
    def is_valid_address(addr):
        return addr and len(addr) == 42 and addr.startswith('0x')
    
    if not is_valid_address(l2_relay_address):
        raise ValueError(f"L2 relay address is not a valid Ethereum address: '{l2_relay_address}' (should be 42 characters starting with 0x)")
    if not is_valid_address(commission_hub_template_address):
        raise ValueError(f"ArtCommissionHub template address is not a valid Ethereum address: '{commission_hub_template_address}' (should be 42 characters starting with 0x)")
    if not is_valid_address(art_piece_stencil_address):
        raise ValueError(f"ArtPiece stencil address is not a valid Ethereum address: '{art_piece_stencil_address}' (should be 42 characters starting with 0x)")
    
    print("Deploying new ArtCommissionHubOwners on Animechain L3...")
    print(f"ArtCommissionHubOwners will be owned by: {deployer.address}")
    print(f"Constructor parameters:")
    print(f"  - L2 Relay Address: {l2_relay_address}")
    print(f"  - Commission Hub Template Address: {commission_hub_template_address}")
    print(f"  - Art Piece Stencil Address: {art_piece_stencil_address}")
    
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        art_commission_hub_owners = deployer.deploy(
            project.ArtCommissionHubOwners, 
            l2_relay_address, 
            commission_hub_template_address,
            art_piece_stencil_address,  # Now includes art piece stencil address
            **deploy_kwargs
        )
        print(f"ArtCommissionHubOwners deployed at: {art_commission_hub_owners.address}")
        update_contract_address(network_type, "l3", art_commission_hub_owners.address, "ArtCommissionHubOwners")
        
        print("=" * 50)  # Delimiter after ArtCommissionHubOwners deployment
        print("ArtCommissionHubOwners deployment completed")
        print("=" * 50)
        
        return art_commission_hub_owners

def update_l2_relay_with_l3_contract(deployer, l2_relay, art_commission_hub_owners):
    print("\n--- Updating L2OwnershipRelay with L3 ArtCommissionHubOwners Address ---")
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        print(f"Updating L2OwnershipRelay with L3 ArtCommissionHubOwners address: {art_commission_hub_owners.address}")
        try:
            # Check the owner of the L2OwnershipRelay contract
            current_owner = l2_relay.owner()
            print(f"L2OwnershipRelay contract owner: {current_owner}")
            print(f"Deployer address: {deployer.address}")
            
            if current_owner != deployer.address:
                print(f"WARNING: Deployer address does not match L2OwnershipRelay owner!")
                print(f"This might be due to network connection issues or contract state not being properly synced.")
                print(f"Attempting to continue anyway...")
            
            gas_params = get_optimized_gas_params(provider)
            tx_kwargs = {}
            tx_kwargs.update(gas_params)
            print(f"Using transaction parameters: {tx_kwargs}")
            tx = l2_relay.setL3Contract(art_commission_hub_owners.address, sender=deployer, **tx_kwargs)
            print("L2OwnershipRelay successfully updated with L3 ArtCommissionHubOwners address")
        except Exception as e:
            print(f"Error updating L2OwnershipRelay with L3 ArtCommissionHubOwners address: {e}")
            print(f"Debug: Try manually checking the owner of the L2OwnershipRelay contract")
            
            # Try getting more debugging information
            try:
                current_owner = l2_relay.owner()
                print(f"L2OwnershipRelay contract owner: {current_owner}")
                print(f"Deployer address: {deployer.address}")
                
                if current_owner != deployer.address:
                    print(f"ISSUE IDENTIFIED: Deployer is not registered as the owner of L2OwnershipRelay.")
                    print(f"If this is unexpected, it might be due to network state inconsistency.")
                    print(f"You may need to wait for transactions to be confirmed and try again.")
                    
                    # Check if we're in the same network context as the deployment
                    print(f"Current network: {provider.network.name}")
                    print(f"Please verify that you're connected to the same network where the contract was deployed.")
            except Exception as debug_error:
                print(f"Could not get debugging information: {debug_error}")
            
            print(f"Please manually set the L3 contract address on L2OwnershipRelay later using:")
            print(f"L2OwnershipRelay.setL3Contract({art_commission_hub_owners.address})")
            
            # Ask if the user wants to retry
            if input("Do you want to retry updating the L3 contract address? (y/n): ").strip().lower() == 'y':
                try:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                    tx = l2_relay.setL3Contract(art_commission_hub_owners.address, sender=deployer, **tx_kwargs)
                    print(f"L2OwnershipRelay successfully updated with L3 ArtCommissionHubOwners address on retry")
                except Exception as retry_error:
                    print(f"Error on retry: {retry_error}")
                    print(f"You will need to manually set the L3 contract address later.")

def main():
    print("=" * 60)
    print("MAINNET DEPLOYMENT")
    print("=" * 60)
    print("L1: Ethereum Mainnet")
    print("L2: Arbitrum Mainnet") 
    print("L3: Animechain Mainnet")
    print("=" * 60)
    
    deploy_mode = input("Enter deployment mode (full, l2only, l3only): ").strip().lower()
    
    # Determine network type based on deployment mode
    if deploy_mode == "l2only":
        network_type = "testnet"  # l2only overwrites testnet addresses
        print("L2 deployment mode: Will overwrite testnet configuration addresses")
    else:
        network_type = "mainnet"  # l3only and full overwrite mainnet addresses
        print(f"Deployment mode '{deploy_mode}': Will overwrite mainnet configuration addresses")
    
    # Check if the user wants to do a full redeployment
    full_redeploy = input("Do a full redeployment? (y/N): ").strip().lower() == 'y'
    
    deployer = setup_deployer()
    
    l1_contract = None
    l2_relay = None
    art_commission_hub_owners = None
    commission_hub_template = None
    art_piece_stencil = None
    profile_template = None
    profile_social_template = None
    art_edition_1155_template = None
    art_sales_1155_template = None
    profile_factory_and_registry = None
    
    if deploy_mode == "full":
        # Deploy ArtPiece stencil first
        art_piece_stencil = deploy_art_piece_stencil(deployer, network_type)
        
        # Deploy all template contracts
        profile_template = deploy_profile_template(deployer, network_type)
        profile_social_template = deploy_profile_social_template(deployer, network_type)
        art_edition_1155_template = deploy_art_edition_1155_template(deployer, network_type)
        art_sales_1155_template = deploy_art_sales_1155_template(deployer, network_type)
        commission_hub_template = deploy_commission_hub_template(deployer, network_type)
        
        # Deploy ProfileFactoryAndRegistry with all five template addresses
        profile_factory_and_registry = deploy_profile_factory_and_registry(
            deployer, 
            profile_template.address, 
            profile_social_template.address,
            commission_hub_template.address,
            art_edition_1155_template.address,
            art_sales_1155_template.address,
            network_type
        )
        
        l1_contract = deploy_l1_query_owner(deployer, network_type)
        l2_relay = deploy_l2_relay(deployer, network_type)
        
        art_commission_hub_owners = deploy_art_commission_hub_owners(
            deployer, 
            l2_relay.address, 
            commission_hub_template.address,
            art_piece_stencil.address,
            network_type
        )
        update_l2_relay_with_l3_contract(deployer, l2_relay, art_commission_hub_owners)
        
        # CRITICAL: Establish bidirectional connection between ArtCommissionHubOwners and ProfileFactoryAndRegistry
        print("\n=== Setting up bidirectional connection between contracts ===")
        print(f"Connecting ArtCommissionHubOwners ({art_commission_hub_owners.address}) to ProfileFactoryAndRegistry ({profile_factory_and_registry.address})")
        with networks.parse_network_choice("ethereum:animechain") as provider:
            gas_params = get_optimized_gas_params(provider)
            tx_kwargs = {}
            tx_kwargs.update(gas_params)
            try:
                # This call is critical - it sets up the bidirectional connection
                # Without it, commission hubs won't be automatically linked to profiles
                tx = art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory_and_registry.address, sender=deployer, **tx_kwargs)
                print(f"Bidirectional connection established successfully")
                
                # Verify the connection
                registry_from_factory = profile_factory_and_registry.artCommissionHubOwners()
                factory_from_registry = art_commission_hub_owners.profileFactoryAndRegistry()
                print(f"Verification: ProfileFactoryAndRegistry points to: {registry_from_factory}")
                print(f"Verification: ArtCommissionHubOwners points to: {factory_from_registry}")
                
                if registry_from_factory != art_commission_hub_owners.address:
                    print(f"WARNING: Verification failed - ProfileFactoryAndRegistry not pointing to ArtCommissionHubOwners")
                if factory_from_registry != profile_factory_and_registry.address:
                    print(f"WARNING: Verification failed - ArtCommissionHubOwners not pointing to ProfileFactoryAndRegistry")
            except Exception as e:
                print(f"Error establishing bidirectional connection: {e}")
                print(f"CRITICAL: You must manually call linkProfileFactoryAndRegistry later using:")
                print(f"ArtCommissionHubOwners.linkProfileFactoryAndRegistry({profile_factory_and_registry.address})")
                print(f"Without this connection, commission hubs won't be linked to user profiles automatically")
        
        # Register L1 contract in L2OwnershipRelay
        with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
            gas_params = get_optimized_gas_params(provider)
            tx_kwargs = {}
            tx_kwargs.update(gas_params)
            l1_chain_id = 1  # For mainnet
            # Create aliased L1 address
            l1_address_int = int(l1_contract.address, 16)
            alias_addition_int = int(ALIAS_ADDITION, 16)
            aliased_l1_address = "0x" + hex(l1_address_int + alias_addition_int)[2:].zfill(40)
            print(f"Registering L1QueryOwnership ({aliased_l1_address}) for chain ID {l1_chain_id} in L2OwnershipRelay")
            try:
                tx = l2_relay.updateCrossChainQueryOwnerContract(
                    aliased_l1_address,
                    l1_chain_id,
                    sender=deployer,
                    **tx_kwargs
                )
                print(f"L1QueryOwnership successfully registered in L2OwnershipRelay for chain ID {l1_chain_id}")
            except Exception as e:
                print(f"Error registering L1QueryOwnership in L2OwnershipRelay: {e}")
                print(f"You will need to manually register L1QueryOwnership later using:")
                print(f"L2OwnershipRelay.updateCrossChainQueryOwnerContract({aliased_l1_address}, {l1_chain_id})")
    
    elif deploy_mode == "l2only":
        l2_relay = deploy_l2_relay(deployer, network_type)
    
    elif deploy_mode == "l3only":
        # Deploy ArtPiece stencil first
        art_piece_stencil = deploy_art_piece_stencil(deployer, network_type)
        
        # Deploy all template contracts
        profile_template = deploy_profile_template(deployer, network_type)
        profile_social_template = deploy_profile_social_template(deployer, network_type)
        art_edition_1155_template = deploy_art_edition_1155_template(deployer, network_type)
        art_sales_1155_template = deploy_art_sales_1155_template(deployer, network_type)
        commission_hub_template = deploy_commission_hub_template(deployer, network_type)
        
        # Deploy ProfileFactoryAndRegistry with all five template addresses
        profile_factory_and_registry = deploy_profile_factory_and_registry(
            deployer,
            profile_template.address,
            profile_social_template.address,
            commission_hub_template.address,
            art_edition_1155_template.address,
            art_sales_1155_template.address,
            network_type
        )
        
        # Get L2 relay address
        l2_address = get_contract_address(network_type, "l2")
        if l2_address:
            use_existing = input(f"Use existing L2OwnershipRelay at {l2_address}? (y/n) [y]: ").strip().lower() or "y"
            if use_existing != "y":
                l2_address = input("Enter L2 relay address (42 characters starting with 0x): ").strip()
                if not l2_address:
                    raise ValueError("L2 relay address is required for ArtCommissionHubOwners deployment")
                # Add 0x prefix if missing
                if not l2_address.startswith('0x') and len(l2_address) == 40:
                    l2_address = '0x' + l2_address
                    print(f"Added 0x prefix: {l2_address}")
        else:
            l2_address = input("Enter L2 relay address (42 characters starting with 0x): ").strip()
            if not l2_address:
                raise ValueError("L2 relay address is required for ArtCommissionHubOwners deployment")
            # Add 0x prefix if missing
            if not l2_address.startswith('0x') and len(l2_address) == 40:
                l2_address = '0x' + l2_address
                print(f"Added 0x prefix: {l2_address}")
        
        print(f"Using L2 relay address: {l2_address}")
        print(f"ArtCommissionHub template address: {commission_hub_template.address}")
        print(f"ArtPiece stencil address: {art_piece_stencil.address}")
            
        art_commission_hub_owners = deploy_art_commission_hub_owners(
            deployer, 
            l2_address, 
            commission_hub_template.address,
            art_piece_stencil.address,
            network_type
        )
        
        # CRITICAL: Establish bidirectional connection between ArtCommissionHubOwners and ProfileFactoryAndRegistry
        if profile_factory_and_registry and art_commission_hub_owners:
            print("\n=== Setting up bidirectional connection between contracts ===")
            print(f"Connecting ArtCommissionHubOwners ({art_commission_hub_owners.address}) to ProfileFactoryAndRegistry ({profile_factory_and_registry.address})")
            with networks.parse_network_choice("ethereum:animechain") as provider:
                gas_params = get_optimized_gas_params(provider)
                tx_kwargs = {}
                tx_kwargs.update(gas_params)
                try:
                    # This call is critical - it sets up the bidirectional connection
                    # Without it, commission hubs won't be automatically linked to profiles
                    tx = art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory_and_registry.address, sender=deployer, **tx_kwargs)
                    print(f"Bidirectional connection established successfully")
                    
                    # Verify the connection
                    registry_from_factory = profile_factory_and_registry.artCommissionHubOwners()
                    factory_from_registry = art_commission_hub_owners.profileFactoryAndRegistry()
                    print(f"Verification: ProfileFactoryAndRegistry points to: {registry_from_factory}")
                    print(f"Verification: ArtCommissionHubOwners points to: {factory_from_registry}")
                    
                    if registry_from_factory != art_commission_hub_owners.address:
                        print(f"WARNING: Verification failed - ProfileFactoryAndRegistry not pointing to ArtCommissionHubOwners")
                    if factory_from_registry != profile_factory_and_registry.address:
                        print(f"WARNING: Verification failed - ArtCommissionHubOwners not pointing to ProfileFactoryAndRegistry")
                except Exception as e:
                    print(f"Error establishing bidirectional connection: {e}")
                    print(f"CRITICAL: You must manually call linkProfileFactoryAndRegistry later using:")
                    print(f"ArtCommissionHubOwners.linkProfileFactoryAndRegistry({profile_factory_and_registry.address})")
                    print(f"Without this connection, commission hubs won't be linked to user profiles automatically")
    
    # Optional L2 relay update for non-full deployments
    if deploy_mode != "full" and input("Update L2OwnershipRelay with L3 ArtCommissionHubOwners address? (y/n): ").strip().lower() == 'y':
        if not l2_relay:
            l2_address = input("Enter L2OwnershipRelay address: ").strip()
            l2_relay = project.L2OwnershipRelay.at(l2_address)
        if not art_commission_hub_owners:
            art_commission_hub_owners_address = input("Enter ArtCommissionHubOwners address: ").strip()
            art_commission_hub_owners = project.ArtCommissionHubOwners.at(art_commission_hub_owners_address)
        update_l2_relay_with_l3_contract(deployer, l2_relay, art_commission_hub_owners)
    
    # Print deployment summary
    print(f"\n=== MAINNET DEPLOYMENT SUMMARY (network_type: {network_type}) ===")
    print(f"L1 Contract (Ethereum Mainnet): {l1_contract.address if l1_contract else 'Not deployed'}")
    print(f"L2 Contract (Arbitrum Mainnet): {l2_relay.address if l2_relay else 'Not deployed'}")
    print(f"L3 Contracts (Animechain Mainnet):")
    print(f"  - ArtCommissionHubOwners: {art_commission_hub_owners.address if art_commission_hub_owners else 'Not deployed'}")
    print(f"  - ArtCommissionHub Template: {commission_hub_template.address if commission_hub_template else 'Not deployed'}")
    print(f"  - ArtPiece Stencil: {art_piece_stencil.address if art_piece_stencil else 'Not deployed'}")
    print(f"  - Profile Template: {profile_template.address if profile_template else 'Not deployed'}")
    print(f"  - ProfileSocial Template: {profile_social_template.address if profile_social_template else 'Not deployed'}")
    print(f"  - ArtEdition1155 Template: {art_edition_1155_template.address if art_edition_1155_template else 'Not deployed'}")
    print(f"  - ArtSales1155 Template: {art_sales_1155_template.address if art_sales_1155_template else 'Not deployed'}")
    print(f"  - ProfileFactoryAndRegistry: {profile_factory_and_registry.address if profile_factory_and_registry else 'Not deployed'}")
    print("\nNOTE: These are MAINNET contracts deployed to PRODUCTION networks.")
    print("They handle real assets and transactions.")
    
    # Check contract links
    if l2_relay:
        try:
            l3_contract = l2_relay.l3Contract()
            print(f"\nContract Links:")
            print(f"  - L2OwnershipRelay -> ArtCommissionHubOwners: {l3_contract}")
            
            # Check registered L1 contracts by chain
            if l1_contract:
                try:
                    l1_chain_id = 1  # Mainnet
                    l1_registered = l2_relay.crossChainRegistryAddressByChainId(l1_chain_id)
                    print(f"  - L2OwnershipRelay -> L1QueryOwnership for chain {l1_chain_id}: {l1_registered}")
                except Exception as e:
                    print(f"Could not retrieve L1 registration info: {e}")
        except Exception as e:
            print(f"Could not retrieve contract links: {e}")
    
    if art_commission_hub_owners:
        try:
            l2relay = art_commission_hub_owners.l2OwnershipRelay()
            hub_template = art_commission_hub_owners.artCommissionHubTemplate()
            print(f"  - ArtCommissionHubOwners -> L2OwnershipRelay: {l2relay}")
            print(f"  - ArtCommissionHubOwners -> ArtCommissionHub Template: {hub_template}")
        except Exception as e:
            print(f"Could not retrieve ArtCommissionHubOwners links: {e}")
    
    print(f"\nFrontend configuration has been updated for network: {network_type}")
    print("\nMAINNET DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print("All contracts are deployed to their respective mainnet networks.")
    
    # Run compile_and_extract_abis script to update ABIs
    update_abis = input("Update ABIs now? (y/n) [y]: ").strip().lower() 
    if update_abis == "" or update_abis == "y":
        print("\nCompiling contracts and extracting ABIs...")
        # Import the function here to avoid circular imports
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent))
        try:
            from compile_and_extract_abis import extract_abis_to_folder
            extract_abis_to_folder()
            print("Successfully updated ABIs")
        except Exception as e:
            print(f"Error updating ABIs: {str(e)}")
    
    print("Make sure to save these addresses for your application")
    print(f"\nPlease run: ape run compile_and_extract_abis\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDeployment canceled by user.")
    except Exception as e:
        print(f"\nUnexpected error during deployment: {e}")
        import traceback
        traceback.print_exc()