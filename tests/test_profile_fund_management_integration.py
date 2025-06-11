import pytest
from ape import accounts, project

# Helper function to get edition address - simplified and more reliable
def get_edition_address_reliable(artist_sales, tx, initial_count):
    """Get edition address using a reliable method - check the ERC1155 list using O(1) operations"""
    try:
        # First try to get return value if available
        if hasattr(tx, 'return_value') and tx.return_value is not None and tx.return_value != "0x0000000000000000000000000000000000000000":
            return tx.return_value
        
        # Most reliable fallback: check if a new ERC1155 was added using O(1) operations
        current_count = artist_sales.artistErc1155sToSellCount()
        if current_count > initial_count:
            # Return the latest one using O(1) index access (should be the one we just created)
            return artist_sales.getArtistErc1155AtIndex(current_count - 1)
            
    except Exception:
        pass
    
    return None

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1NEdUZvQ0FBQUFBMUpSRUZVZU5xVEVFRUFBQUE1VVBBRHhpVXFJVzRBQUFBQlNVVk9SSzVDWUlJPSJ9"
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    """Setup fixture for Profile fund management integration tests"""
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    collector = accounts.test_accounts[2]
    
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
    
    # Create profiles
    profile_factory_and_registry.createProfile(artist.address, sender=deployer)
    profile_factory_and_registry.createProfile(collector.address, sender=deployer)
    
    # Get profile addresses and instances
    artist_profile_address = profile_factory_and_registry.getProfile(artist.address)
    collector_profile_address = profile_factory_and_registry.getProfile(collector.address)
    artist_profile = project.Profile.at(artist_profile_address)
    collector_profile = project.Profile.at(collector_profile_address)
    
    # Set artist status for the artist profile
    artist_profile.setIsArtist(True, sender=artist)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "collector": collector,
        "artist_profile": artist_profile,
        "collector_profile": collector_profile,
        "art_piece_template": art_piece_template,
        "profile_factory_and_registry": profile_factory_and_registry
    }

def test_art_sales_funds_go_to_artist_profile(setup):
    """Test that art sales proceeds go to the artist's Profile and can be withdrawn"""
    artist = setup["artist"]
    collector = setup["collector"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Artist creates an art piece
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,  # As artist
        artist.address,  # Personal piece
        TEST_AI_GENERATED,
        ZERO_ADDRESS,  # No commission hub
        False,  # Not profile art
        sender=artist
    )
    
    # Get the created art piece
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    art_piece_address = art_pieces[0]
    
    # Create an edition from the art piece
    edition_name = "Test Edition"
    edition_symbol = "TEST"
    mint_price_wei = 10000000000000000  # 0.01 ETH in wei
    max_supply = 100
    royalty_percent = 300  # 3%
    
    # Get initial ERC1155 count for reliable edition address extraction
    art_sales_address = artist_profile.artSales1155()
    art_sales = project.ArtSales1155.at(art_sales_address)
    initial_count = art_sales.artistErc1155sToSellCount()
    
    edition_tx = artist_profile.createArtEdition(
        art_piece_address,
        edition_name,
        edition_symbol,
        mint_price_wei,
        max_supply,
        royalty_percent,
        sender=artist
    )
    
    # Get edition address using reliable method
    edition_address = get_edition_address_reliable(art_sales, edition_tx, initial_count)
    assert edition_address is not None and edition_address != ZERO_ADDRESS, "Failed to get edition address"
    
    # Verify proceeds address is set to the artist's profile
    proceeds_address = art_sales.getArtistProceedsAddress()
    assert proceeds_address == artist_profile.address
    
    # Get the edition contract
    edition = project.ArtEdition1155.at(edition_address)
    
    # Verify edition's proceeds address is also the artist's profile
    edition_proceeds_address = edition.proceedsAddress()
    assert edition_proceeds_address == artist_profile.address
    
    # Start the sale
    art_sales.startSaleForEdition(edition_address, sender=artist)
    
    # Check initial Profile balances
    initial_profile_balance = artist_profile.getAvailableEthBalance()
    initial_artist_balance = artist.balance
    
    # Collector mints 2 tokens
    mint_amount = 2
    total_cost = mint_price_wei * mint_amount
    
    # Mint tokens with ETH payment
    tx = edition.mint(mint_amount, value=total_cost, sender=collector)
    
    # Check that ETH went to the artist's profile
    final_profile_balance = artist_profile.getAvailableEthBalance()
    
    assert final_profile_balance == initial_profile_balance + total_cost
    
    # Artist withdraws the funds
    artist_profile.withdrawEth(sender=artist)
    
    # Check artist received the funds and profile is empty  
    final_artist_balance = artist.balance
    balance_increase = final_artist_balance - initial_artist_balance
    # Account for gas costs - should receive close to total_cost but may be slightly less due to gas
    assert balance_increase > total_cost * 0.99  # Allow for gas costs
    assert balance_increase <= total_cost  # But not more than what was withdrawn
    assert artist_profile.getAvailableEthBalance() == 0  # Profile is empty

