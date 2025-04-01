#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from ape import accounts, project, networks

def read_image_file(file_path):
    """Read an image file and return the binary data"""
    with open(file_path, "rb") as f:
        return f.read()

def main():
    # Load environment variables
    load_dotenv()
    
    # Check if private key is set
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("Error: PRIVATE_KEY environment variable not set. Please check your .env file.")
        sys.exit(1)
    
    # Get L3 account from private key
    try:
        deployer = accounts.load("deployer_account", private_key=private_key)
        print(f"Account loaded: {deployer.address}")
    except Exception as e:
        print(f"Error loading account: {e}")
        sys.exit(1)
    
    # Get L1 contract address from environment variable
    l1_contract_address = os.getenv("L1_CONTRACT_ADDRESS")
    if not l1_contract_address:
        print("Warning: L1_CONTRACT_ADDRESS not set. Continuing without linking to L1.")
    
    # Path to Azuki images folder 
    images_folder = Path(__file__).parent / "azuki_images"
    if not images_folder.exists():
        print(f"Error: Images folder not found at {images_folder}")
        sys.exit(1)
    
    # Image files we want to deploy
    image_files = [f"{i}.png" for i in range(5)]
    
    # Verify all image files exist
    for img_file in image_files:
        img_path = images_folder / img_file
        if not img_path.exists():
            print(f"Error: Image file {img_path} not found")
            sys.exit(1)
    
    # Connect to network
    network_name = os.getenv("NETWORK", "animechain:custom")
    networks.parse_network_choice(network_name)
    
    print(f"Connected to network: {networks.provider.network.name}")
    print(f"Deployer address: {deployer.address}")
    print(f"Deployer balance: {deployer.balance}")
    
    try:
        # Deploy Registry contract
        print("Deploying Registry contract...")
        registry = project.Registry.deploy(sender=deployer)
        print(f"Registry deployed at: {registry.address}")
        
        # Set L1 contract address if provided
        if l1_contract_address:
            print(f"Setting L1 contract address to {l1_contract_address}...")
            tx = registry.setL1Contract(l1_contract_address, sender=deployer)
            tx.await_confirmations()
            print(f"L1 contract address set. Transaction hash: {tx.txn_hash}")
        
        # Deploy image contracts for each Azuki PNG
        for i, img_file in enumerate(image_files):
            img_path = images_folder / img_file
            print(f"Reading image data from {img_path}...")
            image_data = read_image_file(img_path)
            
            print(f"Deploying CommissionedArt contract for Azuki #{i}...")
            # Use zero address for owner and artist
            zero_address = "0x0000000000000000000000000000000000000000"
            
            commissioned_art = project.CommissionedArt.deploy(
                image_data,
                zero_address,
                zero_address,
                sender=deployer,
                gas_limit=10000000  # Adjust this as needed
            )
            print(f"CommissionedArt for Azuki #{i} deployed at: {commissioned_art.address}")
            
            # Register the image contract in the Registry
            print(f"Registering Azuki #{i} in the Registry...")
            tx = registry.registerImageData(i, commissioned_art.address, sender=deployer)
            tx.await_confirmations()
            print(f"Azuki #{i} registered. Transaction hash: {tx.txn_hash}")
        
        # After all images are deployed, rescind ownership if specified
        if os.getenv("RESCIND_OWNERSHIP", "false").lower() == "true":
            print("Rescinding Registry ownership...")
            tx = registry.rescindOwnership(sender=deployer)
            tx.await_confirmations()
            print(f"Ownership rescinded. Transaction hash: {tx.txn_hash}")
            print("WARNING: You can no longer register new images or modify the Registry!")
        
        print("\nDeployment Summary:")
        print(f"Registry Contract: {registry.address}")
        print(f"L1 Contract Link: {registry.l1_contract()}")
        print("Registered Azuki Images:")
        for i in range(len(image_files)):
            img_contract = registry.imageDataContracts(i)
            print(f"  Azuki #{i}: {img_contract}")
        
        print("\nDeployment completed successfully!")
        
    except Exception as e:
        print(f"Error during deployment: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 