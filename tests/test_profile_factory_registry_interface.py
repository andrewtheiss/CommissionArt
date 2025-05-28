import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user1 = accounts.test_accounts[1]
    user2 = accounts.test_accounts[2]
    
    # Deploy all required templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with all three required templates
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        commission_hub_template.address,
        sender=deployer
    )
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        project.ArtPiece.deploy(sender=deployer).address,  # art_piece_template for verification
        sender=deployer
    )
    
    # Link factory and hub owners
    profile_factory.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    
    # Create a generic commission hub for testing
    tx = art_commission_hub_owners.createGenericCommissionHub(deployer.address, sender=deployer)
    commission_hub_address = tx.return_value
    commission_hub = project.ArtCommissionHub.at(commission_hub_address)
    
    # Create profiles for users
    profile_factory.createProfile(user1.address, sender=deployer)
    profile_factory.createProfile(user2.address, sender=deployer)
    
    # Get the created profiles
    user1_profile = profile_factory.getProfile(user1.address)
    user2_profile = profile_factory.getProfile(user2.address)
    
    return {
        "deployer": deployer,
        "user1": user1,
        "user2": user2,
        "profile_factory": profile_factory,
        "user1_profile": user1_profile,
        "user2_profile": user2_profile,
        "commission_hub": commission_hub,
        "art_commission_hub_owners": art_commission_hub_owners
    }

def test_get_profile_by_owner(setup):
    """Test that getProfile returns the correct profile address"""
    # Arrange
    user1 = setup["user1"]
    user2 = setup["user2"]
    profile_factory = setup["profile_factory"]
    user1_profile = setup["user1_profile"]
    user2_profile = setup["user2_profile"]
    
    # Act & Assert - Get profile for user1
    retrieved_profile = profile_factory.getProfile(user1.address)
    assert retrieved_profile == user1_profile, "Should return user1's profile"
    
    # Act & Assert - Get profile for user2
    retrieved_profile = profile_factory.getProfile(user2.address)
    assert retrieved_profile == user2_profile, "Should return user2's profile"
    
    # Act & Assert - Get profile for non-existent user
    non_existent_user = accounts.test_accounts[3]  # Use a different account that doesn't have a profile
    retrieved_profile = profile_factory.getProfile(non_existent_user.address)
    assert retrieved_profile == "0x0000000000000000000000000000000000000000", "Should return zero address for non-existent profile"

def test_get_profile_by_owner_in_profile_context(setup):
    """Test that a Profile contract can use getProfile to find another profile"""
    # Arrange
    user1 = setup["user1"]
    user2 = setup["user2"]
    profile_factory = setup["profile_factory"]
    user1_profile = setup["user1_profile"]
    user2_profile = setup["user2_profile"]
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=setup["deployer"])
    commission_hub = setup["commission_hub"]
    
    # Create a commission art piece from user1 to user2
    user1_profile_contract = project.Profile.at(user1_profile)
    user2_profile_contract = project.Profile.at(user2_profile)
    
    # Whitelist user2 on user1's profile to allow commission linking
    user1_profile_contract.addToWhitelist(user2.address, sender=user1)
    user2_profile_contract.addToWhitelist(user1.address, sender=user2)
    
    art_piece_tx = user1_profile_contract.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # is_artist
        user2.address,  # other_party (commissioner)
        False,  # ai_generated
        commission_hub.address,  # Use the commission hub
        False,  # is_profile_art
        sender=user1
    )
    
    # Get the actual art piece address from the profile's myArt list
    art_piece_address = user1_profile_contract.getArtPieceAtIndex(user1_profile_contract.myArtCount() - 1)
    
    # Get user2's profile contract
    user2_profile_contract = project.Profile.at(user2_profile)
    
    # Manually link the commission to user1's profile since automatic linking only links to other party
    user1_profile_contract.linkArtPieceAsMyCommission(art_piece_address, sender=user1)
    
    # With whitelisting, the commission should go directly to verified list
    user1_verified = user1_profile_contract.getCommissionsByOffset(0, 10, False)
    user2_verified = user2_profile_contract.getCommissionsByOffset(0, 10, False)
    
    # Since both parties are whitelisted, the commission should be in verified lists
    assert art_piece_address in user1_verified, "Should be in user1's verified list due to whitelisting"
    assert art_piece_address in user2_verified, "Should be in user2's verified list due to whitelisting"

