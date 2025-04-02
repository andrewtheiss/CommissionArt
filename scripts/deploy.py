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

    # Prompt for start and end IDs
    start = int(input("Enter start ID (inclusive): ").strip())
    end = int(input("Enter end ID (inclusive): ").strip())
    
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

    # Enable auto-signing for the deployer account
    deployer.set_autosign(True, passphrase=passphrase)


    # Use the network from config
    with networks.parse_network_choice("ethereum:custom:node") as provider:
        print(f"Connected to AnimeChain (Chain ID: {ANIMECHAIN_CONFIG['chain_id']})")
        
        # Prompt user for existing registry contract address
        registry_address = input("Enter existing Registry contract address (or press Enter to deploy new): ").strip()
        
        if registry_address:
            # Use existing registry contract
            try:
                registry_contract = project.Registry.at(registry_address) # 0x6E28577074170227E7D3C646D840514e9BE0333C
                print(f"Using existing Registry contract at: {registry_contract.address}")
            except Exception as e:
                raise ValueError(f"Invalid registry contract address or unable to connect: {str(e)}")
        else:
            # Deploy new registry contract
            registry_contract = project.Registry.at("0x5174f3e6F83CF2283b7677829356C8Bc6fCe578f") # 0x6E28577074170227E7D3C646D840514e9BE0333C

            # print("Deploying new Registry contract...")
            # registry_contract = deployer.deploy(project.Registry, required_confirmations=0)
            # print(f"Registry deployed at: {registry_contract.address}")
            # 0x5174f3e6F83CF2283b7677829356C8Bc6fCe578f
        

        # Load image data from the azuki_images_avif_1000x1000 folder
        image_folder = Path(__file__).parent / 'azuki_images_avif_1000x1000'
        image_data_samples = []
        for i in range(start, end + 1):
            image_path = image_folder / f'{i}.avif'
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            with open(image_path, 'rb') as f:
                image_data = f.read()
            image_data_samples.append(image_data)

        # Deploy image data contracts and register them
        image_contracts = []
        for idx, i in enumerate(range(start, end + 1)):
            print(f"Deploying CommissionedArt contract {idx+1}/{end-start+1}...")

            image_contract = deployer.deploy(
                project.CommissionedArt,
                image_data_samples[idx],
                deployer.address,
                deployer.address,
                required_confirmations=0
            )
            image_contracts.append(image_contract)
            print(f"CommissionedArt contract {idx+1} deployed at: {image_contract.address}")

            # Register the contract with the exact ID i
            registry_contract.registerImageData(
                i,  # Using the actual ID (18, 19, 20, etc.), not 0-15
                image_contract.address, 
                sender=deployer,
                required_confirmations=0)
            print(f"Registered CommissionedArt contract {idx+1} with Azuki ID {i}")

        # Verify deployments
        print("\nDeployment Summary:")
        print(f"Registry Contract: {registry_contract.address}")
        for idx, contract in enumerate(image_contracts):
            azuki_id = start + idx
            print(f"CommissionedArt Contract {idx+1} (Azuki ID {azuki_id}): {contract.address}")
            print(f"Stored owner: {contract.get_owner()}")
            print(f"Stored artist: {contract.get_artist()}")
        
        return registry_contract, image_contracts

def main():
    deploy_contracts()

if __name__ == "__main__":
    main()