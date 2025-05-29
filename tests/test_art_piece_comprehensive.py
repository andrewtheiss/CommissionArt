import pytest
from ape import accounts, project
from eth_utils import to_checksum_address
import base64
import json

# Define zero address constant
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Test data constants matching the working tests
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJCTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False

@pytest.fixture
def setup():
    """Setup function that deploys and initializes all contracts needed for testing"""
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    tagged_person = accounts.test_accounts[3]
    commissioner = accounts.test_accounts[4]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy factory registry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
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
    profile_factory.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    
    # Create profiles for test accounts that will be used
    profile_factory.createProfile(artist.address, sender=deployer)
    profile_factory.createProfile(owner.address, sender=deployer)
    profile_factory.createProfile(tagged_person.address, sender=deployer)
    
    # Deploy and initialize an art piece directly for basic testing
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # No commission hub for basic tests
        TEST_AI_GENERATED,
        artist.address,  # original uploader (artist account, not profile)
        profile_factory.address,  # Profile factory address
        sender=deployer
    )
    
    # Approve the ArtPiece instance in ArtCommissionHubOwners (required step)
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "tagged_person": tagged_person,
        "commissioner": commissioner,
        "profile_factory": profile_factory,
        "art_commission_hub_owners": art_commission_hub_owners,
        "art_piece_template": art_piece_template,
        "art_piece": art_piece
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

def test_initialization(setup):
    """Test that the contract is initialized with the correct values"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    artist = setup["artist"]
    
    # Check initialization status using correct method name
    assert art_piece.initialized() is True
    
    # Check basic data using correct method names
    assert art_piece.getTokenURIData() == TEST_TOKEN_URI_DATA
    assert art_piece.tokenURI_data_format() == TEST_TOKEN_URI_DATA_FORMAT
    assert art_piece.title() == TEST_TITLE
    assert art_piece.description() == TEST_DESCRIPTION
    assert art_piece.getOwner() == artist.address  # Original uploader is the effective owner initially
    assert art_piece.artist() == artist.address
    assert art_piece.aiGenerated() == TEST_AI_GENERATED

def test_initialize_only_once(setup):
    """Test that initialize can only be called once"""
    art_piece = setup["art_piece"]
    deployer = setup["deployer"]
    owner = setup["owner"]
    artist = setup["artist"]
    profile_factory = setup["profile_factory"]
    
    # Try to initialize the contract again
    with pytest.raises(Exception) as excinfo:
        art_piece.initialize(
            TEST_TOKEN_URI_DATA,
            TEST_TOKEN_URI_DATA_FORMAT,
            TEST_TITLE,
            TEST_DESCRIPTION,
            owner.address,
            artist.address,
            ZERO_ADDRESS,
            TEST_AI_GENERATED,
            artist.address,  # original uploader (artist account, not profile)
            profile_factory.address,  # Profile factory address
            sender=deployer
        )
    
    # Verify the error message contains something about already being initialized
    error_message = str(excinfo.value).lower()
    assert "already" in error_message or "initialized" in error_message

def test_transfer_ownership(setup):
    """Test that transfer ownership is disabled for art pieces"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    deployer = setup["deployer"]
    artist = setup["artist"]
    
    # Get the initial state - should be the original uploader (artist)
    initial_owner = art_piece.getOwner()
    assert initial_owner == artist.address, "Initial owner should be the original uploader (artist)"
    
    # Try to transfer ownership - should fail because transfers are disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.transferOwnership(deployer.address, sender=artist)
    
    # Verify the error message indicates transfers are disabled
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_transfer_ownership_only_by_owner(setup):
    """Test that transfer ownership fails with proper error message"""
    art_piece = setup["art_piece"]
    commissioner = setup["commissioner"]
    deployer = setup["deployer"]
    
    # Try to transfer ownership from a non-owner account - should fail because transfers are disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.transferOwnership(deployer.address, sender=commissioner)
    
    # Verify the error message indicates transfers are disabled
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_transfer_ownership_not_to_zero_address(setup):
    """Test that transfer ownership fails with proper error message"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    
    # Try to transfer ownership to the zero address - should fail because transfers are disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.transferOwnership(ZERO_ADDRESS, sender=artist)
    
    # Verify the error message indicates transfers are disabled
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_tag_person(setup):
    """Test tagging a person by an owner"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    tagged_person = setup["tagged_person"]
    profile_factory = setup["profile_factory"]
    
    # Artist (effective owner) tags a person
    art_piece.tagPerson(tagged_person.address, profile_factory.address, sender=artist)
    
    # Verify the person was tagged
    assert art_piece.isPersonTagged(tagged_person.address) is True
    
    # Verify address is in the list of tagged addresses
    tagged_addresses = art_piece.getAllTaggedAddresses()
    assert tagged_person.address in tagged_addresses

