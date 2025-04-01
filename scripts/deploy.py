from ape import accounts, project, Contract, networks
from ape_accounts import import_account_from_private_key
from getpass import getpass
from dotenv import load_dotenv
from pathlib import Path
import os

ANIMECHAIN_CONFIG = {
    "name": "animechain",
    "chain_id": 69000,
    "rpc_url": "https://rpc-animechain-39xf6m45e3.t.conduit.xyz"
}

def deploy_contracts():

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
        # If loaded, ensure it matches the private key (optional check)
    except:
        deployer = import_account_from_private_key("animechain_deployer", passphrase, private_key)


    # Use the network from config
    with networks.parse_network_choice("ethereum:custom:node") as provider:
        print(f"Connected to AnimeChain (Chain ID: {ANIMECHAIN_CONFIG['chain_id']})")
        
        # Sample image data for 5 contracts
        image_data_samples = [
            b"image_data_1" + b"\x00" * (45000 - len(b"image_data_1")),
            b"image_data_2" + b"\x00" * (45000 - len(b"image_data_2")),
            b"image_data_3" + b"\x00" * (45000 - len(b"image_data_3")),
            b"image_data_4" + b"\x00" * (45000 - len(b"image_data_4")),
            b"image_data_5" + b"\x00" * (45000 - len(b"image_data_5")),
        ]

        # Deploy the registry contract first
        print("Deploying Registry contract...")
        registry_contract = deployer.deploy(project.Registry)
        print(f"Registry deployed at: {registry_contract.address}")

        # Deploy 5 image data contracts and register them
        image_contracts = []
        for i in range(5):
            print(f"Deploying CommissionedArt contract {i+1}/5...")
            image_contract = deployer.deploy(
                project.CommissionedArt,
                image_data_samples[i],
                deployer.address,
                deployer.address
            )
            image_contracts.append(image_contract)
            print(f"CommissionedArt contract {i+1} deployed at: {image_contract.address}")

            # Register the contract
            print(f"Registering CommissionedArt contract {i+1} with Azuki ID {i}...")
            registry_contract.registerCommissionedArt(i, image_contract.address, sender=deployer)
            print(f"Registered CommissionedArt contract {i+1} with Azuki ID {i}")

        # Verify deployments
        print("\nDeployment Summary:")
        print(f"Registry Contract: {registry_contract.address}")
        for i, contract in enumerate(image_contracts):
            print(f"CommissionedArt Contract {i+1} (Azuki ID {i}): {contract.address}")
            print(f"Stored owner: {contract.get_owner()}")
            print(f"Stored artist: {contract.get_artist()}")
        
        return registry_contract, image_contracts

def main():
    deploy_contracts()

if __name__ == "__main__":
    main()