def test_multiple_sales_accumulate_in_profile(setup):
    """Test that multiple sales accumulate ETH in the artist's Profile"""
    artist = setup["artist"]
    collector = setup["collector"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Artist creates an art piece and edition
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Multiple Sales Art",
        "Art for testing multiple sales",
        True,  # As artist
        artist.address,  # Personal piece
        False,
        ZERO_ADDRESS,
        False,
        sender=artist
    )
    
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    art_piece_address = art_pieces[0]
    
    mint_price_wei = 5000000000000000  # 0.005 ETH
    max_supply = 1000
    
    # Get initial ERC1155 count for reliable edition address extraction
    art_sales_address = artist_profile.artSales1155()
    art_sales = project.ArtSales1155.at(art_sales_address)
    initial_count = art_sales.artistErc1155sToSellCount()
    
    edition_tx = artist_profile.createArtEdition(
        art_piece_address,
        "Multi Sale Edition",
        "MULTI",
        mint_price_wei,
        max_supply,
        500,  # 5% royalty
        sender=artist
    )
    
    # Get edition address using reliable method
    edition_address = get_edition_address_reliable(art_sales, edition_tx, initial_count)
    assert edition_address is not None and edition_address != ZERO_ADDRESS, "Failed to get edition address"
    
    # Start the sale
    art_sales_address = artist_profile.artSales1155()
    art_sales = project.ArtSales1155.at(art_sales_address)
    art_sales.startSaleForEdition(edition_address, sender=artist)
    
    edition = project.ArtEdition1155.at(edition_address)
    
    # Track initial balances
    initial_profile_balance = artist_profile.getAvailableEthBalance()
    total_expected_income = 0
    
    # Make multiple purchases
    purchases = [1, 3, 2, 5]  # Different amounts
    
    for i, amount in enumerate(purchases):
        cost = mint_price_wei * amount
        total_expected_income += cost
        
        # Mint tokens with ETH payment
        edition.mint(amount, value=cost, sender=collector)
        
        # Check profile balance after each purchase
        current_balance = artist_profile.getAvailableEthBalance()
        expected_balance = initial_profile_balance + total_expected_income
        assert current_balance == expected_balance
    
    # Check final balance
    final_balance = artist_profile.getAvailableEthBalance()
    assert final_balance == total_expected_income
    
    # Artist withdraws all funds (only option available)
    artist_profile.withdrawEth(sender=artist)
    
    # Check all funds were withdrawn
    assert artist_profile.getAvailableEthBalance() == 0

def test_artist_can_withdraw_to_different_address(setup):
    """Test that artist can withdraw proceeds to a different address"""
    artist = setup["artist"]
    collector = setup["collector"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    deployer = setup["deployer"]  # Will be the recipient
    
    # Setup art piece and edition
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Withdrawal Test Art",
        "Testing withdrawal to different address",
        True,
        artist.address,
        False,
        ZERO_ADDRESS,
        False,
        sender=artist
    )
    
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    art_piece_address = art_pieces[0]
    
    mint_price_wei = 20000000000000000  # 0.02 ETH
    
    # Get initial ERC1155 count for reliable edition address extraction
    art_sales_address = artist_profile.artSales1155()
    art_sales = project.ArtSales1155.at(art_sales_address)
    initial_count = art_sales.artistErc1155sToSellCount()
    
    edition_tx = artist_profile.createArtEdition(
        art_piece_address,
        "Withdrawal Edition",
        "WDRAW",
        mint_price_wei,
        50,
        250,  # 2.5% royalty
        sender=artist
    )
    
    # Get edition address using reliable method
    edition_address = get_edition_address_reliable(art_sales, edition_tx, initial_count)
    assert edition_address is not None and edition_address != ZERO_ADDRESS, "Failed to get edition address"
    
    # Start sale and make purchase
    art_sales.startSaleForEdition(edition_address, sender=artist)
    
    edition = project.ArtEdition1155.at(edition_address)
    
    # Collector buys tokens
    mint_amount = 3
    total_cost = mint_price_wei * mint_amount
    
    # Mint tokens with ETH payment
    edition.mint(mint_amount, value=total_cost, sender=collector)
    
    # Verify funds are in profile
    assert artist_profile.getAvailableEthBalance() == total_cost
    
    # Track deployer's initial balance
    initial_deployer_balance = deployer.balance
    
    # Artist withdraws to deployer's address
    artist_profile.withdrawEth(deployer.address, sender=artist)
    
    # Check that deployer received the funds
    final_deployer_balance = deployer.balance
    assert final_deployer_balance == initial_deployer_balance + total_cost
    
    # Check profile is empty
    assert artist_profile.getAvailableEthBalance() == 0

