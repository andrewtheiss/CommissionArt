import pytest
from ape import accounts, project
import time

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

def create_unique_test_token(deployer, test_name=""):
    """Create a unique ERC20 token for each test to avoid file locking issues"""
    # Use timestamp and test name to ensure uniqueness
    timestamp = str(int(time.time() * 1000000))  # Microsecond precision
    unique_name = f"TestToken_{test_name}_{timestamp}"
    unique_symbol = f"TEST_{timestamp[-6:]}"  # Last 6 digits of timestamp
    
    return project.MockERC20.deploy(unique_name, unique_symbol, 18, sender=deployer)

@pytest.fixture
def setup():
    """Setup fixture for Profile fund management tests"""
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    profile_owner = accounts.test_accounts[1]
    other_user = accounts.test_accounts[2]
    recipient = accounts.test_accounts[3]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with all templates
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, 
        profile_social_template.address, 
        commission_hub_template.address, 
        art_edition_1155_template.address, 
        art_sales_1155_template.address,
        sender=deployer
    )
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Link factory and hub owners
    profile_factory_and_registry.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory_and_registry.address, sender=deployer)
    
    # Create profile for the owner
    profile_factory_and_registry.createProfile(profile_owner.address, sender=deployer)
    
    # Get profile address and instance
    profile_address = profile_factory_and_registry.getProfile(profile_owner.address)
    profile = project.Profile.at(profile_address)
    
    # DON'T deploy test_token here - let each test create its own unique instance
    
    return {
        "deployer": deployer,
        "profile_owner": profile_owner,
        "other_user": other_user,
        "recipient": recipient,
        "profile": profile,
        "profile_factory_and_registry": profile_factory_and_registry,
        "create_test_token": lambda test_name="": create_unique_test_token(deployer, test_name)
    }

def test_profile_receives_eth(setup):
    """Test that Profile can receive ETH payments"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    other_user = setup["other_user"]
    
    # Initial balances
    initial_profile_balance = profile.balance
    
    # Send ETH to profile
    amount_to_send = 1000000000000000000  # 1 ETH in wei
    other_user.transfer(profile.address, amount_to_send)
    
    # Check balances updated correctly
    assert profile.balance == initial_profile_balance + amount_to_send
    assert profile.getAvailableEthBalance() == amount_to_send

def test_profile_receives_multiple_eth_payments(setup):
    """Test that Profile correctly accumulates multiple ETH payments"""
    profile = setup["profile"]
    other_user = setup["other_user"]
    deployer = setup["deployer"]
    
    # Send multiple payments
    payment1 = 500000000000000000  # 0.5 ETH
    payment2 = 300000000000000000  # 0.3 ETH
    payment3 = 200000000000000000  # 0.2 ETH
    
    other_user.transfer(profile.address, payment1)
    deployer.transfer(profile.address, payment2)
    other_user.transfer(profile.address, payment3)
    
    total_expected = payment1 + payment2 + payment3
    
    # Check totals
    assert profile.getAvailableEthBalance() == total_expected
    assert profile.balance == total_expected

def test_withdraw_eth_by_owner(setup):
    """Test that profile owner can withdraw all ETH"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    other_user = setup["other_user"]
    
    # Send ETH to profile
    amount_to_send = 2000000000000000000  # 2 ETH
    other_user.transfer(profile.address, amount_to_send)
    
    # Check initial state
    assert profile.getAvailableEthBalance() == amount_to_send
    initial_owner_balance = profile_owner.balance
    
    # Owner withdraws all ETH (new interface only supports withdrawing all)
    tx = profile.withdrawEth(sender=profile_owner)
    
    # Check balances after withdrawal (all ETH should be withdrawn)
    assert profile.getAvailableEthBalance() == 0
    
    # Check that owner received the ETH (account for gas costs)
    final_owner_balance = profile_owner.balance
    balance_increase = final_owner_balance - initial_owner_balance
    # The balance increase should be close to the amount sent, but may be slightly less due to gas
    assert balance_increase > amount_to_send * 0.99  # Allow for gas costs
    assert balance_increase <= amount_to_send  # But not more than what was sent
    
    # Check event was emitted - TokenWithdrawn with empty address for ETH
    events = tx.events
    assert len(events) > 0
    
    # Find the TokenWithdrawn event
    token_withdrawn_event = None
    for event in events:
        if hasattr(event, 'token'):
            token_withdrawn_event = event
            break
    
    assert token_withdrawn_event is not None
    assert token_withdrawn_event.token == "0x0000000000000000000000000000000000000000"  # Empty address for ETH

