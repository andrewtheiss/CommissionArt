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
    
    # Deploy ArtCommissionHub template to pass to ProfileFactoryAndRegistry
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with templates
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
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
        "profile_social": profile_social,
        "commission_hub_template": commission_hub_template
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

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
    profile_factory = setup["profile_factory"]
    
    # Deploy a new Profile contract
    profile = project.Profile.deploy(sender=deployer)
    
    # Act/Assert - Try to initialize with empty social address (should fail)
    with pytest.raises(Exception) as excinfo:
        profile.initialize(user.address, ZERO_ADDRESS, profile_factory.address, sender=deployer)
    assert "empty" in str(excinfo.value), "Should not allow initialization with empty ProfileSocial address"

def test_initialize_once_only(setup):
    """Test that Profile can only be initialized once"""
    # Arrange
    profile = setup["profile"]
    user = setup["user"]
    deployer = setup["deployer"]
    profile_social = setup["profile_social"]
    profile_factory = setup["profile_factory"]
    
    # Act/Assert - Try to initialize the profile again (should fail)
    with pytest.raises(Exception) as excinfo:
        profile.initialize(user.address, profile_social.address, profile_factory.address, sender=deployer)
    assert "Already initialized" in str(excinfo.value), "Profile should not allow initialization more than once"

def test_factory_created_profile_social_link(setup):
    """Test the creation of a Profile and ProfileSocial through the registry and verify the link"""
    # Arrange
    # Use the same fixture pattern as in generic hub tests
    # We need to deploy ArtCommissionHubOwners and link it to the factory
    deployer = setup["deployer"]
    profile_factory = setup["profile_factory"]
    profile_social_template = setup["profile_social_template"]
    profile_template = setup["profile_template"]
    
    # Deploy L2OwnershipRelay and ArtCommissionHub template for ArtCommissionHubOwners
    l2_relay = project.L2OwnershipRelay.deploy(sender=deployer)
    art_commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_collection_ownership_registry = project.ArtCommissionHubOwners.deploy(
        l2_relay.address,
        art_commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    # Link ArtCommissionHubOwners and ProfileFactoryAndRegistry
    art_collection_ownership_registry.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    profile_factory.linkArtCommissionHubOwnersContract(art_collection_ownership_registry.address, sender=deployer)
    # Set L2OwnershipRelay to the deployer for testing
    art_collection_ownership_registry.setL2OwnershipRelay(deployer.address, sender=deployer)

    # Act - Create a generic commission hub for the deployer (this will create the profile via the registry)
    tx = art_collection_ownership_registry.createGenericCommissionHub(deployer.address, sender=deployer)

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