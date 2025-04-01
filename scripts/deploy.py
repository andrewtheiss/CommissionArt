from ape import accounts, project, Contract, networks
import os

# Configuration for AnimeChain
ANIMECHAIN_CONFIG = {
    "name": "animechain",
    "chain_id": 69000,
    "rpc_url": "https://rpc-animechain-39xf6m45e3.t.conduit.xyz",
    "private_key": "0xYourPrivateKeyHere1234567890abcdef1234567890abcdef1234567890abcdef"  # Replace with your actual private key
}

def setup_animechain_network():
    # Register the custom network if not already registered
    if "animechain" not in networks.ecosystems["ethereum"]:
        networks.parse_network_choice(f"ethereum:{ANIMECHAIN_CONFIG['name']}:{ANIMECHAIN_CONFIG['rpc_url']}:{ANIMECHAIN_CONFIG['chain_id']}")
    
def deploy_contracts():
    # Set up the private key account
    try:
        deployer = accounts.load("animechain_deployer")
    except:
        deployer = accounts.add(ANIMECHAIN_CONFIG["private_key"])
        deployer.alias = "animechain_deployer"

    # Switch to AnimeChain network
    setup_animechain_network()
    with networks.ethereum["animechain"].use_provider("custom"):
        print(f"Connected to AnimeChain (Chain ID: {ANIMECHAIN_CONFIG['chain_id']})")
        
        # Sample image data for 5 contracts (you can modify these)
        image_data_samples = [
            b"image_data_1" + b"\x00" * (250000 - len(b"image_data_1")),
            b"image_data_2" + b"\x00" * (250000 - len(b"image_data_2")),
            b"image_data_3" + b"\x00" * (250000 - len(b"image_data_3")),
            b"image_data_4" + b"\x00" * (250000 - len(b"image_data_4")),
            b"image_data_5" + b"\x00" * (250000 - len(b"image_data_5")),
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
                deployer.address,  # owner
                deployer.address   # artist
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