def test_withdraw_eth_to_different_recipient(setup):
    """Test withdrawing all ETH to a different recipient"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    recipient = setup["recipient"]
    other_user = setup["other_user"]
    
    # Send ETH to profile
    amount_to_send = 1000000000000000000  # 1 ETH
    other_user.transfer(profile.address, amount_to_send)
    
    initial_recipient_balance = recipient.balance
    
    # Owner withdraws all ETH to different recipient
    tx = profile.withdrawEth(recipient.address, sender=profile_owner)
    
    # Check balances (all ETH should be withdrawn)
    assert profile.getAvailableEthBalance() == 0
    assert recipient.balance == initial_recipient_balance + amount_to_send
    
    # Check event - TokenWithdrawn with empty address for ETH
    events = tx.events
    token_withdrawn_event = None
    for event in events:
        if hasattr(event, 'token'):
            token_withdrawn_event = event
            break
    
    assert token_withdrawn_event is not None
    assert token_withdrawn_event.token == "0x0000000000000000000000000000000000000000"  # Empty address for ETH

def test_withdraw_all_eth_to_different_recipient(setup):
    """Test withdrawing all ETH to a different recipient"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    recipient = setup["recipient"]
    other_user = setup["other_user"]
    
    # Send ETH to profile
    amount_to_send = 800000000000000000  # 0.8 ETH
    other_user.transfer(profile.address, amount_to_send)
    
    initial_recipient_balance = recipient.balance
    
    # Withdraw all ETH to recipient
    profile.withdrawEth(recipient.address, sender=profile_owner)
    
    # Check balances
    assert profile.getAvailableEthBalance() == 0
    assert recipient.balance == initial_recipient_balance + amount_to_send

def test_only_owner_can_withdraw_eth(setup):
    """Test that only profile owner can withdraw ETH"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    other_user = setup["other_user"]
    
    # Send ETH to profile
    amount_to_send = 1000000000000000000  # 1 ETH
    other_user.transfer(profile.address, amount_to_send)
    
    # Other user tries to withdraw - should fail
    with pytest.raises(Exception, match="Only owner can withdraw ETH"):
        profile.withdrawEth(sender=other_user)
    
    # Profile owner can withdraw successfully
    profile.withdrawEth(sender=profile_owner)
    assert profile.getAvailableEthBalance() == 0

def test_withdraw_eth_with_no_balance_fails(setup):
    """Test that withdrawing ETH fails when balance is zero"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    
    # Profile has no ETH
    assert profile.getAvailableEthBalance() == 0
    
    # Try to withdraw when balance is zero
    with pytest.raises(Exception, match="No ETH to withdraw"):
        profile.withdrawEth(sender=profile_owner)

def test_erc20_token_withdrawal(setup):
    """Test ERC20 token withdrawal functionality"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    test_token = setup["create_test_token"]("erc20_withdrawal")  # Create unique token for this test
    deployer = setup["deployer"]
    
    # Mint tokens to deployer first
    token_amount = 1000000000000000000000  # 1000 tokens
    test_token.mint(deployer.address, token_amount, sender=deployer)
    
    # Transfer tokens to profile
    transfer_amount = 500000000000000000000  # 500 tokens
    test_token.transfer(profile.address, transfer_amount, sender=deployer)
    
    # Check profile has tokens
    assert profile.getTokenBalance(test_token.address) == transfer_amount
    
    # Owner withdraws all tokens
    initial_owner_balance = test_token.balanceOf(profile_owner.address)
    
    tx = profile.withdrawTokens(test_token.address, sender=profile_owner)
    
    # Check balances (all tokens should be withdrawn)
    assert profile.getTokenBalance(test_token.address) == 0
    assert test_token.balanceOf(profile_owner.address) == initial_owner_balance + transfer_amount
    
    # Check event was emitted - TokenWithdrawn with the token address
    events = tx.events
    token_withdrawn_event = None
    for event in events:
        if hasattr(event, 'token'):
            token_withdrawn_event = event
            break
    
    assert token_withdrawn_event is not None
    assert token_withdrawn_event.token == test_token.address

def test_withdraw_tokens_basic(setup):
    """Test basic token withdrawal functionality"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    test_token = setup["create_test_token"]("withdraw_basic")  # Create unique token for this test
    deployer = setup["deployer"]
    
    # Mint and transfer tokens to profile
    token_amount = 750000000000000000000  # 750 tokens
    test_token.mint(deployer.address, token_amount, sender=deployer)
    test_token.transfer(profile.address, token_amount, sender=deployer)
    
    initial_owner_balance = test_token.balanceOf(profile_owner.address)
    
    # Withdraw all tokens (only option available)
    tx = profile.withdrawTokens(test_token.address, sender=profile_owner)
    
    # Check all tokens were withdrawn
    assert profile.getTokenBalance(test_token.address) == 0
    assert test_token.balanceOf(profile_owner.address) == initial_owner_balance + token_amount

