#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def read_image_file(file_path):
    """Read an image file and return the binary data"""
    with open(file_path, "rb") as f:
        return f.read()

def hex_encode_bytes(data):
    """Convert binary data to hex string for command line"""
    return "0x" + data.hex()

def run_ape_command(command, input_data=None):
    """Run an ape command and return the output"""
    full_command = f"ape {command}"
    print(f"Running: {full_command}")
    
    result = subprocess.run(
        full_command,
        shell=True,
        text=True,
        capture_output=True,
        input=input_data
    )
    
    if result.returncode != 0:
        print(f"Error executing command: {full_command}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        sys.exit(1)
    
    return result.stdout.strip()

def main():
    # Load environment variables
    load_dotenv()
    
    # Check if private key is set
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("Error: PRIVATE_KEY environment variable not set. Please check your .env file.")
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
    
    # Network to connect to
    network_name = os.getenv("NETWORK", "animechain:custom")
    
    # Create a keyfile for the account
    account_name = "deployer"
    keyfile_path = Path.home() / ".ape" / "accounts" / f"{account_name}.json"
    
    # Only create the keyfile if it doesn't exist
    if not keyfile_path.exists():
        # Make sure directory exists
        keyfile_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a password for the keyfile
        password = os.getenv("ACCOUNT_PASSWORD", "password")
        
        # Create the keyfile data
        keyfile_data = {
            "address": None,  # Ape will fill this in
            "crypto": {
                "cipher": "aes-128-ctr",
                "cipherparams": {
                    "iv": None  # Ape will fill this in
                },
                "ciphertext": None,  # Ape will fill this in
                "kdf": "scrypt",
                "kdfparams": {
                    "dklen": 32,
                    "n": 262144,
                    "p": 1,
                    "r": 8,
                    "salt": None  # Ape will fill this in
                },
                "mac": None  # Ape will fill this in
            },
            "id": account_name,
            "version": 3
        }
        
        # Write the keyfile
        with open(keyfile_path, "w") as f:
            json.dump(keyfile_data, f, indent=4)
        
        # Import the private key
        import_cmd = f"accounts import {account_name}"
        run_ape_command(import_cmd, private_key + "\n" + password + "\n" + password)
        
        print(f"Created account: {account_name}")
    
    # Connect to the network
    print(f"Connecting to network: {network_name}")
    
    try:
        # Create a temporary deploy script in the scripts folder
        scripts_dir = Path(__file__).parent.parent / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # Deploy Registry contract
        print("Deploying Registry contract...")
        deploy_script = scripts_dir / "temp_deploy_registry.py"
        
        with open(deploy_script, "w") as f:
            f.write(f"""
import ape
from ape import accounts, project

def main():
    account = accounts.load("{account_name}")
    registry = project.Registry.deploy(sender=account)
    print("REGISTRY_ADDRESS=", registry.address)
""")
        
        deploy_cmd = f"run temp_deploy_registry.py -s {network_name}"
        result = run_ape_command(deploy_cmd)
        
        # Extract registry address from output
        for line in result.split("\n"):
            if "REGISTRY_ADDRESS=" in line:
                registry_address = line.split("=")[1].strip()
                print(f"Registry deployed at: {registry_address}")
                break
        else:
            print("Failed to find registry address in output")
            sys.exit(1)
        
        # Set L1 contract address if provided
        if l1_contract_address:
            print(f"Setting L1 contract address to {l1_contract_address}...")
            
            set_l1_script = scripts_dir / "temp_set_l1.py"
            with open(set_l1_script, "w") as f:
                f.write(f"""
import ape
from ape import accounts, project

def main():
    account = accounts.load("{account_name}")
    registry = project.Registry.at("{registry_address}")
    tx = registry.setL1Contract("{l1_contract_address}", sender=account)
    print("TX_HASH=", tx.txn_hash)
""")
            
            set_l1_cmd = f"run temp_set_l1.py -s {network_name}"
            result = run_ape_command(set_l1_cmd)
            print("L1 contract address set.")
        
        # Deploy image contracts for each Azuki PNG
        image_contract_addresses = []
        
        for i, img_file in enumerate(image_files):
            img_path = images_folder / img_file
            print(f"Reading image data from {img_path}...")
            image_data = read_image_file(img_path)
            
            # Use temporary file to store hex-encoded image data
            temp_file = Path(__file__).parent / f"temp_image_data_{i}.txt"
            with open(temp_file, "w") as f:
                f.write(hex_encode_bytes(image_data))
            
            print(f"Deploying CommissionedArt contract for Azuki #{i}...")
            zero_address = "0x0000000000000000000000000000000000000000"
            
            deploy_img_script = scripts_dir / f"temp_deploy_image_{i}.py"
            with open(deploy_img_script, "w") as f:
                f.write(f"""
import ape
from ape import accounts, project

def main():
    account = accounts.load("{account_name}")
    with open("{temp_file}", "r") as f:
        image_data = bytes.fromhex(f.read()[2:])
    contract = project.CommissionedArt.deploy(image_data, "{zero_address}", "{zero_address}", sender=account, gas_limit=10000000)
    print("CONTRACT_ADDRESS=", contract.address)
""")
            
            deploy_img_cmd = f"run temp_deploy_image_{i}.py -s {network_name}"
            result = run_ape_command(deploy_img_cmd)
            
            # Clean up temp file
            temp_file.unlink(missing_ok=True)
            
            # Extract contract address from output
            for line in result.split("\n"):
                if "CONTRACT_ADDRESS=" in line:
                    contract_address = line.split("=")[1].strip()
                    image_contract_addresses.append(contract_address)
                    print(f"CommissionedArt for Azuki #{i} deployed at: {contract_address}")
                    break
            else:
                print(f"Failed to find address for Azuki #{i}")
                continue
            
            # Register the image contract in the Registry
            print(f"Registering Azuki #{i} in the Registry...")
            
            register_script = scripts_dir / f"temp_register_image_{i}.py"
            with open(register_script, "w") as f:
                f.write(f"""
import ape
from ape import accounts, project

def main():
    account = accounts.load("{account_name}")
    registry = project.Registry.at("{registry_address}")
    tx = registry.registerImageData({i}, "{contract_address}", sender=account)
    print("TX_HASH=", tx.txn_hash)
""")
            
            register_cmd = f"run temp_register_image_{i}.py -s {network_name}"
            result = run_ape_command(register_cmd)
            print(f"Azuki #{i} registered.")
        
        # After all images are deployed, rescind ownership if specified
        if os.getenv("RESCIND_OWNERSHIP", "false").lower() == "true":
            print("Rescinding Registry ownership...")
            
            rescind_script = scripts_dir / "temp_rescind_ownership.py"
            with open(rescind_script, "w") as f:
                f.write(f"""
import ape
from ape import accounts, project

def main():
    account = accounts.load("{account_name}")
    registry = project.Registry.at("{registry_address}")
    tx = registry.rescindOwnership(sender=account)
    print("TX_HASH=", tx.txn_hash)
""")
            
            rescind_cmd = f"run temp_rescind_ownership.py -s {network_name}"
            result = run_ape_command(rescind_cmd)
            print("Ownership rescinded.")
            print("WARNING: You can no longer register new images or modify the Registry!")
        
        # Print deployment summary
        print("\nDeployment Summary:")
        print(f"Registry Contract: {registry_address}")
        
        # Get L1 contract link
        l1_script = scripts_dir / "temp_get_l1.py"
        with open(l1_script, "w") as f:
            f.write(f"""
import ape
from ape import project

def main():
    registry = project.Registry.at("{registry_address}")
    print("L1_CONTRACT=", registry.l1_contract())
""")
        
        l1_cmd = f"run temp_get_l1.py -s {network_name}"
        result = run_ape_command(l1_cmd)
        
        # Extract L1 contract address
        for line in result.split("\n"):
            if "L1_CONTRACT=" in line:
                l1_contract = line.split("=")[1].strip()
                print(f"L1 Contract Link: {l1_contract}")
                break
        
        # Display registered images
        print("Registered Azuki Images:")
        for i in range(len(image_files)):
            get_img_script = scripts_dir / f"temp_get_image_{i}.py"
            with open(get_img_script, "w") as f:
                f.write(f"""
import ape
from ape import project

def main():
    registry = project.Registry.at("{registry_address}")
    print("IMG_CONTRACT_{i}=", registry.imageDataContracts({i}))
""")
            
            get_img_cmd = f"run temp_get_image_{i}.py -s {network_name}"
            result = run_ape_command(get_img_cmd)
            
            # Extract contract address
            for line in result.split("\n"):
                if f"IMG_CONTRACT_{i}=" in line:
                    img_contract = line.split("=")[1].strip()
                    print(f"  Azuki #{i}: {img_contract}")
                    break
        
        # Clean up temporary scripts
        for file in scripts_dir.glob("temp_*.py"):
            file.unlink(missing_ok=True)
        
        print("\nDeployment completed successfully!")
        
    except Exception as e:
        print(f"Error during deployment: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 