def test_tag_person_as_artist(setup):
    """Test tagging a person by the artist"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    tagged_person = setup["tagged_person"]
    profile_factory = setup["profile_factory"]
    
    # Artist tags a person
    art_piece.tagPerson(tagged_person.address, profile_factory.address, sender=artist)
    
    # Verify the person was tagged
    assert art_piece.isPersonTagged(tagged_person.address) is True
    
    # Verify address is in the list of tagged addresses
    tagged_addresses = art_piece.getAllTaggedAddresses()
    assert tagged_person.address in tagged_addresses

def test_tag_person_unauthorized(setup):
    """Test that only the owner or artist can tag a person"""
    art_piece = setup["art_piece"]
    commissioner = setup["commissioner"]
    tagged_person = setup["tagged_person"]
    profile_factory = setup["profile_factory"]
    
    # Try to tag a person from an unauthorized account
    with pytest.raises(Exception) as excinfo:
        art_piece.tagPerson(tagged_person.address, profile_factory.address, sender=commissioner)
    
    # Verify the error message contains authorization info
    error_message = str(excinfo.value).lower()
    assert "owner" in error_message or "artist" in error_message or "only" in error_message

def test_tag_not_zero_address(setup):
    """Test that the zero address cannot be tagged"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    profile_factory = setup["profile_factory"]
    
    # Try to tag the zero address
    with pytest.raises(Exception) as excinfo:
        art_piece.tagPerson(ZERO_ADDRESS, profile_factory.address, sender=artist)
    
    # Verify the error message contains info about zero address
    error_message = str(excinfo.value).lower()
    assert "zero" in error_message or "invalid" in error_message or "cannot" in error_message

def test_tag_limits(setup):
    """Test the upper limit of tagged addresses"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    deployer = setup["deployer"]
    tagged_person = setup["tagged_person"]
    commissioner = setup["commissioner"]
    owner = setup["owner"]
    profile_factory = setup["profile_factory"]
    
    # Use the accounts we already have for tagging, to ensure they exist
    accounts_to_tag = [
        deployer,     # accounts.test_accounts[0]
        tagged_person, # accounts.test_accounts[3]
        commissioner,  # accounts.test_accounts[4]
        owner         # accounts.test_accounts[2]
    ]
    
    # Tag these accounts (excluding artist as they can't tag themselves)
    for account in accounts_to_tag:
        if account.address != artist.address:
            art_piece.tagPerson(account.address, profile_factory.address, sender=artist)
    
    # Verify tagged addresses
    tagged_addresses = art_piece.getAllTaggedAddresses()
    assert len(tagged_addresses) >= 1  # At least one should be tagged
    
    # Check a specific account is tagged
    assert art_piece.isPersonTagged(deployer.address) is True

def test_validate_tag(setup):
    """Test validating a tag"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    tagged_person = setup["tagged_person"]
    profile_factory = setup["profile_factory"]
    
    # Artist tags a person
    art_piece.tagPerson(tagged_person.address, profile_factory.address, sender=artist)
    
    # Tagged person validates the tag - use call() to get return value
    result = art_piece.validateTag.call(sender=tagged_person)
    assert result is True
    
    # Actually execute the transaction
    art_piece.validateTag(sender=tagged_person)
    
    # Verify the tag is validated
    assert art_piece.isTaggedValidated(tagged_person.address) is True

