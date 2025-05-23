import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user1 = accounts.test_accounts[1]
    user2 = accounts.test_accounts[2]
    
    # Deploy ProfileFactoryAndRegistry
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)

    # Deploy ProfileSocial template
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    # Deploy ProfileFactoryAndRegistry with both templates
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        sender=deployer
    )
    
    # Set the template in the factory
    profile_factory.updateProfileTemplateContract(project.Profile.deploy(sender=deployer), sender=deployer)
    
    # Create profiles for users
    profile_factory.createProfile(sender=user1)
    profile_factory.createProfile(sender=user2)
    
    # Get the created profiles
    user1_profile = profile_factory.getProfile(user1.address)
    user2_profile = profile_factory.getProfile(user2.address)
    
    return {
        "deployer": deployer,
        "user1": user1,
        "user2": user2,
        "profile_factory": profile_factory,
        "user1_profile": user1_profile,
        "user2_profile": user2_profile
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
    retrieved_profile = profile_factory.getProfile(setup["deployer"].address)
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
    
    # Create a commission art piece from user1 to user2
    user1_profile_contract = project.Profile(user1_profile)
    art_piece_address = user1_profile_contract.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # is_artist
        user2.address,  # other_party (commissioner)
        False,  # ai_generated
        ZERO_ADDRESS,  # No commission hub
        False,  # is_profile_art
        sender=user1
    )
    
    # Add the commission to user2's profile
    user2_profile_contract = project.Profile(user2_profile)
    user2_profile_contract.addCommission(art_piece_address, sender=user2)
    
    # Act - Both parties verify the commission
    user1_profile_contract.verifyCommission(art_piece_address, sender=user1)
    user2_profile_contract.verifyCommission(art_piece_address, sender=user2)
    
    # Assert - Commission should be in verified list for both profiles
    user1_verified = user1_profile_contract.getCommissions(0, 10)
    user2_verified = user2_profile_contract.getCommissions(0, 10)
    
    assert art_piece_address in user1_verified, "Should be in user1's verified list"
    assert art_piece_address in user2_verified, "Should be in user2's verified list"

def test_profile_factory_registry_interface_in_verification(setup):
    """Test that the ProfileFactoryAndRegistry interface is used correctly in the verification process"""
    # Arrange
    user1 = setup["user1"]
    user2 = setup["user2"]
    profile_factory = setup["profile_factory"]
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=setup["deployer"])
    
    # Create user profiles
    user1_profile_contract = project.Profile(setup["user1_profile"])
    user2_profile_contract = project.Profile(setup["user2_profile"])
    
    # Set user1 as artist
    user1_profile_contract.setIsArtist(True, sender=user1)
    
    # Create a commission art piece from user1 to user2
    art_piece_address = user1_profile_contract.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # is_artist
        user2.address,  # other_party (commissioner)
        False,  # ai_generated
        ZERO_ADDRESS,  # No commission hub
        False,  # is_profile_art
        sender=user1
    )
    
    # Verify the commission is in unverified lists for user1
    user1_unverified = user1_profile_contract.getUnverifiedCommissions(0, 10)
    assert art_piece_address in user1_unverified, "Should be in user1's unverified list"
    
    # Act - User2 verifies the commission (this should find user1's profile through the registry)
    user2_profile_contract.verifyCommission(art_piece_address, sender=user2)
    
    # Act - User1 verifies the commission (this should find user2's profile through the registry)
    user1_profile_contract.verifyCommission(art_piece_address, sender=user1)
    
    # Assert - Commission should be fully verified
    art_piece = project.ArtPiece(art_piece_address)
    assert art_piece.isFullyVerifiedCommission(), "Commission should be fully verified"
    
    # Assert - Commission should be in verified list for both profiles
    user1_verified = user1_profile_contract.getCommissions(0, 10)
    user2_verified = user2_profile_contract.getCommissions(0, 10)
    
    assert art_piece_address in user1_verified, "Should be in user1's verified list"
    assert art_piece_address in user2_verified, "Should be in user2's verified list"
    
    # Assert - Commission should be removed from unverified list for both profiles
    user1_unverified = user1_profile_contract.getUnverifiedCommissions(0, 10)
    user2_unverified = user2_profile_contract.getUnverifiedCommissions(0, 10)
    
    assert art_piece_address not in user1_unverified, "Should not be in user1's unverified list"
    assert art_piece_address not in user2_unverified, "Should not be in user2's unverified list"
    
def test_profile_factory_registry_cross_profile_updates(setup):
    """Test that the ProfileFactoryAndRegistry enables cross-profile updates during verification"""
    # Arrange
    user1 = setup["user1"]
    user2 = setup["user2"]
    deployer = setup["deployer"]
    
    # Create user profiles
    user1_profile_contract = project.Profile(setup["user1_profile"])
    user2_profile_contract = project.Profile(setup["user2_profile"])
    
    # Set user1 as artist
    user1_profile_contract.setIsArtist(True, sender=user1)
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Create a commission art piece directly (not through profile)
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        b"test_data",
        "avif",
        "Cross Profile Test",
        "Test Description",
        user2.address,  # commissioner_input
        user1.address,  # artist_input
        ZERO_ADDRESS,  # No commission hub
        False,  # ai_generated
        sender=deployer
    )
    
    # Add to both profiles
    user1_profile_contract.addCommission(art_piece.address, sender=user1)
    user2_profile_contract.addCommission(art_piece.address, sender=user2)
    
    # Act - User2 verifies the commission
    user2_profile_contract.verifyCommission(art_piece.address, sender=user2)
    
    # Assert - User1's profile should be automatically updated through registry
    # when user1 verifies their side
    user1_profile_contract.verifyCommission(art_piece.address, sender=user1)
    
    # Assert - Commission should be in verified list for both profiles
    user1_verified = user1_profile_contract.getCommissions(0, 10)
    user2_verified = user2_profile_contract.getCommissions(0, 10)
    assert art_piece.address in user1_verified, "Should be in user1's verified list"
    assert art_piece.address in user2_verified, "Should be in user2's verified list"
    
    # Assert - Commission should be removed from unverified list for both profiles
    user1_unverified = user1_profile_contract.getUnverifiedCommissions(0, 10)
    user2_unverified = user2_profile_contract.getUnverifiedCommissions(0, 10)
    assert art_piece.address not in user1_unverified, "Should not be in user1's unverified list"
    assert art_piece.address not in user2_unverified, "Should not be in user2's unverified list" 