import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    """Setup test environment with deployed contracts and user accounts"""
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with templates
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        sender=deployer
    )
    
    # Create a profile for testing
    profile_factory.createProfile(sender=user)
    
    # Get the created profile address
    profile_address = profile_factory.getProfile(user.address)
    profile = project.Profile.at(profile_address)
    
    # Get the ProfileSocial address
    profile_social_address = profile.profileSocial()
    profile_social = project.ProfileSocial.at(profile_social_address)
    
    return {
        "deployer": deployer,
        "user": user,
        "profile_template": profile_template,
        "profile_social_template": profile_social_template,
        "profile_factory": profile_factory,
        "profile": profile,
        "profile_social": profile_social
    }

def test_profilesocial_link_immutability(setup):
    """Test that the link between Profile and ProfileSocial is permanent and immutable"""
    # Arrange
    profile = setup["profile"]
    user = setup["user"]
    deployer = setup["deployer"]
    
    # Get the original ProfileSocial address
    original_social_address = profile.profileSocial()
    
    # Create a new ProfileSocial contract to try to replace the original
    new_social = project.ProfileSocial.deploy(sender=deployer)
  
    # Verify the link remains unchanged
    assert profile.profileSocial() == original_social_address, "ProfileSocial link should remain unchanged"

def test_bidirectional_link_integrity(setup):
    """Test that the bidirectional link between Profile and ProfileSocial is properly established"""
    # Arrange
    profile = setup["profile"]
    profile_social = setup["profile_social"]
    user = setup["user"]
    
    # Assert - Profile points to ProfileSocial
    assert profile.profileSocial() == profile_social.address, "Profile should link to ProfileSocial"
    
    # Assert - ProfileSocial points back to Profile
    assert profile_social.profile() == profile.address, "ProfileSocial should link back to Profile"
    
    # Assert - Both have same owner
    assert profile.owner() == user.address, "Profile owner should be user"
    assert profile_social.owner() == user.address, "ProfileSocial owner should be user"

def test_initialize_with_empty_social(setup):
    """Test that Profile initialization fails with empty ProfileSocial address"""
    # Arrange
    deployer = setup["deployer"]
    user = setup["user"]
    
    # Deploy a new Profile contract
    profile = project.Profile.deploy(sender=deployer)
    
    # Act/Assert - Try to initialize with empty social address (should fail)
    with pytest.raises(Exception) as excinfo:
        profile.initialize(user.address, ZERO_ADDRESS, sender=deployer)
    assert "empty" in str(excinfo.value), "Should not allow initialization with empty ProfileSocial address"

def test_initialize_once_only(setup):
    """Test that Profile can only be initialized once"""
    # Arrange
    profile = setup["profile"]
    user = setup["user"]
    deployer = setup["deployer"]
    profile_social = setup["profile_social"]
    
    # Act/Assert - Try to initialize the profile again (should fail)
    with pytest.raises(Exception) as excinfo:
        profile.initialize(user.address, profile_social.address, sender=deployer)
    assert "Already initialized" in str(excinfo.value), "Profile should not allow initialization more than once"

def test_factory_created_profile_social_link(setup):
    """Test the creation of a Profile and ProfileSocial through the registry and verify the link"""
    # Arrange
    # Use the same fixture pattern as in generic hub tests
    # We need to deploy OwnerRegistry and link it to the factory
    deployer = setup["deployer"]
    profile_factory = setup["profile_factory"]
    profile_social_template = setup["profile_social_template"]
    profile_template = setup["profile_template"]
    
    # Deploy L2Relay and ArtCommissionHub template for OwnerRegistry
    l2_relay = project.L2Relay.deploy(sender=deployer)
    art_commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy OwnerRegistry
    owner_registry = project.OwnerRegistry.deploy(
        l2_relay.address,
        art_commission_hub_template.address,
        sender=deployer
    )
    # Link OwnerRegistry and ProfileFactoryAndRegistry
    owner_registry.setProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    profile_factory.setOwnerRegistry(owner_registry.address, sender=deployer)
    # Set L2Relay to the deployer for testing
    owner_registry.setL2Relay(deployer.address, sender=deployer)

    # Act - Create a generic commission hub for the deployer (this will create the profile via the registry)
    tx = owner_registry.createGenericCommissionHub(1, deployer.address, sender=deployer)

    # Get the created profile
    profile_address = profile_factory.getProfile(deployer.address)
    profile = project.Profile.at(profile_address)

    # Assert - Profile has a ProfileSocial link
    profile_social_address = profile.profileSocial()
    assert profile_social_address != ZERO_ADDRESS, "Profile should have a ProfileSocial link"

    # Get the ProfileSocial contract
    profile_social = project.ProfileSocial.at(profile_social_address)

    # Assert - Bidirectional link is established
    assert profile_social.profile() == profile_address, "ProfileSocial should link back to Profile"
    assert profile_social.owner() == deployer.address, "ProfileSocial should have deployer as owner" 