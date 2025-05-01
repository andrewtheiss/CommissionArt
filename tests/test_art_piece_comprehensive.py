import pytest
from ape import accounts, project
from eth_utils import to_checksum_address
import base64
import json

# Test data
TEST_TOKEN_URI_DATA = "data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
# Parse base64 data to extract title and description
base64_data = TEST_TOKEN_URI_DATA.replace("data:application/json;base64,", "")
json_data = json.loads(base64.b64decode(base64_data).decode("utf-8"))
TEST_TITLE = json_data["name"]  # "Test Artwork"
TEST_DESCRIPTION = json_data["description"]  # "This is a test description for the artwork"
TEST_AI_GENERATED = False

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    tagged_person = accounts.test_accounts[3]
    commissioner = accounts.test_accounts[4]
    
    # Deploy CommissionHub
    commission_hub = project.CommissionHub.deploy(sender=deployer)
    
    # Deploy ArtPiece contract
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the contract
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        commission_hub.address,
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "tagged_person": tagged_person,
        "commissioner": commissioner,
        "commission_hub": commission_hub,
        "art_piece": art_piece
    }

def test_initialization(setup):
    """Test that the contract is initialized with the correct values"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    artist = setup["artist"]
    
    # Check initialization status
    assert art_piece.initialized() is True
    
    # Check basic data
    assert art_piece.getTokenURIData() == TEST_TOKEN_URI_DATA
    assert art_piece.getImageData() == TEST_TOKEN_URI_DATA  # Test backwards compatibility
    assert art_piece.getTitle() == TEST_TITLE
    assert art_piece.getDescription() == TEST_DESCRIPTION
    assert art_piece.getOwner() == owner.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getAIGenerated() == TEST_AI_GENERATED
    assert art_piece.aiGenerated() == TEST_AI_GENERATED  # Test both methods


def test_initialize_only_once(setup):
    """Test that initialize can only be called once"""
    art_piece = setup["art_piece"]
    deployer = setup["deployer"]
    owner = setup["owner"]
    artist = setup["artist"]
    commission_hub = setup["commission_hub"]
    
    # Try to initialize the contract again
    with pytest.raises(Exception) as excinfo:
        art_piece.initialize(
            TEST_TOKEN_URI_DATA,
            TEST_TITLE,
            TEST_DESCRIPTION,
            owner.address,
            artist.address,
            commission_hub.address,
            TEST_AI_GENERATED,
            sender=deployer
        )
    
    # Verify the error message
    assert "Already initialized" in str(excinfo.value)


def test_transfer_ownership(setup):
    """Test transferring ownership"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    deployer = setup["deployer"]
    
    # Transfer ownership to deployer
    art_piece.transferOwnership(deployer.address, sender=owner)
    
    # Check that the owner was updated
    assert art_piece.getOwner() == deployer.address


def test_transfer_ownership_only_by_owner(setup):
    """Test that only the owner can transfer ownership"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    deployer = setup["deployer"]
    
    # Try to transfer ownership from a non-owner account
    with pytest.raises(Exception) as excinfo:
        art_piece.transferOwnership(deployer.address, sender=artist)
    
    # Verify the error message
    assert "Only the owner can transfer ownership" in str(excinfo.value)


def test_transfer_ownership_not_to_zero_address(setup):
    """Test that ownership cannot be transferred to the zero address"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    zero_address = "0x0000000000000000000000000000000000000000"
    
    # Try to transfer ownership to the zero address
    with pytest.raises(Exception) as excinfo:
        art_piece.transferOwnership(zero_address, sender=owner)
    
    # Verify the error message
    assert "Invalid new owner address" in str(excinfo.value)


def test_tag_person(setup):
    """Test tagging a person by an owner"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    tagged_person = setup["tagged_person"]
    
    # Owner tags a person
    art_piece.tagPerson(tagged_person.address, sender=owner)
    
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
    
    # Artist tags a person
    art_piece.tagPerson(tagged_person.address, sender=artist)
    
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
    
    # Try to tag a person from an unauthorized account
    with pytest.raises(Exception) as excinfo:
        art_piece.tagPerson(tagged_person.address, sender=commissioner)
    
    # Verify the error message
    assert "Only owner or artist can tag people" in str(excinfo.value)


def test_tag_not_zero_address(setup):
    """Test that the zero address cannot be tagged"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    zero_address = "0x0000000000000000000000000000000000000000"
    
    # Try to tag the zero address
    with pytest.raises(Exception) as excinfo:
        art_piece.tagPerson(zero_address, sender=owner)
    
    # Verify the error message
    assert "Cannot tag zero address" in str(excinfo.value)