def test_withdraw_tokens_to_different_recipient(setup):
    """Test withdrawing all ERC20 tokens to a different recipient"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    recipient = setup["recipient"]
    test_token = setup["create_test_token"]("different_recipient")  # Create unique token for this test
    deployer = setup["deployer"]
    
    # Setup tokens
    token_amount = 400000000000000000000  # 400 tokens
    test_token.mint(deployer.address, token_amount, sender=deployer)
    test_token.transfer(profile.address, token_amount, sender=deployer)
    
    initial_recipient_balance = test_token.balanceOf(recipient.address)
    
    # Withdraw all tokens to different recipient
    profile.withdrawTokens(test_token.address, recipient.address, sender=profile_owner)
    
    # Check balances (all tokens should be withdrawn)
    assert test_token.balanceOf(recipient.address) == initial_recipient_balance + token_amount
    assert profile.getTokenBalance(test_token.address) == 0

def test_only_owner_can_withdraw_tokens(setup):
    """Test that only profile owner can withdraw ERC20 tokens"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    other_user = setup["other_user"]
    test_token = setup["create_test_token"]("only_owner")  # Create unique token for this test
    deployer = setup["deployer"]
    
    # Setup tokens
    token_amount = 300000000000000000000  # 300 tokens
    test_token.mint(deployer.address, token_amount, sender=deployer)
    test_token.transfer(profile.address, token_amount, sender=deployer)
    
    # Other user tries to withdraw tokens - should fail
    with pytest.raises(Exception, match="Only owner can withdraw tokens"):
        profile.withdrawTokens(test_token.address, sender=other_user)
    
    # Profile owner can withdraw successfully
    profile.withdrawTokens(test_token.address, sender=profile_owner)

# Removed test_token_withdrawal_insufficient_balance since we only support withdrawing all tokens

def test_token_withdrawal_invalid_address(setup):
    """Test token withdrawal with invalid token address"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    
    # Try to withdraw from zero address
    with pytest.raises(Exception, match="Invalid token address"):
        profile.withdrawTokens(ZERO_ADDRESS, sender=profile_owner)
    
    # Try to get balance of zero address
    with pytest.raises(Exception, match="Invalid token address"):
        profile.getTokenBalance(ZERO_ADDRESS)

def test_withdraw_tokens_with_no_balance_fails(setup):
    """Test that withdrawing tokens fails when balance is zero"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    test_token = setup["create_test_token"]("no_balance")  # Create unique token for this test
    
    # Profile has no tokens
    assert profile.getTokenBalance(test_token.address) == 0
    
    # Try to withdraw when balance is zero
    with pytest.raises(Exception, match="No tokens to withdraw"):
        profile.withdrawTokens(test_token.address, sender=profile_owner)

def test_eth_balance_tracking_simplified(setup):
    """Test simplified ETH balance tracking"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    other_user = setup["other_user"]
    deployer = setup["deployer"]
    
    # Initial balance should be zero
    assert profile.getAvailableEthBalance() == 0
    
    # Send multiple payments
    payment1 = 1000000000000000000  # 1 ETH
    payment2 = 500000000000000000   # 0.5 ETH
    
    other_user.transfer(profile.address, payment1)
    deployer.transfer(profile.address, payment2)
    
    # Check accumulated balance
    total_expected = payment1 + payment2
    assert profile.getAvailableEthBalance() == total_expected
    
    # Withdraw all ETH (only option available)
    profile.withdrawEth(sender=profile_owner)
    
    # Check balance is now zero
    assert profile.getAvailableEthBalance() == 0

def test_combined_eth_and_token_operations(setup):
    """Test combined ETH and token operations"""
    profile = setup["profile"]
    profile_owner = setup["profile_owner"]
    test_token = setup["create_test_token"]("combined_ops")  # Create unique token for this test
    other_user = setup["other_user"]
    deployer = setup["deployer"]
    
    # Send ETH and tokens to profile
    eth_amount = 2000000000000000000  # 2 ETH
    token_amount = 1000000000000000000000  # 1000 tokens
    
    other_user.transfer(profile.address, eth_amount)
    test_token.mint(deployer.address, token_amount, sender=deployer)
    test_token.transfer(profile.address, token_amount, sender=deployer)
    
    # Check initial balances
    assert profile.getAvailableEthBalance() == eth_amount
    assert profile.getTokenBalance(test_token.address) == token_amount
    
    # Withdraw all of each (only option available)
    profile.withdrawEth(sender=profile_owner)
    profile.withdrawTokens(test_token.address, sender=profile_owner)
    
    # Check everything is withdrawn
    assert profile.getAvailableEthBalance() == 0
    assert profile.getTokenBalance(test_token.address) == 0

def test_eth_balance_accumulation(setup):
    """Test that ETH balance accumulates correctly"""
    profile = setup["profile"]
    other_user = setup["other_user"]
    deployer = setup["deployer"]
    
    # Send ETH payments
    amount1 = 1500000000000000000  # 1.5 ETH
    tx1 = other_user.transfer(profile.address, amount1)
    
    # Check balance after first payment
    assert profile.getAvailableEthBalance() == amount1
    
    # Send another payment
    amount2 = 800000000000000000  # 0.8 ETH
    tx2 = deployer.transfer(profile.address, amount2)
    
    # Check total balance is cumulative
    assert profile.getAvailableEthBalance() == amount1 + amount2 