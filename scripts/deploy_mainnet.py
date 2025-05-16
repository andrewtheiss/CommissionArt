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
    print("\n--- L2RelayOwnership Setup ---")
    
    existing_l2_address = get_contract_address(network_type, "l2")
    if existing_l2_address:
        print(f"Found existing L2RelayOwnership in config: {existing_l2_address}")
        use_existing = input("Use existing L2RelayOwnership? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.L2RelayOwnership.at(existing_l2_address)
    
    print("Deploying new L2RelayOwnership on Arbitrum Mainnet...")
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 1}
        deploy_kwargs.update(gas_params)
        l2_relay = deployer.deploy(project.L2RelayOwnership, **deploy_kwargs)
        print(f"L2RelayOwnership deployed at: {l2_relay.address}")
        update_contract_address(network_type, "l2", l2_relay.address, "L2RelayOwnership")
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
        return art_piece_stencil

def deploy_commission_hub_template(deployer, art_piece_stencil_address=None, network_type="mainnet"):
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
        update_contract_address(network_type, "artCommissionHub", commission_hub_template.address, "ArtCommissionHub")
        
        # Whitelist the ArtPiece stencil if provided
        if art_piece_stencil_address:
            print(f"Whitelisting ArtPiece stencil ({art_piece_stencil_address}) in ArtCommissionHub...")
            tx_kwargs = {}
            tx_kwargs.update(gas_params)
            tx = commission_hub_template.setWhitelistedArtPieceContract(
                art_piece_stencil_address, 
                sender=deployer,
                **tx_kwargs
            )
            print(f"ArtPiece stencil whitelisted in ArtCommissionHub")
            
        return commission_hub_template

