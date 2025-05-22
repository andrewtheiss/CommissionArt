import json
import os
from pathlib import Path
from datetime import datetime

# Configuration file path (relative to project root)
CONFIG_FILE_PATH = "src/assets/contract_config.json"

def ensure_directory_exists(file_path):
    """Ensure the directory for the file exists."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def get_default_config():
    """Get the default configuration structure."""
    return {
        "networks": {
            "testnet": {
                "l1": {
                    "address": "",
                    "contract": "L1QueryOwnership"
                },
                "l2": {
                    "address": "",
                    "contract": "L2OwnershipRelay"
                },
                "l3": {
                    "address": "",
                    "contract": "ArtCommissionHubOwners"
                },
                "artCommissionHub": {
                    "address": "",
                    "contract": "ArtCommissionHub"
                },
                "artPiece": {
                    "address": "",
                    "contract": "ArtPiece"
                },
                "profileTemplate": {
                    "address": "",
                    "contract": "Profile"
                },
                "profileFactoryAndRegistry": {
                    "address": "",
                    "contract": "ProfileFactoryAndRegistry"
                }
            },
            "mainnet": {
                "l1": {
                    "address": "",
                    "contract": "L1QueryOwnership"
                },
                "l2": {
                    "address": "",
                    "contract": "L2OwnershipRelay"
                },
                "l3": {
                    "address": "",
                    "contract": "ArtCommissionHubOwners"
                },
                "artCommissionHub": {
                    "address": "",
                    "contract": "ArtCommissionHub"
                },
                "artPiece": {
                    "address": "",
                    "contract": "ArtPiece"
                },
                "profileTemplate": {
                    "address": "",
                    "contract": "Profile"
                },
                "profileFactoryAndRegistry": {
                    "address": "",
                    "contract": "ProfileFactoryAndRegistry"
                }
            }
        },
        "lastUpdated": datetime.now().isoformat()
    }

def validate_config(config):
    """
    Validate the configuration and ensure all required fields exist.
    If fields are missing, they will be added with default values.
    """
    default_config = get_default_config()
    modified = False
    
    # Check networks section
    if "networks" not in config:
        config["networks"] = default_config["networks"]
        modified = True
    
    # Ensure lastUpdated is present
    if "lastUpdated" not in config:
        config["lastUpdated"] = default_config["lastUpdated"]
        modified = True
    
    # Check for required networks
    required_networks = ["testnet", "mainnet"]
    for network in required_networks:
        if network not in config["networks"]:
            config["networks"][network] = default_config["networks"][network]
            modified = True
            print(f"Added missing network '{network}' to configuration")
        else:
            # Check for required layers in each network
            required_layers = ["l1", "l2", "l3", "artCommissionHub", "artPiece", "profileTemplate", "profileFactoryAndRegistry"]
            for layer in required_layers:
                if layer not in config["networks"][network]:
                    config["networks"][network][layer] = default_config["networks"][network][layer]
                    modified = True
                    print(f"Added missing layer '{layer}' to network '{network}'")
                else:
                    # Check for required fields in each layer
                    required_fields = ["address", "contract"]
                    for field in required_fields:
                        if field not in config["networks"][network][layer]:
                            config["networks"][network][layer][field] = default_config["networks"][network][layer][field]
                            modified = True
                            print(f"Added missing field '{field}' to layer '{layer}' in network '{network}'")
    
    return config, modified

def load_config():
    """Load the existing configuration or create a default one if it doesn't exist."""
    config_path = Path(__file__).parent.parent / CONFIG_FILE_PATH
    
    # Make sure the directory exists
    ensure_directory_exists(config_path)
    
    default_config = get_default_config()
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate and repair config if needed
            config, modified = validate_config(config)
            
            # If config was modified, save it back
            if modified:
                print("Configuration structure was repaired and missing fields were added")
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
            
            return config
        except json.JSONDecodeError:
            print(f"Warning: {CONFIG_FILE_PATH} exists but is not valid JSON. Creating default.")
            return default_config
    
    # If no config exists, return default
    return default_config

def save_config(config):
    """Save the configuration to the file with validation."""
    # Validate config before saving
    config, _ = validate_config(config)
    
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
        layer (str): 'l1', 'l2', 'l3', or 'artCommissionHub'
        address (str): The contract address
        contract_name (str, optional): Contract name to update
    """
    config = load_config()
    
    # Update the timestamp
    config["lastUpdated"] = datetime.now().isoformat()
    
    # Ensure network and layer exist
    if network not in config["networks"]:
        config["networks"][network] = get_default_config()["networks"]["testnet"]
        print(f"Created missing network '{network}' in configuration")
    
    if layer not in config["networks"][network]:
        config["networks"][network][layer] = get_default_config()["networks"]["testnet"][layer]
        print(f"Created missing layer '{layer}' in network '{network}'")
    
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
        layer (str): 'l1', 'l2', 'l3', or 'artCommissionHub'
        
    Returns:
        str: The contract address or empty string if not found
    """
    config = load_config()
    
    # Handle missing network or layer gracefully
    if network not in config["networks"]:
        print(f"Network '{network}' not found in configuration")
        return ""
    
    if layer not in config["networks"][network]:
        print(f"Layer '{layer}' not found in network '{network}'")
        return ""
    
    return config["networks"][network][layer]["address"]

def get_all_contracts():
    """Get all contract configurations."""
    return load_config()

if __name__ == "__main__":
    # Test the functionality
    update_contract_address("testnet", "l1", "0x123456789abcdef")
    print(get_contract_address("testnet", "l1")) 