import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    """Setup test environment with deployed contracts and user accounts"""
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user1 = accounts.test_accounts[1]
    user2 = accounts.test_accounts[2]
    user3 = accounts.test_accounts[3]
    
    # Deploy Profile and ProfileSocial templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with both templates
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, 
        profile_social_template.address, 
        sender=deployer
    )
    
    # Deploy ArtPiece template for art piece creation if needed
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    return {
        "deployer": deployer,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "profile_template": profile_template,
        "profile_social_template": profile_social_template,
        "profile_factory_and_registry": profile_factory_and_registry,
        "art_piece_template": art_piece_template
    }

def test_profile_social_creation(setup):
    """Test that ProfileSocial is created alongside Profile"""
    # Arrange
    profile_factory = setup["profile_factory_and_registry"]
    user1 = setup["user1"]
    
    # Act - Create a profile
    profile_factory.createProfile(sender=user1)
    
    # Assert - Profile was created
    profile_address = profile_factory.getProfile(user1.address)
    assert profile_address != ZERO_ADDRESS, "Profile should be created"
    
    # Get the profile contract
    profile = project.Profile.at(profile_address)
    
    # Assert - ProfileSocial was created and linked to Profile
    profile_social_address = profile.profileSocial()
    assert profile_social_address != ZERO_ADDRESS, "ProfileSocial should be created and linked"
    
    # Get the ProfileSocial contract
    profile_social = project.ProfileSocial.at(profile_social_address)
    
    # Assert - Bidirectional link is established
    assert profile_social.owner() == user1.address, "ProfileSocial should have the same owner as Profile"
    assert profile_social.profile() == profile_address, "ProfileSocial should link back to Profile"

def test_profile_social_immutable_link(setup):
    """Test that the link between Profile and ProfileSocial is permanent"""
    # Arrange
    profile_factory = setup["profile_factory_and_registry"]
    user1 = setup["user1"]
    
    # Create a profile
    profile_factory.createProfile(sender=user1)
    profile_address = profile_factory.getProfile(user1.address)
    profile = project.Profile.at(profile_address)
    
    # Get the original ProfileSocial
    original_profile_social = profile.profileSocial()
    assert original_profile_social != ZERO_ADDRESS
    
    # Deploy a new ProfileSocial to attempt to replace the original
    new_profile_social = project.ProfileSocial.deploy(sender=setup["deployer"])
    
    assert "already set" in str(excinfo.value) or "Only hub" in str(excinfo.value), "Should not allow changing ProfileSocial once set"
    
    # Verify the link remained unchanged
    assert profile.profileSocial() == original_profile_social, "ProfileSocial link should remain unchanged"

def test_profile_creation_for_other(setup):
    """Test creating a profile for another user (via createProfileFor)"""
    # Arrange
    profile_factory = setup["profile_factory_and_registry"]
    deployer = setup["deployer"]
    user2 = setup["user2"]
    
    # First establish deployer as owner registry to allow using createProfileFor
    profile_factory.setArtCommissionHubOwners(deployer.address, sender=deployer)
    
    # Act - Create profile for user2
    profile_factory.createProfileFor(user2.address, sender=deployer)
    
    # Assert - Profile was created
    profile_address = profile_factory.getProfile(user2.address)
    assert profile_address != ZERO_ADDRESS, "Profile should be created for user2"
    
    # Get the profile contract
    profile = project.Profile.at(profile_address)
    
    # Assert - ProfileSocial was created and correctly linked
    profile_social_address = profile.profileSocial()
    assert profile_social_address != ZERO_ADDRESS, "ProfileSocial should be created and linked"
    
    # Get the ProfileSocial contract
    profile_social = project.ProfileSocial.at(profile_social_address)
    
    # Assert - Correct ownership and bidirectional links
    assert profile.owner() == user2.address, "Profile owner should be user2"
    assert profile_social.owner() == user2.address, "ProfileSocial owner should be user2"
    assert profile_social.profile() == profile_address, "ProfileSocial should link back to Profile"