def deploy_art_collection_ownership_registry(deployer, l2_relay_address, commission_hub_template_address, network_type="mainnet"):
    print("\n--- ArtCommissionHubOwners Setup ---")
    
    existing_l3_address = get_contract_address(network_type, "l3")
    if existing_l3_address:
        print(f"Found existing ArtCommissionHubOwners in config: {existing_l3_address}")
        use_existing = input("Use existing ArtCommissionHubOwners? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ArtCommissionHubOwners.at(existing_l3_address)
    
    print("Deploying new ArtCommissionHubOwners on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        art_collection_ownership_registry = deployer.deploy(project.ArtCommissionHubOwners, l2_relay_address, commission_hub_template_address, **deploy_kwargs)
        print(f"ArtCommissionHubOwners deployed at: {art_collection_ownership_registry.address}")
        update_contract_address(network_type, "l3", art_collection_ownership_registry.address, "ArtCommissionHubOwners")
        return art_collection_ownership_registry

def update_l2_relay_with_l3_contract(deployer, l2_relay, art_collection_ownership_registry):
    print("\n--- Updating L2RelayOwnership with L3 ArtCommissionHubOwners Address ---")
    with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
        gas_params = get_optimized_gas_params(provider)
        tx_kwargs = {}
        tx_kwargs.update(gas_params)
        print(f"Using transaction parameters: {tx_kwargs}")
        tx = l2_relay.setL3Contract(art_collection_ownership_registry.address, sender=deployer, **tx_kwargs)
        print("L2RelayOwnership successfully updated with L3 ArtCommissionHubOwners address")

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
        print(f"Updated profileTemplate address in configuration")
        
        return profile_template

def deploy_profile_factory_and_regsitry(deployer, profile_template_address, network_type="mainnet"):
    print("\n--- ProfileFactoryAndRegistry Setup ---")
    
    existing_profile_factory_and_regsitry_address = get_contract_address(network_type, "profileFactoryAndRegistry")
    if existing_profile_factory_and_regsitry_address:
        print(f"Found existing ProfileFactoryAndRegistry in config: {existing_profile_factory_and_regsitry_address}")
        use_existing = input("Use existing ProfileFactoryAndRegistry? (y/n) [y]: ").strip().lower() or "y"
        if use_existing == "y":
            return project.ProfileFactoryAndRegistry.at(existing_profile_factory_and_regsitry_address)
    
    print("Deploying new ProfileFactoryAndRegistry on Animechain L3...")
    with networks.parse_network_choice("ethereum:animechain") as provider:
        gas_params = get_optimized_gas_params(provider)
        deploy_kwargs = {"required_confirmations": 0}
        deploy_kwargs.update(gas_params)
        profile_factory_and_regsitry = deployer.deploy(project.ProfileFactoryAndRegistry, profile_template_address, **deploy_kwargs)
        print(f"ProfileFactoryAndRegistry deployed at: {profile_factory_and_regsitry.address}")
        
        # Update the contract address in the configuration
        update_contract_address(network_type, "profileFactoryAndRegistry", profile_factory_and_regsitry.address, "ProfileFactoryAndRegistry")
        print(f"Updated profileFactoryAndRegistry address in configuration")
        
        return profile_factory_and_regsitry

def main():
    network_type = "mainnet"  # Always use mainnet
    deploy_mode = input("Enter deployment mode (full, l2only, l3only): ").strip().lower()
    
    deployer = setup_deployer()
    
    l1_contract = None
    l2_relay = None
    art_collection_ownership_registry = None
    commission_hub_template = None
    art_piece_stencil = None
    profile_template = None
    profile_factory_and_regsitry = None
    
    if deploy_mode == "full":
        # Deploy ArtPiece stencil first
        art_piece_stencil = deploy_art_piece_stencil(deployer, network_type)
        
        # Deploy Profile template and ProfileFactoryAndRegistry
        profile_template = deploy_profile_template(deployer, network_type)
        profile_factory_and_regsitry = deploy_profile_factory_and_regsitry(deployer, profile_template.address, network_type)
        
        l1_contract = deploy_l1_query_owner(deployer, network_type)
        l2_relay = deploy_l2_relay(deployer, network_type)
        
        # Deploy ArtCommissionHub and whitelist the ArtPiece contract
        commission_hub_template = deploy_commission_hub_template(deployer, art_piece_stencil.address, network_type)
        
        art_collection_ownership_registry = deploy_art_collection_ownership_registry(deployer, l2_relay.address, commission_hub_template.address, network_type)
        update_l2_relay_with_l3_contract(deployer, l2_relay, art_collection_ownership_registry)
        
        # CRITICAL: Establish bidirectional connection between ArtCommissionHubOwners and ProfileFactoryAndRegistry
        print("\n--- Setting up bidirectional connection between contracts ---")
        with networks.parse_network_choice("ethereum:animechain") as provider:
            gas_params = get_optimized_gas_params(provider)
            tx_kwargs = {}
            tx_kwargs.update(gas_params)
            print(f"Connecting ArtCommissionHubOwners ({art_collection_ownership_registry.address}) to ProfileFactoryAndRegistry ({profile_factory_and_regsitry.address})")
            try:
                # This call is critical - it sets up the bidirectional connection
                # Without it, commission hubs won't be automatically linked to profiles
                tx = art_collection_ownership_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer, **tx_kwargs)
                print(f"Bidirectional connection established successfully")
                
                # Verify the connection
                registry_from_factory = profile_factory_and_regsitry.artCommissionHubOwners()
                factory_from_registry = art_collection_ownership_registry.profileFactoryAndRegistry()
                print(f"Verification: ProfileFactoryAndRegistry points to: {registry_from_factory}")
                print(f"Verification: ArtCommissionHubOwners points to: {factory_from_registry}")
                
                if registry_from_factory != art_collection_ownership_registry.address:
                    print(f"WARNING: Verification failed - ProfileFactoryAndRegistry not pointing to ArtCommissionHubOwners")
                if factory_from_registry != profile_factory_and_regsitry.address:
                    print(f"WARNING: Verification failed - ArtCommissionHubOwners not pointing to ProfileFactoryAndRegistry")
            except Exception as e:
                print(f"Error establishing bidirectional connection: {e}")
                print(f"CRITICAL: You must manually call setProfileFactoryAndRegistry later using:")
                print(f"ArtCommissionHubOwners.setProfileFactoryAndRegistry({profile_factory_and_regsitry.address})")
                print(f"Without this connection, commission hubs won't be linked to user profiles automatically")
        
        with networks.parse_network_choice(ARBITRUM_MAINNET_CONFIG["network"]) as provider:
            gas_params = get_optimized_gas_params(provider)
            tx_kwargs = {}
            tx_kwargs.update(gas_params)
            l1_chain_id = 1  # For mainnet
            # Create aliased L1 address
            l1_address_int = int(l1_contract.address, 16)
            alias_addition_int = int(ALIAS_ADDITION, 16)
            aliased_l1_address = "0x" + hex(l1_address_int + alias_addition_int)[2:].zfill(40)
            tx = l2_relay.updateCrossChainQueryOwnerContract(
                aliased_l1_address,
                l1_chain_id,
                sender=deployer,
                **tx_kwargs
            )
            print(f"Aliased L1QueryOwnership ({aliased_l1_address}) registered in L2RelayOwnership for chain ID {l1_chain_id}")
    
    elif deploy_mode == "l2only":
        l2_relay = deploy_l2_relay(deployer, network_type)
    
    elif deploy_mode == "l3only":
        # Deploy ArtPiece stencil first
        art_piece_stencil = deploy_art_piece_stencil(deployer, network_type)
        
        # Deploy Profile template and ProfileFactoryAndRegistry
        profile_template = deploy_profile_template(deployer, network_type)
        profile_factory_and_regsitry = deploy_profile_factory_and_regsitry(deployer, profile_template.address, network_type)
        
        # Deploy ArtCommissionHub and whitelist the ArtPiece contract
        commission_hub_template = deploy_commission_hub_template(deployer, art_piece_stencil.address, network_type)
        
        l2_address = get_contract_address(network_type, "l2")
        if l2_address:
            use_existing = input(f"Use existing L2RelayOwnership at {l2_address}? (y/n) [y]: ").strip().lower() or "y"
            if use_existing != "y":
                l2_address = input("Enter L2 relay address: ").strip()
        else:
            l2_address = input("Enter L2 relay address: ").strip()
        ch_address = commission_hub_template.address if commission_hub_template else get_contract_address(network_type, "artCommissionHub")
        if not ch_address:
            ch_address = input("Enter ArtCommissionHub template address: ").strip()
        art_collection_ownership_registry = deploy_art_collection_ownership_registry(deployer, l2_address, ch_address, network_type)
        
        # CRITICAL: Establish bidirectional connection between ArtCommissionHubOwners and ProfileFactoryAndRegistry
        if profile_factory_and_regsitry and art_collection_ownership_registry:
            print("\n--- Setting up bidirectional connection between contracts ---")
            with networks.parse_network_choice("ethereum:animechain") as provider:
                gas_params = get_optimized_gas_params(provider)
                tx_kwargs = {}
                tx_kwargs.update(gas_params)
                print(f"Connecting ArtCommissionHubOwners ({art_collection_ownership_registry.address}) to ProfileFactoryAndRegistry ({profile_factory_and_regsitry.address})")
                try:
                    # This call is critical - it sets up the bidirectional connection
                    # Without it, commission hubs won't be automatically linked to profiles
                    tx = art_collection_ownership_registry.setProfileFactoryAndRegistry(profile_factory_and_regsitry.address, sender=deployer, **tx_kwargs)
                    print(f"Bidirectional connection established successfully")
                    
                    # Verify the connection
                    registry_from_factory = profile_factory_and_regsitry.artCommissionHubOwners()
                    factory_from_registry = art_collection_ownership_registry.profileFactoryAndRegistry()
                    print(f"Verification: ProfileFactoryAndRegistry points to: {registry_from_factory}")
                    print(f"Verification: ArtCommissionHubOwners points to: {factory_from_registry}")
                    
                    if registry_from_factory != art_collection_ownership_registry.address:
                        print(f"WARNING: Verification failed - ProfileFactoryAndRegistry not pointing to ArtCommissionHubOwners")
                    if factory_from_registry != profile_factory_and_regsitry.address:
                        print(f"WARNING: Verification failed - ArtCommissionHubOwners not pointing to ProfileFactoryAndRegistry")
                except Exception as e:
                    print(f"Error establishing bidirectional connection: {e}")
                    print(f"CRITICAL: You must manually call setProfileFactoryAndRegistry later using:")
                    print(f"ArtCommissionHubOwners.setProfileFactoryAndRegistry({profile_factory_and_regsitry.address})")
                    print(f"Without this connection, commission hubs won't be linked to user profiles automatically")
    
    if deploy_mode != "full" and input("Update L2RelayOwnership with L3 ArtCommissionHubOwners address? (y/n): ").strip().lower() == 'y':
        if not l2_relay:
            l2_address = input("Enter L2RelayOwnership address: ").strip()
            l2_relay = project.L2RelayOwnership.at(l2_address)
        if not art_collection_ownership_registry:
            art_collection_ownership_registry_address = input("Enter ArtCommissionHubOwners address: ").strip()
            art_collection_ownership_registry = project.ArtCommissionHubOwners.at(art_collection_ownership_registry_address)
        update_l2_relay_with_l3_contract(deployer, l2_relay, art_collection_ownership_registry)
    
    print("\n=== Deployment Complete ===")
    print("Contract addresses have been saved to the configuration file")
    
    # Run compile_and_extract_abis script to update ABIs
    update_abis = input("Update ABIs now? (y/n) [y]: ").strip().lower() 
    if update_abis == "" or update_abis == "y":
        print("\nCompiling contracts and extracting ABIs...")
        # Import the function here to avoid circular imports
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent))
        from compile_and_extract_abis import extract_abis_to_folder
        try:
            extract_abis_to_folder()
            print("Successfully updated ABIs")
        except Exception as e:
            print(f"Error updating ABIs: {str(e)}")
    
    print("Make sure to save these addresses for your application")
    print(f"\nPlease run: ape run compile_and_extract_abis\n")

if __name__ == "__main__":
    main()