def test_tag_limits(setup):
    """Test the upper limit of tagged addresses"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    deployer = setup["deployer"]
    artist = setup["artist"]
    tagged_person = setup["tagged_person"]
    commissioner = setup["commissioner"]
    
    # Use the accounts we already have for tagging, to ensure they exist
    accounts_to_tag = [
        deployer,     # accounts.test_accounts[0]
        artist,       # accounts.test_accounts[1]
        owner,        # accounts.test_accounts[2]
        tagged_person, # accounts.test_accounts[3]
        commissioner   # accounts.test_accounts[4]
    ]
    
    # Tag these accounts
    for account in accounts_to_tag:
        # Skip if account is owner (can't tag self)
        if account.address != owner.address:
            art_piece.tagPerson(account.address, sender=owner)
    
    # Verify tagged addresses
    tagged_addresses = art_piece.getAllTaggedAddresses()
    assert len(tagged_addresses) == len(accounts_to_tag) - 1  # -1 because owner can't tag self
    
    # Check a specific account is tagged
    assert art_piece.isPersonTagged(artist.address) is True


def test_validate_tag(setup):
    """Test validating a tag"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    tagged_person = setup["tagged_person"]
    
    # Owner tags a person
    art_piece.tagPerson(tagged_person.address, sender=owner)
    
    # Tagged person validates the tag
    art_piece.validateTag(sender=tagged_person)
    
    # Verify the tag is validated
    assert art_piece.isTaggedValidated(tagged_person.address) is True


def test_invalidate_tag(setup):
    """Test invalidating a tag"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    tagged_person = setup["tagged_person"]
    
    # Owner tags a person
    art_piece.tagPerson(tagged_person.address, sender=owner)
    
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
    
    # Try to validate a tag when not tagged
    with pytest.raises(Exception) as excinfo:
        art_piece.validateTag(sender=tagged_person)
    
    # Verify the error message
    assert "You are not tagged in this artwork" in str(excinfo.value)


def test_invalidate_tag_requires_being_tagged(setup):
    """Test that only tagged persons can invalidate their tag"""
    art_piece = setup["art_piece"]
    tagged_person = setup["tagged_person"]
    
    # Try to invalidate a tag when not tagged
    with pytest.raises(Exception) as excinfo:
        art_piece.invalidateTag(sender=tagged_person)
    
    # Verify the error message
    assert "You are not tagged in this artwork" in str(excinfo.value)


def test_commission_whitelist(setup):
    """Test setting and checking commission whitelist"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    commissioner = setup["commissioner"]
    
    # Check initial whitelist status
    assert art_piece.isOnCommissionWhitelist(commissioner.address) is False
    
    # Whitelist the commissioner
    art_piece.setCommissionWhitelist(commissioner.address, True, sender=owner)
    
    # Check that the commissioner is now whitelisted
    assert art_piece.isOnCommissionWhitelist(commissioner.address) is True
    
    # Remove the commissioner from the whitelist
    art_piece.setCommissionWhitelist(commissioner.address, False, sender=owner)
    
    # Check that the commissioner is no longer whitelisted
    assert art_piece.isOnCommissionWhitelist(commissioner.address) is False


def test_commission_whitelist_by_artist(setup):
    """Test that the artist can also manage the commission whitelist"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    
    # Whitelist the commissioner as the artist
    art_piece.setCommissionWhitelist(commissioner.address, True, sender=artist)
    
    # Check that the commissioner is now whitelisted
    assert art_piece.isOnCommissionWhitelist(commissioner.address) is True


def test_commission_whitelist_unauthorized(setup):
    """Test that only the owner or artist can manage the commission whitelist"""
    art_piece = setup["art_piece"]
    tagged_person = setup["tagged_person"]
    commissioner = setup["commissioner"]
    
    # Try to whitelist the commissioner as an unauthorized account
    with pytest.raises(Exception) as excinfo:
        art_piece.setCommissionWhitelist(commissioner.address, True, sender=tagged_person)
    
    # Verify the error message
    assert "Only owner or artist can set commission whitelist" in str(excinfo.value)


def test_all_getter_methods(setup):
    """Test all getter methods of the contract"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    artist = setup["artist"]
    
    # Test all available getter methods
    assert art_piece.getTokenURIData() == TEST_TOKEN_URI_DATA
    assert art_piece.getImageData() == TEST_TOKEN_URI_DATA  # Test backwards compatibility
    assert art_piece.getTitle() == TEST_TITLE
    assert art_piece.getDescription() == TEST_DESCRIPTION
    assert art_piece.getOwner() == owner.address
    assert art_piece.getArtist() == artist.address
    assert art_piece.getAIGenerated() == TEST_AI_GENERATED
    
    # Test auto-generated getters for public variables
    assert art_piece.aiGenerated() == TEST_AI_GENERATED
    assert art_piece.initialized() is True 