def test_create_art_piece_and_register_profile(setup):
    """Test creating an art piece and registering a profile in one transaction"""
    # Arrange
    profile_factory = setup["profile_factory_and_registry"]
    user3 = setup["user3"]
    art_piece_template = setup["art_piece_template"]
    
    # Ensure user3 doesn't have a profile yet
    assert profile_factory.hasProfile(user3.address) is False, "User3 should not have a profile yet"
    
    # Act - Create art piece and register profile
    result = profile_factory.createNewArtPieceAndRegisterProfile(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Art Piece",
        "Test Description",
        True,  # is_artist
        ZERO_ADDRESS,  # other_party
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=user3
    )
    
    # Parse result tuple
    profile_address = result[0]
    art_piece_address = result[1]
    
    # Assert - Profile was created
    assert profile_factory.hasProfile(user3.address) is True, "User3 should now have a profile"
    assert profile_address != ZERO_ADDRESS, "Profile address should not be zero"
    
    # Get the profile contract
    profile = project.Profile.at(profile_address)
    
    # Assert - ProfileSocial was created and correctly linked
    profile_social_address = profile.profileSocial()
    assert profile_social_address != ZERO_ADDRESS, "ProfileSocial should be created and linked"
    
    # Get the ProfileSocial contract
    profile_social = project.ProfileSocial.at(profile_social_address)
    
    # Assert - Correct ownership and bidirectional links
    assert profile.owner() == user3.address, "Profile owner should be user3"
    assert profile_social.owner() == user3.address, "ProfileSocial owner should be user3"
    assert profile_social.profile() == profile_address, "ProfileSocial should link back to Profile"
    
    # Assert - Art piece was created and linked to profile
    assert profile.myArtCount() > 0, "Profile should have art pieces"
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getArtist() == user3.address, "Art piece should have user3 as artist"

def test_create_art_piece_for_party(setup):
    """Test creating an art piece for another party with automatic profile creation"""
    # Arrange
    profile_factory = setup["profile_factory_and_registry"]
    user1 = setup["user1"]
    user2 = setup["user2"]
    art_piece_template = setup["art_piece_template"]
    
    # Make sure user1 and user2 don't have profiles yet
    if profile_factory.hasProfile(user1.address):
        # If test_profile_social_creation ran first, user1 might already have a profile
        # We'll use user3 instead
        user1 = setup["user3"]
    
    if profile_factory.hasProfile(user2.address):
        # If test_profile_creation_for_other ran first, user2 might already have a profile
        # We'll skip this test if both user1 and user2 already have profiles
        if profile_factory.hasProfile(user1.address):
            pytest.skip("Both users already have profiles, skipping test")
    
    # Ensure at least one of the users doesn't have a profile
    assert not (profile_factory.hasProfile(user1.address) and profile_factory.hasProfile(user2.address)), "At least one user should not have a profile"
    
    # Act - Create art piece for party
    result = profile_factory.createArtPieceForParty(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # user1 is artist
        user2.address,  # other_party (user2 is commissioner)
        ZERO_ADDRESS,  # commission_hub
        False,  # ai_generated
        sender=user1
    )
    
    # Parse result tuple
    user1_profile_address = result[0]
    user2_profile_address = result[1]
    art_piece_address = result[2]
    
    # Assert - Profiles were created for both users
    assert profile_factory.hasProfile(user1.address) is True, "Artist (user1) should now have a profile"
    assert profile_factory.hasProfile(user2.address) is True, "Commissioner (user2) should now have a profile"
    
    # Get profile contracts
    user1_profile = project.Profile.at(user1_profile_address)
    user2_profile = project.Profile.at(user2_profile_address)
    
    # Assert - ProfileSocial contracts were created and correctly linked for both users
    user1_social_address = user1_profile.profileSocial()
    user2_social_address = user2_profile.profileSocial()
    
    assert user1_social_address != ZERO_ADDRESS, "Artist's ProfileSocial should be created and linked"
    assert user2_social_address != ZERO_ADDRESS, "Commissioner's ProfileSocial should be created and linked"
    
    # Get ProfileSocial contracts
    user1_social = project.ProfileSocial.at(user1_social_address)
    user2_social = project.ProfileSocial.at(user2_social_address)
    
    # Assert - Correct ownership and bidirectional links for both users
    assert user1_profile.owner() == user1.address, "Profile owner should be user1"
    assert user1_social.owner() == user1.address, "ProfileSocial owner should be user1"
    assert user1_social.profile() == user1_profile_address, "ProfileSocial should link back to Profile"
    
    assert user2_profile.owner() == user2.address, "Profile owner should be user2"
    assert user2_social.owner() == user2.address, "ProfileSocial owner should be user2"
    assert user2_social.profile() == user2_profile_address, "ProfileSocial should link back to Profile"
    
    # Assert - Art piece was created and linked correctly
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getArtist() == user1.address, "Art piece should have user1 as artist"
    assert art_piece.getCommissioner() == user2.address, "Art piece should have user2 as commissioner"

def test_update_profile_social_template(setup):
    """Test updating the ProfileSocial template in the factory"""
    # Arrange
    profile_factory = setup["profile_factory_and_registry"]
    deployer = setup["deployer"]
    
    # Get original template
    original_template = profile_factory.profileSocialTemplate()
    
    # Deploy a new ProfileSocial template
    new_template = project.ProfileSocial.deploy(sender=deployer)
    
    # Act - Update the template
    profile_factory.updateProfileSocialTemplateContract(new_template.address, sender=deployer)
    
    # Assert - Template was updated
    assert profile_factory.profileSocialTemplate() == new_template.address, "ProfileSocial template should be updated"
    assert profile_factory.profileSocialTemplate() != original_template, "ProfileSocial template should be different from original" 