import pytest
from ape import accounts, project
from eth_utils import to_checksum_address

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False

# Define zero address constant for testing
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# ERC721 constants
INTERFACE_ID_ERC721 = 0x80ac58cd
INTERFACE_ID_ERC165 = 0x01ffc9a7
TOKEN_ID = 1

GENERIC_CONTRACT = "0x1000000000000000000000000000000000000001"  # GENERIC_ART_COMMISSION_HUB_CONTRACT

# Individual standalone tests - each test is fully independent

def test_01_deploy_profile_template():
    """Test that Profile template can be deployed"""
    deployer = accounts.test_accounts[0]
    profile_template = project.Profile.deploy(sender=deployer)
    
    assert profile_template.address != ZERO_ADDRESS


def test_02_deploy_profile_social_template():
    """Test that ProfileSocial template can be deployed"""
    deployer = accounts.test_accounts[0]
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    
    assert profile_social_template.address != ZERO_ADDRESS


def test_03_deploy_commission_hub_template():
    """Test that ArtCommissionHub template can be deployed"""
    deployer = accounts.test_accounts[0]
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    
    assert commission_hub_template.address != ZERO_ADDRESS


def test_04_deploy_art_piece_template():
    """Test that ArtPiece template can be deployed"""
    deployer = accounts.test_accounts[0]
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    assert art_piece_template.address != ZERO_ADDRESS


def test_05_deploy_profile_factory_registry():
    """Test that ProfileFactoryAndRegistry can be deployed with the templates"""
    deployer = accounts.test_accounts[0]
    
    # First deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    assert profile_factory.address != ZERO_ADDRESS
    assert profile_factory.profileTemplate() == profile_template.address
    assert profile_factory.profileSocialTemplate() == profile_social_template.address
    assert profile_factory.commissionHubTemplate() == commission_hub_template.address


def test_06_deploy_art_commission_hub_owners():
    """Test that ArtCommissionHubOwners can be deployed"""
    deployer = accounts.test_accounts[0]
    
    # Deploy templates first
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    assert art_commission_hub_owners.address != ZERO_ADDRESS
    assert art_commission_hub_owners.l2OwnershipRelay() == deployer.address


def test_07_link_factory_and_hub_owners():
    """Test linking ProfileFactoryAndRegistry and ArtCommissionHubOwners"""
    deployer = accounts.test_accounts[0]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy both contracts
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Link them together
    profile_factory.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    
    # Verify the links
    assert profile_factory.artCommissionHubOwners() == art_commission_hub_owners.address
    assert art_commission_hub_owners.profileFactoryAndRegistry() == profile_factory.address


def test_08_initialize_commission_hub():
    """Test initializing ArtCommissionHub with ArtCommissionHubOwners"""
    deployer = accounts.test_accounts[0]
    
    # Deploy templates
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHubOwners
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Deploy a commission hub instance
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Initialize the hub
    commission_hub.initializeParentCommissionHubOwnerContract(art_commission_hub_owners.address, sender=deployer)
    
    # Verify initialization
    assert commission_hub.artCommissionHubOwners() == art_commission_hub_owners.address


def test_09_create_profile():
    """Test creating a profile through ProfileFactoryAndRegistry"""
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    
    # Deploy all necessary templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    
    # Deploy factory registry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    # Verify no profile exists for user
    assert profile_factory.hasProfile(user.address) == False
    
    # Create profile for user
    tx = profile_factory.createProfile(user.address, sender=deployer)
    
    # Verify profile now exists
    assert profile_factory.hasProfile(user.address) == True
    
    # Get profile address
    profile_address = profile_factory.getProfile(user.address)
    assert profile_address != ZERO_ADDRESS
    
    # Verify profile owner
    profile = project.Profile.at(profile_address)
    assert profile.owner() == user.address


def test_10_initialize_art_piece():
    """Test initializing an ArtPiece contract"""
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    
    # Deploy necessary templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    
    # Deploy factory registry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    # Create profile for deployer
    profile_factory.createProfile(deployer.address, sender=deployer)
    profile_factory.createProfile(owner.address, sender=deployer)
    
    # Deploy ArtPiece
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the art piece
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # No commission hub needed for this test
        TEST_AI_GENERATED,
        owner.address,  # original uploader
        profile_factory.address,  # Now we provide the profile factory address
        sender=deployer
    )
    
    # Verify initialization
    assert art_piece.getOwner() == owner.address
    assert art_piece.artist() == artist.address
    assert art_piece.title() == TEST_TITLE
    assert art_piece.description() == TEST_DESCRIPTION
    assert art_piece.aiGenerated() == TEST_AI_GENERATED
    
    # Test basic ERC721 functionality
    assert art_piece.balanceOf(owner.address) == 1
    assert art_piece.balanceOf(artist.address) == 0
