from ape import accounts, project, networks
from ape_accounts import import_account_from_private_key
from dotenv import load_dotenv
from pathlib import Path
import os
import time
from datetime import datetime
from .contract_config_writer import update_contract_address, get_contract_address, get_all_contracts, save_config
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
    network_choice = input("Enter network (local, testnet, prodtest, production): ").strip().lower()
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
    elif network_choice == "prodtest":
        l1_network = "ethereum:mainnet:alchemy"
        l2_network = "arbitrum:mainnet:alchemy"
        # Use real Animechain L3 for prodtest
        l3_network = "ethereum:custom"  # Animechain should be configured as a custom network
        config_network = "prodtest"  # New config category
        
        # Ensure the prodtest configuration exists by loading all contracts
        # and checking if we need to add the prodtest network
        config = get_all_contracts()
        if "prodtest" not in config["networks"]:
            # Copy the structure from testnet as a starting point
            config["networks"]["prodtest"] = {
                "l1": {"address": "", "contract": "L1QueryOwnership"},
                "l2": {"address": "", "contract": "L2OwnershipRelay"},
                "l3": {"address": "", "contract": "ArtCommissionHubOwners"},
                "artCommissionHub": {"address": "", "contract": "ArtCommissionHub"},
                "artPiece": {"address": "", "contract": "ArtPiece"},
                "profileTemplate": {"address": "", "contract": "Profile"},
                "profileSocialTemplate": {"address": "", "contract": "ProfileSocial"},
                "profileFactoryAndRegistry": {"address": "", "contract": "ProfileFactoryAndRegistry"}
            }
            # Save the updated config
            save_config(config)
            print("Added 'prodtest' network configuration")
            
        print("WARNING: Using PRODUCTION networks with test deployment!")
        print("This will deploy to real Ethereum, Arbitrum, and Animechain networks.")
        confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Deployment canceled.")
            sys.exit(0)
    elif network_choice == "production":
        l1_network = "ethereum:mainnet:alchemy"
        l2_network = "arbitrum:mainnet:alchemy"
        # For production, we'll use Animechain L3
        l3_network = "ethereum:custom"
        config_network = "mainnet"
    else:
        raise ValueError("Invalid network choice")

    # For production or prodtest, use Animechain L3
    if network_choice in ["production", "prodtest"]:
        print("Using Animechain L3 for deployment")
        # If this is prodtest, check if we have Animechain configured
        if network_choice == "prodtest":
            print("IMPORTANT: Make sure you have configured Animechain as a custom network in your ape-config.yaml")
            print("Configuration should include RPC URL, chain ID, and account settings")
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
        deployer = import_account_from_private_key("deployer", passphrase.encode('utf-8'), private_key)
    deployer.set_autosign(True, passphrase=passphrase.encode('utf-8'))

    # Check if the user wants to do a full redeployment
    # For prodtest, we default to reusing L1 but redeploying L2/L3
    if network_choice == "prodtest":
        full_redeploy = False
        redeploy_l2_l3 = input("Redeploy L2 and L3 contracts? (Y/n): ").strip().lower() != 'n'
    else:
        full_redeploy = input("Do a full redeployment? (y/N): ").strip().lower() == 'y'
        redeploy_l2_l3 = full_redeploy  # For other modes, this follows the full_redeploy choice
    
    # Get existing addresses from config
    l1_existing_address = get_contract_address(config_network, "l1")
    l2_existing_address = get_contract_address(config_network, "l2")
    l3_existing_address = get_contract_address(config_network, "l3")
    commission_hub_existing_address = get_contract_address(config_network, "artCommissionHub")
    art_piece_existing_address = get_contract_address(config_network, "artPiece")
    profile_template_existing_address = get_contract_address(config_network, "profileTemplate")
    profile_social_template_existing_address = get_contract_address(config_network, "profileSocialTemplate")
    profile_factory_and_registry_existing_address = get_contract_address(config_network, "profileFactoryAndRegistry")
    
    # For prodtest mode, if we don't have an L1 address, prompt for one
    if network_choice == "prodtest" and not l1_existing_address:
        l1_manual_address = input("Enter existing L1QueryOwnership address (leave empty to deploy new): ").strip()
        if l1_manual_address:
            l1_existing_address = l1_manual_address
            # Save this to config for future use
            update_contract_address(config_network, "l1", l1_existing_address, "L1QueryOwnership")
    
    # Track deployed contracts
    l1_contract = None
    l2_contract = None
    l3_art_commission_hub_owners = None
    commission_hub_template = None
    art_piece_stencil = None
    profile_template = None
    profile_social_template = None
    profile_factory_and_registry = None

    # Deploy L2OwnershipRelay first with 0 parameters
    with networks.parse_network_choice(l2_network) as provider:
        if not (full_redeploy or (network_choice == "prodtest" and redeploy_l2_l3)) and l2_existing_address and input(f"Use existing L2OwnershipRelay at {l2_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing L2OwnershipRelay at: {l2_existing_address}")
            l2_contract = project.L2OwnershipRelay.at(l2_existing_address)
        else:
            print(f"Deploying L2OwnershipRelay on {l2_network}")
            try:
                # For L2 deployments, we often need custom gas settings
                gas_limit = 3000000  # Higher gas limit for L2
                
                # Deploy L2OwnershipRelay with no parameters
                l2_contract = deployer.deploy(
                    project.L2OwnershipRelay,
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"L2OwnershipRelay deployed at: {l2_contract.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "l2", l2_contract.address, "L2OwnershipRelay")
                
                print("=" * 50)  # Delimiter after L2OwnershipRelay deployment
                print("L2OwnershipRelay deployment completed")
                print("=" * 50)
            except Exception as e:
                print(f"Error deploying L2OwnershipRelay: {e}")
                sys.exit(1)

    # Deploy ArtPiece stencil on L3
    with networks.parse_network_choice(l3_network) as provider:
        if not full_redeploy and art_piece_existing_address and input(f"Use existing ArtPiece stencil at {art_piece_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing ArtPiece stencil at: {art_piece_existing_address}")
            art_piece_stencil = project.ArtPiece.at(art_piece_existing_address)
        else:
            print(f"Deploying ArtPiece stencil on {l3_network}")
            try:
                # For L3 deployments, we may need higher gas limits
                gas_limit = 3000000  # Higher gas limit
                art_piece_stencil = deployer.deploy(
                    project.ArtPiece,
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"ArtPiece stencil deployed at: {art_piece_stencil.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "artPiece", art_piece_stencil.address, "ArtPiece")
                
                print("=" * 50)  # Delimiter after ArtPiece stencil deployment
                print("ArtPiece stencil deployment completed")
                print("=" * 50)
            except Exception as e:
                print(f"Error deploying ArtPiece stencil: {e}")
                sys.exit(1)

    # Deploy ArtCommissionHub template on L3
    with networks.parse_network_choice(l3_network) as provider:
        if not full_redeploy and commission_hub_existing_address and input(f"Use existing ArtCommissionHub template at {commission_hub_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing ArtCommissionHub template at: {commission_hub_existing_address}")
            commission_hub_template = project.ArtCommissionHub.at(commission_hub_existing_address)
        else:
            print(f"Deploying ArtCommissionHub template on {l3_network} (as reference for ArtCommissionHubOwners)")
            try:
                # For Arbitrum deployments, we may need higher gas limits
                gas_limit = 6000000  # Increased gas limit for larger contract
                commission_hub_template = deployer.deploy(
                    project.ArtCommissionHub, 
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"ArtCommissionHub template deployed at: {commission_hub_template.address}")
                print(f"Note: This ArtCommissionHub template is ONLY for reference in ArtCommissionHubOwners")
                print(f"      Actual ArtCommissionHub instances will be created through ArtCommissionHubOwners")
                
                # Update the frontend config
                update_contract_address(config_network, "artCommissionHub", commission_hub_template.address, "ArtCommissionHub")
                
                print("=" * 50)  # Delimiter after ArtCommissionHub template deployment
                print("ArtCommissionHub template deployment completed")
                print("=" * 50)
            except Exception as e:
                print(f"Error deploying ArtCommissionHub template: {e}")
                sys.exit(1)

    # Deploy Profile template on L3
    with networks.parse_network_choice(l3_network) as provider:
        if not full_redeploy and profile_template_existing_address and input(f"Use existing Profile template at {profile_template_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing Profile template at: {profile_template_existing_address}")
            profile_template = project.Profile.at(profile_template_existing_address)
        else:
            print(f"Deploying Profile template on {l3_network}")
            try:
                # For L3 deployments, we may need higher gas limits
                gas_limit = 6000000  # Much higher gas limit for Profile which is larger
                profile_template = deployer.deploy(
                    project.Profile,
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"Profile template deployed at: {profile_template.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "profileTemplate", profile_template.address, "Profile")
                
                print("=" * 50)  # Delimiter after Profile template deployment
                print("Profile template deployment completed")
                print("=" * 50)
            except Exception as e:
                print(f"Error deploying Profile template: {e}")
                sys.exit(1)

    # Deploy ProfileSocial template on L3
    with networks.parse_network_choice(l3_network) as provider:
        if not full_redeploy and profile_social_template_existing_address and input(f"Use existing ProfileSocial template at {profile_social_template_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing ProfileSocial template at: {profile_social_template_existing_address}")
            profile_social_template = project.ProfileSocial.at(profile_social_template_existing_address)
        else:
            print(f"Deploying ProfileSocial template on {l3_network}")
            try:
                # For L3 deployments, we may need higher gas limits
                gas_limit = 3000000  # Higher gas limit for ProfileSocial
                profile_social_template = deployer.deploy(
                    project.ProfileSocial,
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"ProfileSocial template deployed at: {profile_social_template.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "profileSocialTemplate", profile_social_template.address, "ProfileSocial")
                
                print("=" * 50)  # Delimiter after ProfileSocial template deployment
                print("ProfileSocial template deployment completed")
                print("=" * 50)
            except Exception as e:
                print(f"Error deploying ProfileSocial template: {e}")
                sys.exit(1)

    # Deploy ProfileFactoryAndRegistry on L3
    with networks.parse_network_choice(l3_network) as provider:
        if not full_redeploy and profile_factory_and_registry_existing_address and input(f"Use existing ProfileFactoryAndRegistry at {profile_factory_and_registry_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing ProfileFactoryAndRegistry at: {profile_factory_and_registry_existing_address}")
            profile_factory_and_registry = project.ProfileFactoryAndRegistry.at(profile_factory_and_registry_existing_address)
        else:
            print(f"Deploying ProfileFactoryAndRegistry on {l3_network}")
            try:
                # For L3 deployments, we may need higher gas limits
                gas_limit = 6000000  # Much higher gas limit for ProfileFactoryAndRegistry which might be large
                profile_factory_and_registry = deployer.deploy(
                    project.ProfileFactoryAndRegistry,
                    profile_template.address,  # Profile template address
                    profile_social_template.address,  # ProfileSocial template address
                    commission_hub_template.address,  # ArtCommissionHub template address
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"ProfileFactoryAndRegistry deployed at: {profile_factory_and_registry.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "profileFactoryAndRegistry", profile_factory_and_registry.address, "ProfileFactoryAndRegistry")
                
                print("=" * 50)  # Delimiter after ProfileFactoryAndRegistry deployment
                print("ProfileFactoryAndRegistry deployment completed")
                print("=" * 50)
            except Exception as e:
                print(f"Error deploying ProfileFactoryAndRegistry: {e}")
                sys.exit(1)

    # Deploy or use existing ArtCommissionHubOwners on L3
    with networks.parse_network_choice(l3_network) as provider:
        if not (full_redeploy or (network_choice == "prodtest" and redeploy_l2_l3)) and l3_existing_address and input(f"Use existing ArtCommissionHubOwners at {l3_existing_address}? (Y/n): ").strip().lower() != 'n':
            print(f"Using existing ArtCommissionHubOwners at: {l3_existing_address}")
            l3_art_commission_hub_owners = project.ArtCommissionHubOwners.at(l3_existing_address)
        else:
            print(f"Deploying ArtCommissionHubOwners on {l3_network}")
            try:
                # For Arbitrum deployments, we may need higher gas limits
                gas_limit = 6000000  # Increased gas limit for larger contract
                
                # Note: The deployer address (msg.sender) will automatically become the owner of the contract
                print(f"ArtCommissionHubOwners will be owned by: {deployer.address}")
                l3_art_commission_hub_owners = deployer.deploy(
                    project.ArtCommissionHubOwners,
                    l2_contract.address,  # L2OwnershipRelay address
                    commission_hub_template.address,  # ArtCommissionHub template address
                    art_piece_stencil.address,  # ArtPiece template address
                    gas_limit=gas_limit,
                    required_confirmations=1
                )
                print(f"ArtCommissionHubOwners deployed at: {l3_art_commission_hub_owners.address}")
                
                # Update the frontend config
                update_contract_address(config_network, "l3", l3_art_commission_hub_owners.address, "ArtCommissionHubOwners")
                
                print("=" * 50)  # Delimiter after ArtCommissionHubOwners deployment
                print("ArtCommissionHubOwners deployment completed")
                print("=" * 50)
            except Exception as e:
                print(f"Error deploying ArtCommissionHubOwners: {e}")
                sys.exit(1)

    # Now update the L2OwnershipRelay with the L3 ArtCommissionHubOwners address
    with networks.parse_network_choice(l2_network) as provider:
        print(f"Updating L2OwnershipRelay with L3 ArtCommissionHubOwners address: {l3_art_commission_hub_owners.address}")
        try:
            # Check the owner of the L2OwnershipRelay contract
            current_owner = l2_contract.owner()
            print(f"L2OwnershipRelay contract owner: {current_owner}")
            print(f"Deployer address: {deployer.address}")
            
            if current_owner != deployer.address:
                print(f"WARNING: Deployer address does not match L2OwnershipRelay owner!")
                print(f"This might be due to network connection issues or contract state not being properly synced.")
                print(f"Attempting to continue anyway...")
            
            # Set the L3 contract address
            tx = l2_contract.setL3Contract(l3_art_commission_hub_owners.address)
            print(f"L2OwnershipRelay updated with L3 ArtCommissionHubOwners address")
        except Exception as e:
            print(f"Error updating L2OwnershipRelay with L3 ArtCommissionHubOwners address: {e}")
            print(f"Debug: Try manually checking the owner of the L2OwnershipRelay contract")
            
            # Try getting more debugging information
            try:
                current_owner = l2_contract.owner()
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
            print(f"L2OwnershipRelay.setL3Contract({l3_art_commission_hub_owners.address})")
            
            # Ask if the user wants to retry
            if input("Do you want to retry updating the L3 contract address? (y/n): ").strip().lower() == 'y':
                try:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                    tx = l2_contract.setL3Contract(l3_art_commission_hub_owners.address)
                    print(f"L2OwnershipRelay successfully updated with L3 ArtCommissionHubOwners address on retry")
                except Exception as retry_error:
                    print(f"Error on retry: {retry_error}")
                    print(f"You will need to manually set the L3 contract address later.")

    # Deploy or use existing L1 contract on Ethereum
    with networks.parse_network_choice(l1_network) as provider:
        skip_l1_deployment = False
        if (not full_redeploy and l1_existing_address and 
            (input(f"Use existing L1 contract at {l1_existing_address}? (Y/n): ").strip().lower() != 'n' or 
             network_choice == "prodtest")):  # Always prefer existing L1 for prodtest
            print(f"Using existing L1QueryOwnership at: {l1_existing_address}")
            l1_contract = project.L1QueryOwnership.at(l1_existing_address)
        else:
            # For prodtest, double-check before deploying to mainnet
            if network_choice == "prodtest":
                print("WARNING: You're about to deploy a new L1QueryOwnership contract to Ethereum Mainnet")
                confirm = input("This will cost significant gas. Are you sure? (yes/no): ").strip().lower()
                if confirm != "yes":
                    print("Please provide an existing L1QueryOwnership address instead.")
                    l1_address = input("Enter existing L1QueryOwnership address: ").strip()
                    if l1_address:
                        l1_contract = project.L1QueryOwnership.at(l1_address)
                        update_contract_address(config_network, "l1", l1_address, "L1QueryOwnership")
                        print(f"Using provided L1QueryOwnership at: {l1_address}")
                        skip_l1_deployment = True
                    else:
                        print("No address provided. Deployment canceled.")
                        sys.exit(1)
            
            # Only deploy if we haven't decided to skip
            if not skip_l1_deployment:
                print(f"Deploying L1QueryOwnership on {l1_network}")
                # Get the Sequencer inbox address for the L1QueryOwnership constructor
                if network_choice == "local":
                    inbox_address = "0x0000000000000000000000000000000000000000"  # Default for local
                elif network_choice == "testnet":
                    inbox_address = "0xaAe29B0366299461418F5324a79Afc425BE5ae21"  # Sepolia for retryable tickets
                else:
                    inbox_address = "0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f"  # Mainnet
                
                # Allow customizing the inbox address
                inbox_input = input(f"Enter Arbitrum Inbox address (default: {inbox_address}): ").strip()
                if inbox_input:
                    inbox_address = inbox_input
                
                try:    
                    l1_contract = deployer.deploy(project.L1QueryOwnership, inbox_address, required_confirmations=1)
                    print(f"L1QueryOwnership deployed at: {l1_contract.address}")
                    
                    # Update the frontend config
                    update_contract_address(config_network, "l1", l1_contract.address, "L1QueryOwnership")
                    
                    print("=" * 50)  # Delimiter after L1QueryOwnership deployment
                    print("L1QueryOwnership deployment completed")
                    print("=" * 50)
                except Exception as e:
                    print(f"Error deploying L1QueryOwnership: {e}")
                    sys.exit(1)

    # Set up cross-chain communication by registering L1QueryOwnership in L2OwnershipRelay for specific chain ID
    with networks.parse_network_choice(l2_network) as provider:
        if l1_contract:
            # Get the L1 chain ID
            if network_choice == "local":
                l1_chain_id = 1337  # Default local chain ID
            elif network_choice == "testnet":
                l1_chain_id = 11155111  # Sepolia
            else:
                l1_chain_id = 1  # Ethereum Mainnet
            
            # Allow customizing the chain ID
            chain_id_input = input(f"Enter L1 chain ID to register (default: {l1_chain_id}): ").strip()
            if chain_id_input and chain_id_input.isdigit():
                l1_chain_id = int(chain_id_input)
            
            print(f"Registering L1QueryOwnership ({l1_contract.address}) for chain ID {l1_chain_id} in L2OwnershipRelay")
            try:
                tx = l2_contract.updateCrossChainQueryOwnerContract(l1_contract.address, l1_chain_id)
                print(f"L1QueryOwnership successfully registered in L2OwnershipRelay for chain ID {l1_chain_id}")
            except Exception as e:
                print(f"Error registering L1QueryOwnership in L2OwnershipRelay: {e}")
                print(f"You will need to manually register L1QueryOwnership later using:")
                print(f"L2OwnershipRelay.updateCrossChainQueryOwnerContract({l1_contract.address}, {l1_chain_id})")

    # CRITICAL: Establish bidirectional connection between ArtCommissionHubOwners and ProfileFactoryAndRegistry
    if l3_art_commission_hub_owners and profile_factory_and_registry:
        with networks.parse_network_choice(l3_network) as provider:
            print(f"\n=== Setting up bidirectional connection between contracts ===")
            print(f"Connecting ArtCommissionHubOwners ({l3_art_commission_hub_owners.address}) to ProfileFactoryAndRegistry ({profile_factory_and_registry.address})")
            try:
                # This call is critical - it sets up the bidirectional connection
                # Without it, commission hubs won't be automatically linked to profiles
                tx = l3_art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory_and_registry.address)
                print(f"Bidirectional connection established successfully")
                
                # Verify the connection
                registry_from_factory = profile_factory_and_registry.artCommissionHubOwners()
                factory_from_registry = l3_art_commission_hub_owners.profileFactoryAndRegistry()
                print(f"Verification: ProfileFactoryAndRegistry points to: {registry_from_factory}")
                print(f"Verification: ArtCommissionHubOwners points to: {factory_from_registry}")
                
                if registry_from_factory != l3_art_commission_hub_owners.address:
                    print(f"WARNING: Verification failed - ProfileFactoryAndRegistry not pointing to ArtCommissionHubOwners")
                if factory_from_registry != profile_factory_and_registry.address:
                    print(f"WARNING: Verification failed - ArtCommissionHubOwners not pointing to ProfileFactoryAndRegistry")
            except Exception as e:
                print(f"Error establishing bidirectional connection: {e}")
                print(f"CRITICAL: You must manually call linkProfileFactoryAndRegistry later using:")
                print(f"ArtCommissionHubOwners.linkProfileFactoryAndRegistry({profile_factory_and_registry.address})")
                print(f"Without this connection, commission hubs won't be linked to user profiles automatically")

    # Print deployment summary
    print("\n=== Deployment Summary ===")
    print(f"Network: {network_choice}")
    print(f"L1 Contract (Ethereum): {l1_contract.address if l1_contract else 'Not deployed'}")
    print(f"L2 Contract (Arbitrum): {l2_contract.address if l2_contract else 'Not deployed'}")
    
    if network_choice == "production":
        print(f"L3 Contracts (Animechain L3) - PENDING DEPLOYMENT:")
        print(f"  Note: Contracts will need to be deployed to Animechain L3 later")
        print(f"  Save these addresses for reference when deploying to production")
    elif network_choice == "prodtest":
        print(f"L3 Contracts (Animechain L3):")
        print(f"  - ArtCommissionHubOwners: {l3_art_commission_hub_owners.address if l3_art_commission_hub_owners else 'Not deployed'}")
        print(f"  - ArtCommissionHub Template: {commission_hub_template.address if commission_hub_template else 'Not deployed'}")
        print(f"  - ArtPiece Stencil: {art_piece_stencil.address if art_piece_stencil else 'Not deployed'}")
        print(f"  - Profile Template: {profile_template.address if profile_template else 'Not deployed'}")
        print(f"  - ProfileSocial Template: {profile_social_template.address if profile_social_template else 'Not deployed'}")
        print(f"  - ProfileFactoryAndRegistry: {profile_factory_and_registry.address if profile_factory_and_registry else 'Not deployed'}")
        print("\nNOTE: These are TEST contracts deployed to PRODUCTION networks.")
        print("They can be used for testing with real chain interactions, but should not be")
        print("considered the final production deployment.")
    else:
        print(f"L3 Contracts ({l3_network}):")
        print(f"  - ArtCommissionHubOwners: {l3_art_commission_hub_owners.address if l3_art_commission_hub_owners else 'Not deployed'}")
        print(f"  - ArtCommissionHub Template: {commission_hub_template.address if commission_hub_template else 'Not deployed'}")
        print(f"  - ArtPiece Stencil: {art_piece_stencil.address if art_piece_stencil else 'Not deployed'}")
        print(f"  - Profile Template: {profile_template.address if profile_template else 'Not deployed'}")
        print(f"  - ProfileSocial Template: {profile_social_template.address if profile_social_template else 'Not deployed'}")
        print(f"  - ProfileFactoryAndRegistry: {profile_factory_and_registry.address if profile_factory_and_registry else 'Not deployed'}")
    
    # Check if the contracts were properly linked
    if l2_contract:
        try:
            l3_contract = l2_contract.l3Contract()
            print(f"\nContract Links:")
            print(f"  - L2OwnershipRelay -> ArtCommissionHubOwners: {l3_contract}")
            
            # Check registered L1 contracts by chain
            if l1_contract:
                try:
                    l1_chain_id_str = str(l1_chain_id) if 'l1_chain_id' in locals() else "unknown"
                    l1_registered = l2_contract.crossChainRegistryAddressByChainId(l1_chain_id if 'l1_chain_id' in locals() else 1)
                    print(f"  - L2OwnershipRelay -> L1QueryOwnership for chain {l1_chain_id_str}: {l1_registered}")
                except Exception as e:
                    print(f"Could not retrieve L1 registration info: {e}")
        except Exception as e:
            print(f"Could not retrieve contract links: {e}")
    
    if l3_art_commission_hub_owners:
        try:
            l2relay = l3_art_commission_hub_owners.l2OwnershipRelay()
            hub_template = l3_art_commission_hub_owners.artCommissionHubTemplate()
            print(f"  - ArtCommissionHubOwners -> L2OwnershipRelay: {l2relay}")
            print(f"  - ArtCommissionHubOwners -> ArtCommissionHub Template: {hub_template}")
        except Exception as e:
            print(f"Could not retrieve ArtCommissionHubOwners links: {e}")
    
    print("\nFrontend configuration has been updated.")
    
    if network_choice == "production":
        print("\nIMPORTANT: For production, you will need to:")
        print("1. Deploy the L3 contracts to Animechain L3 later when available")
        print("2. Update the L2OwnershipRelay contract with the new L3 ArtCommissionHubOwners address")
        print("3. Update your frontend configuration with the final production addresses")
    
    print(f"\nMake sure to use these contract addresses in your application.\n")
    print(f"\nPlease run: ape run compile_and_extract_abis\n")

    return l1_contract, l2_contract, l3_art_commission_hub_owners, commission_hub_template, art_piece_stencil, profile_template, profile_social_template, profile_factory_and_registry

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