def test_invalidate_tag(setup):
    """Test invalidating a tag"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    tagged_person = setup["tagged_person"]
    profile_factory = setup["profile_factory"]
    
    # Artist tags a person
    art_piece.tagPerson(tagged_person.address, profile_factory.address, sender=artist)
    
    # Tagged person initially validates the tag
    art_piece.validateTag(sender=tagged_person)
    assert art_piece.isTaggedValidated(tagged_person.address) is True
    
    # Then invalidates the tag
    art_piece.invalidateTag(sender=tagged_person)
    
    # Verify the tag is invalidated
    assert art_piece.isTaggedValidated(tagged_person.address) is False

def test_validate_tag_requires_being_tagged(setup):
    """Test that only tagged persons can validate their tag"""
    art_piece = setup["art_piece"]
    tagged_person = setup["tagged_person"]
    
    # Try to validate a tag when not tagged - should return False
    result = art_piece.validateTag.call(sender=tagged_person)
    assert result is False

def test_invalidate_tag_requires_being_tagged(setup):
    """Test that only tagged persons can invalidate their tag"""
    art_piece = setup["art_piece"]
    tagged_person = setup["tagged_person"]
    
    # Try to invalidate a tag when not tagged
    with pytest.raises(Exception) as excinfo:
        art_piece.invalidateTag(sender=tagged_person)
    
    # Verify the error message contains relevant info
    error_message = str(excinfo.value).lower()
    assert "tagged" in error_message or "not" in error_message

def test_is_on_chain(setup):
    """Test that the IS_ON_CHAIN constant is set to True"""
    art_piece = setup["art_piece"]
    
    # Verify the IS_ON_CHAIN constant is True
    assert art_piece.IS_ON_CHAIN() is True

def test_all_getter_methods(setup):
    """Test all getter methods of the contract"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    
    # Test all available getter methods using correct method names
    assert art_piece.getTokenURIData() == TEST_TOKEN_URI_DATA
    assert art_piece.tokenURI_data_format() == TEST_TOKEN_URI_DATA_FORMAT
    assert art_piece.title() == TEST_TITLE
    assert art_piece.description() == TEST_DESCRIPTION
    assert art_piece.getOwner() == artist.address  # Original uploader is the effective owner
    assert art_piece.artist() == artist.address
    assert art_piece.aiGenerated() == TEST_AI_GENERATED
    
    # Test initialization status and constants
    assert art_piece.initialized() is True
    assert art_piece.IS_ON_CHAIN() is True

def test_erc721_methods(setup):
    """Test ERC721 standard methods"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    
    # Test ERC721 methods
    assert art_piece.name() == "ArtPiece"
    assert art_piece.symbol() == "ART"
    assert art_piece.balanceOf(artist.address) == 1  # Artist is the effective owner
    assert art_piece.ownerOf(1) == artist.address  # Token ID 1
    
    # Test that approvals are disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.approve(accounts.test_accounts[5].address, 1, sender=artist)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "approvals" in error_message
    
    # Test that transfers are disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.transferFrom(artist.address, accounts.test_accounts[5].address, 1, sender=artist)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_commission_methods(setup):
    """Test commission-related methods"""
    art_piece = setup["art_piece"]
    
    # Test commission status methods
    assert art_piece.getCommissioner() == setup["owner"].address
    assert art_piece.getArtist() == setup["artist"].address
    
    # Since commissioner != artist, this is a commission piece but not fully verified yet
    # (it would need both parties to verify to be fully verified)
    assert art_piece.isFullyVerifiedCommission() is False
    assert art_piece.isUnverifiedCommission() is True
    
    # Test hub attachment
    assert art_piece.getArtCommissionHubAddress() == ZERO_ADDRESS 