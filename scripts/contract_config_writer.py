import json
import os
from pathlib import Path

# Configuration file path (relative to project root)
CONFIG_FILE_PATH = "src/assets/contract_config.json"

def ensure_directory_exists(file_path):
    """Ensure the directory for the file exists."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def load_config():
    """Load the existing configuration or create a default one if it doesn't exist."""
    config_path = Path(__file__).parent.parent / CONFIG_FILE_PATH
    
    # Make sure the directory exists
    ensure_directory_exists(config_path)
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {CONFIG_FILE_PATH} exists but is not valid JSON. Creating default.")
    
    # Default configuration
    default_config = {
        "networks": {
            "testnet": {
                "l1": {
                    "address": "",
                    "contract": "L1QueryOwner"
                },
                "l2": {
                    "address": "",
                    "contract": "L2Relay"
                },
                "l3": {
                    "address": "",
                    "contract": "OwnerRegistry"
                }
            },
            "mainnet": {
                "l1": {
                    "address": "",
                    "contract": "L1QueryOwner"
                },
                "l2": {
                    "address": "",
                    "contract": "L2Relay"
                },
                "l3": {
                    "address": "",
                    "contract": "OwnerRegistry"
                }
            }
        },
        "lastUpdated": ""
    }
    
    return default_config

def save_config(config):
    """Save the configuration to the file."""
    config_path = Path(__file__).parent.parent / CONFIG_FILE_PATH
    
    # Ensure the directory exists
    ensure_directory_exists(config_path)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        
    print(f"Contract configuration saved to {CONFIG_FILE_PATH}")
    
def update_contract_address(network, layer, address, contract_name=None):
    """
    Update a contract address in the configuration.
    
    Args:
        network (str): 'testnet' or 'mainnet'
        layer (str): 'l1', 'l2', or 'l3'
        address (str): The contract address
        contract_name (str, optional): Contract name to update
    """
    config = load_config()
    
    # Update the timestamp
    from datetime import datetime
    config["lastUpdated"] = datetime.now().isoformat()
    
    # Update the address
    config["networks"][network][layer]["address"] = address
    
    # Update the contract name if provided
    if contract_name:
        config["networks"][network][layer]["contract"] = contract_name
    
    save_config(config)
    print(f"Updated {layer.upper()} contract on {network}: {address}")
    
def get_contract_address(network, layer):
    """
    Get a contract address from the configuration.
    
    Args:
        network (str): 'testnet' or 'mainnet'
        layer (str): 'l1', 'l2', or 'l3'
        
    Returns:
        str: The contract address or empty string if not found
    """
    config = load_config()
    return config["networks"][network][layer]["address"]

def get_all_contracts():
    """Get all contract configurations."""
    return load_config()

if __name__ == "__main__":
    # Test the functionality
    update_contract_address("testnet", "l1", "0x123456789abcdef")
    print(get_contract_address("testnet", "l1")) 