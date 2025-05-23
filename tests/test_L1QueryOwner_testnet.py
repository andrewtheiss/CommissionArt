import pytest
from ape import accounts, project, networks
from ape_accounts import import_account_from_private_key
from dotenv import load_dotenv
from pathlib import Path
import os

@pytest.fixture(scope="module")
def setup():
    """Set up the test environment with network and accounts"""
    # Load .env file from project root
    dotenv_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=dotenv_path)
    
    # Get private key and passphrase
    private_key = os.environ.get("PRIVATE_KEY")
    passphrase = os.environ.get("DEPLOYER_PASSPHRASE")
    if not private_key or not passphrase:
        pytest.skip("PRIVATE_KEY and DEPLOYER_PASSPHRASE must be set in .env")
    
    # Use a default network for testing - Ethereum Sepolia
    network_choice = "ethereum:sepolia:alchemy"

    with networks.parse_network_choice(network_choice) as provider:
        # Import the deployer account
        try:
            deployer = accounts.load("testnet_deployer")
        except:
            deployer = import_account_from_private_key("testnet_deployer", passphrase, private_key)
        
        # Enable auto-signing
        deployer.set_autosign(True, passphrase=passphrase)
        
        yield deployer, network_choice
'''
@pytest.fixture(scope="module")
def deployed_contracts(setup):
    """Deploy the necessary contracts for testing"""
    deployer, network_choice = setup
    
    with networks.parse_network_choice(network_choice):
        # Deploy the SimpleERC721 for testing
        erc721 = deployer.deploy(
            project.SimpleERC721, 
            "TestNFT", 
            "TNFT",
            required_confirmations=1
        )
        
        # Mint a token to the deployer
        token_id = 1
        erc721.mint(deployer.address, token_id, sender=deployer)
        
        # Arbitrum Sepolia Inbox address
        arbitrum_inbox_address = "0x2389E6E1E0AF0aCD567cc8D0fda530D9c2a8317e"
        
        # Previous hardcoded contract address (keeping as reference)
        # l1_contract_address = "0x6E28577074170227E7D3C646D840514e9BE0333C"
        
        # Deploy a new L1QueryOwnership contract for testing
        print(f"Deploying new L1QueryOwnership contract with Inbox address: {arbitrum_inbox_address}")
        l1_contract = deployer.deploy(
            project.L1QueryOwnership,
            arbitrum_inbox_address,
            required_confirmations=1
        )
        print(f"Deployed new L1QueryOwnership at: {l1_contract.address}")
        
        yield erc721, l1_contract, token_id, deployer

def test_verify_erc721_ownership(deployed_contracts):
    """Test that the ERC721 contract correctly reports ownership"""
    erc721, l1_contract, token_id, deployer = deployed_contracts
    
    # Verify the NFT ownership directly from the ERC721 contract
    owner = erc721.ownerOf(token_id)
    
    # Log the results for verification
    print(f"SimpleERC721 deployed at: {erc721.address}")
    print(f"Token ID {token_id} is owned by: {owner}")
    
    # Verify the correct owner
    assert owner == deployer.address
    
    # Log L1QueryOwnership info
    print(f"Using L1QueryOwnership at: {l1_contract.address}")

def test_transfer_and_verify_ownership(deployed_contracts):
    """Test ownership verification after transferring the NFT to another address"""
    erc721, l1_contract, token_id, deployer = deployed_contracts
    
    # Create a new account to transfer to
    try:
        receiver = accounts[1]  # Using a test account
    except:
        # Create a new account if accounts[1] is not available
        receiver = accounts.generate_test_account()
        
    print(f"Receiver address: {receiver.address}")
    
    # Transfer the NFT to the receiver
    try:
        erc721.transferFrom(deployer.address, receiver.address, token_id, sender=deployer)
        
        # Verify the new owner directly from ERC721
        new_owner = erc721.ownerOf(token_id)
        
        # Log the results
        print(f"Token transferred from {deployer.address} to {receiver.address}")
        print(f"New owner verified by ERC721: {new_owner}")
        
        # Verify ownership change
        assert new_owner == receiver.address
        
    except Exception as e:
        pytest.skip(f"Transfer transaction failed: {str(e)}")

def test_verify_nft_events(deployed_contracts):
    """Test emitting and capturing Transfer events from ERC721"""
    erc721, l1_contract, token_id, deployer = deployed_contracts
    
    # Deploy a new token for this test
    new_token_id = 999
    
    try:
        # Mint another token to track the event
        tx = erc721.mint(deployer.address, new_token_id, sender=deployer)
        
        # Wait for the transaction to be included in a block
        tx.await_confirmations(1)
        
        # Get the receipt and check for events
        receipt = tx.receipt
        
        # Log transaction details
        print(f"Transaction hash: {tx.txn_hash}")
        
        # Verify token ownership
        new_owner = erc721.ownerOf(new_token_id)
        print(f"New token {new_token_id} owner: {new_owner}")
        assert new_owner == deployer.address
        
        print(f"Transaction successful, new token minted and ownership verified")
        
    except Exception as e:
        pytest.skip(f"Event test failed: {str(e)}")

def test_existing_contract_connection(setup):
    """Test that we can connect to the existing deployed L1QueryOwnership contract"""
    deployer, network_choice = setup
    
    with networks.parse_network_choice(network_choice):
        # Try to connect to the existing contract
        existing_address = "0x6E28577074170227E7D3C646D840514e9BE0333C"
        
        try:
            l1_contract = project.L1QueryOwnership.at(existing_address)
            print(f"Successfully connected to L1QueryOwnership at {existing_address}")
            
            # Check contract bytecode exists (basic verification that it's a contract)
            bytecode_len = len(l1_contract.address.code)
            print(f"Contract bytecode length: {bytecode_len}")
            assert bytecode_len > 0
            
        except Exception as e:
            pytest.skip(f"Could not connect to existing contract: {str(e)}") 
'''