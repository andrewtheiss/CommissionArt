from ape import accounts, project, networks
from ape_accounts import import_account_from_private_key
from dotenv import load_dotenv
from pathlib import Path
import os

def deploy_contracts():
    # Load .env file
    dotenv_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=dotenv_path)

    # Choose network
    network_choice = input("Enter network (local, testnet, production): ").strip().lower()
    if network_choice == "local":
        l1_network = "ethereum:local"
        l2_network = "arbitrum:local"
    elif network_choice == "testnet":
        l1_network = "ethereum:sepolia:alchemy"
        l2_network = "arbitrum:sepolia:alchemy"
    elif network_choice == "production":
        l1_network = "ethereum:mainnet:alchemy"
        l2_network = "arbitrum:mainnet:alchemy"
    else:
        raise ValueError("Invalid network choice")

    # Load or import deployer account
    private_key = os.environ.get("PRIVATE_KEY")
    passphrase = os.environ.get("DEPLOYER_PASSPHRASE")
    if not private_key or not passphrase:
        raise ValueError("PRIVATE_KEY and DEPLOYER_PASSPHRASE must be set in .env")

    try:
        deployer = accounts.load("deployer")
    except:
        deployer = import_account_from_private_key("deployer", passphrase, private_key)
    deployer.set_autosign(True, passphrase=passphrase)

    # Prompt for using existing L1 contract
    use_existing = input("Use existing L1 contract? (y/N): ").strip().lower()
    
    # Deploy or use existing L1 contract on Ethereum
    with networks.parse_network_choice(l1_network) as provider:
        if use_existing == 'y':
            l1_contract_address = "0x6E28577074170227E7D3C646D840514e9BE0333C"
            print(f"Using existing L1QueryOwner at: {l1_contract_address}")
            l1_contract = project.L1QueryOwner.at(l1_contract_address)
        else:
            print(f"Deploying L1QueryOwner on {l1_network}")
            l1_contract = deployer.deploy(project.L1QueryOwner, required_confirmations=1)
            print(f"L1QueryOwner deployed at: {l1_contract.address}")

    # Prompt for using existing L2 contract
    use_existing_l2 = input("Use existing L2 contract? (y/N): ").strip().lower()

    # Prompt for initial_l3_contract for L2 (only needed for new L2 deployment)
    initial_l3_contract = "0x0000000000000000000000000000000000000000"
    if use_existing_l2 != 'y':
        initial_l3_contract_input = input("Enter initial_l3_contract address (or press Enter for zero address): ").strip()
        if initial_l3_contract_input:
            initial_l3_contract = initial_l3_contract_input

    # Deploy or use existing L2 contract on Arbitrum
    with networks.parse_network_choice(l2_network) as provider:
        if use_existing_l2 == 'y':
            l2_contract_address = "0x2097c9cD16fcbBeB112db40D058f013c90C019f8"
            print(f"Using existing L2Relay at: {l2_contract_address}")
            l2_contract = project.L2Relay.at(l2_contract_address)
        else:
            print(f"Deploying L2Relay on {l2_network}")
            l2_contract = deployer.deploy(project.L2Relay, l1_contract.address, initial_l3_contract, required_confirmations=0)
            print(f"L2Relay deployed at: {l2_contract.address}")

    return l1_contract, l2_contract

def main():
    deploy_contracts()

if __name__ == "__main__":
    main()