def test_profile_factory_registry_interface_in_verification(setup):
    """Test that the ProfileFactoryAndRegistry interface is used correctly in the verification process"""
    # Arrange
    user1 = setup["user1"]
    user2 = setup["user2"]
    profile_factory = setup["profile_factory"]
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=setup["deployer"])
    commission_hub = setup["commission_hub"]
    
    # Create user profiles
    user1_profile_contract = project.Profile.at(setup["user1_profile"])
    user2_profile_contract = project.Profile.at(setup["user2_profile"])
    
    # Set user1 as artist
    user1_profile_contract.setIsArtist(True, sender=user1)
    
    # Whitelist each other to allow commission linking
    user1_profile_contract.addToWhitelist(user2.address, sender=user1)
    user2_profile_contract.addToWhitelist(user1.address, sender=user2)
    
    # Create a commission art piece from user1 to user2
    art_piece_tx = user1_profile_contract.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # is_artist
        user2.address,  # other_party (commissioner)
        False,  # ai_generated
        commission_hub.address,  # Use the commission hub
        False,  # is_profile_art
        sender=user1
    )
    
    # Get the actual art piece address from the profile's myArt list
    art_piece_address = user1_profile_contract.getArtPieceAtIndex(user1_profile_contract.myArtCount() - 1)
    
    # Manually link the commission to user1's profile since automatic linking only links to other party
    user1_profile_contract.linkArtPieceAsMyCommission(art_piece_address, sender=user1)
    
    # With whitelisting, the commission should go directly to verified list
    user1_verified = user1_profile_contract.getCommissionsByOffset(0, 10, False)
    user2_verified = user2_profile_contract.getCommissionsByOffset(0, 10, False)
    
    # Since both parties are whitelisted, the commission should be in verified lists
    assert art_piece_address in user1_verified, "Should be in user1's verified list due to whitelisting"
    assert art_piece_address in user2_verified, "Should be in user2's verified list due to whitelisting"
    
def test_profile_factory_registry_cross_profile_updates(setup):
    """Test that the ProfileFactoryAndRegistry enables cross-profile updates during verification"""
    # Arrange
    user1 = setup["user1"]
    user2 = setup["user2"]
    deployer = setup["deployer"]
    
    # Create user profiles
    user1_profile_contract = project.Profile.at(setup["user1_profile"])
    user2_profile_contract = project.Profile.at(setup["user2_profile"])
    
    # Set user1 as artist
    user1_profile_contract.setIsArtist(True, sender=user1)
    
    # Whitelist each other to allow commission linking
    user1_profile_contract.addToWhitelist(user2.address, sender=user1)
    user2_profile_contract.addToWhitelist(user1.address, sender=user2)
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Create a commission art piece directly (not through profile)
    commission_hub = setup["commission_hub"]
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Cross Profile Test",
        "Test Description",
        user2.address,  # commissioner_input
        user1.address,  # artist_input
        commission_hub.address,  # Use the commission hub
        False,  # ai_generated
        user1.address,  # original_uploader (need to specify this)
        setup["profile_factory"].address,  # profile_factory_address (need to specify this)
        sender=deployer
    )
    
    # Add to both profiles
    user1_profile_contract.linkArtPieceAsMyCommission(art_piece.address, sender=user1)
    user2_profile_contract.linkArtPieceAsMyCommission(art_piece.address, sender=user2)
    
    # With whitelisting, the commission should already be in verified lists
    user1_verified = user1_profile_contract.getCommissionsByOffset(0, 10, False)
    user2_verified = user2_profile_contract.getCommissionsByOffset(0, 10, False)
    assert art_piece.address in user1_verified, "Should be in user1's verified list due to whitelisting"
    assert art_piece.address in user2_verified, "Should be in user2's verified list due to whitelisting" 