def test_only_artist_can_withdraw_profile_funds(setup):
    """Test that only the artist (profile owner) can withdraw funds"""
    artist = setup["artist"]
    collector = setup["collector"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Setup and make a sale
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Access Control Art",
        "Testing access control",
        True,
        artist.address,
        False,
        ZERO_ADDRESS,
        False,
        sender=artist
    )
    
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    art_piece_address = art_pieces[0]
    
    mint_price_wei = 15000000000000000  # 0.015 ETH
    
    # Get initial ERC1155 count for reliable edition address extraction
    art_sales_address = artist_profile.artSales1155()
    art_sales = project.ArtSales1155.at(art_sales_address)
    initial_count = art_sales.artistErc1155sToSellCount()
    
    edition_tx = artist_profile.createArtEdition(
        art_piece_address,
        "Access Control Edition",
        "ACCESS",
        mint_price_wei,
        100,
        1000,  # 10% royalty
        sender=artist
    )
    
    # Get edition address using reliable method
    edition_address = get_edition_address_reliable(art_sales, edition_tx, initial_count)
    assert edition_address is not None and edition_address != ZERO_ADDRESS, "Failed to get edition address"
    
    # Start sale and make purchase
    art_sales.startSaleForEdition(edition_address, sender=artist)
    
    edition = project.ArtEdition1155.at(edition_address)
    
    total_cost = mint_price_wei * 2
    
    # Mint tokens with ETH payment
    edition.mint(2, value=total_cost, sender=collector)
    
    # Verify funds are in profile
    assert artist_profile.getAvailableEthBalance() == total_cost
    
    # Collector tries to withdraw - should fail
    with pytest.raises(Exception, match="Only owner can withdraw ETH"):
        artist_profile.withdrawEth(sender=collector)
    
    # Artist can withdraw successfully
    artist_profile.withdrawEth(sender=artist)
    assert artist_profile.getAvailableEthBalance() == 0

def test_proceeds_address_verification(setup):
    """Test that proceeds addresses are correctly set throughout the system"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create art piece and edition
    artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Proceeds Test Art",
        "Testing proceeds address setup",
        True,
        artist.address,
        False,
        ZERO_ADDRESS,
        False,
        sender=artist
    )
    
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    art_piece_address = art_pieces[0]
    
    # Get initial ERC1155 count for reliable edition address extraction
    art_sales_address = artist_profile.artSales1155()
    art_sales = project.ArtSales1155.at(art_sales_address)
    initial_count = art_sales.artistErc1155sToSellCount()
    
    edition_tx = artist_profile.createArtEdition(
        art_piece_address,
        "Proceeds Edition",
        "PROC",
        1000000000000000,  # 0.001 ETH
        1000,
        100,  # 1% royalty
        sender=artist
    )
    
    # Get edition address using reliable method
    edition_address = get_edition_address_reliable(art_sales, edition_tx, initial_count)
    assert edition_address is not None and edition_address != ZERO_ADDRESS, "Failed to get edition address"
    
    # Verify the chain of proceeds addresses
    # 1. ArtSales1155 should have profile as proceeds address
    assert art_sales.getArtistProceedsAddress() == artist_profile.address
    
    # 2. Edition should get proceeds address from ArtSales1155
    edition = project.ArtEdition1155.at(edition_address)
    assert edition.proceedsAddress() == artist_profile.address
    
    # 3. Profile should be able to receive ETH
    assert artist_profile.getAvailableEthBalance() == 0  # Initially empty
    
    # Send test ETH directly to profile to verify it can receive
    test_amount = 1000000000000000000  # 1 ETH
    artist.transfer(artist_profile.address, test_amount)
    
    assert artist_profile.getAvailableEthBalance() == test_amount 