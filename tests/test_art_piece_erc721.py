import pytest
from ape import accounts, project
from eth_utils import to_checksum_address

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJCTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
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

@pytest.fixture
def setup():
    """Setup function that deploys and initializes all contracts needed for ERC721 testing"""
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    approved_spender = accounts.test_accounts[3]
    approved_operator = accounts.test_accounts[4]
    receiver = accounts.test_accounts[5]
    
    # Deploy all necessary templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy profile factory with required parameters
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    # Deploy ArtCommissionHubOwners with L2OwnershipRelay as the deployer (for testing)
    art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
        deployer.address,  # L2OwnershipRelay (using deployer for testing)
        commission_hub_template.address,
        art_piece_template.address,
        sender=deployer
    )
    
    # Link the ArtCommissionHubOwners to the ProfileFactoryAndRegistry
    profile_factory.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
    art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
    
    # Create profiles for test accounts
    profile_factory.createProfile(deployer.address, sender=deployer)
    profile_factory.createProfile(artist.address, sender=deployer)
    profile_factory.createProfile(owner.address, sender=deployer)
    
    # Deploy ArtPiece contract
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the art piece (no commission hub for basic ERC721 testing)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # No commission hub for basic ERC721 testing
        TEST_AI_GENERATED,
        artist.address,  # original uploader (artist)
        profile_factory.address,  # profile factory address
        sender=deployer
    )
    
    # Approve the ArtPiece instance in ArtCommissionHubOwners (required step)
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "approved_spender": approved_spender,
        "approved_operator": approved_operator,
        "receiver": receiver,
        "art_piece": art_piece,
        "profile_factory": profile_factory,
        "art_commission_hub_owners": art_commission_hub_owners
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

def test_balanceOf(setup):
    """Test balanceOf method"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner (original uploader)
    owner = setup["owner"]
    
    # Check balance of effective owner (artist)
    assert art_piece.balanceOf(artist.address) == 1
    
    # Check balance of non-owner
    assert art_piece.balanceOf(owner.address) == 0

def test_ownerOf(setup):
    """Test ownerOf method"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner (original uploader)
    
    # Check owner of token
    assert art_piece.ownerOf(TOKEN_ID) == artist.address
    
    # Test with invalid token ID
    with pytest.raises(Exception) as excinfo:
        art_piece.ownerOf(2)  # Invalid token ID
    
    error_message = str(excinfo.value).lower()
    assert "single id" in error_message or "only" in error_message

def test_approve(setup):
    """Test approve method - should always fail with current design"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    approved_spender = setup["approved_spender"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.approve(approved_spender.address, TOKEN_ID, sender=artist)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "approvals" in error_message

def test_approve_unauthorized(setup):
    """Test approve by unauthorized caller - should always fail with current design"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]  # Not the effective owner
    approved_spender = setup["approved_spender"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.approve(approved_spender.address, TOKEN_ID, sender=owner)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "approvals" in error_message

def test_setApprovalForAll(setup):
    """Test setApprovalForAll method - should always fail with current design"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    approved_operator = setup["approved_operator"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.setApprovalForAll(approved_operator.address, True, sender=artist)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "approvals" in error_message

def test_setApprovalForAll_self(setup):
    """Test that setApprovalForAll cannot approve caller - should always fail with current design"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.setApprovalForAll(artist.address, True, sender=artist)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "approvals" in error_message

def test_transferFrom(setup):
    """Test transferFrom method - should fail because transfers are disabled"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    receiver = setup["receiver"]
    
    # Transfers should be disabled for all art pieces
    with pytest.raises(Exception) as excinfo:
        art_piece.transferFrom(artist.address, receiver.address, TOKEN_ID, sender=artist)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_transferFrom_by_approved(setup):
    """Test transferFrom by approved spender - should fail because approvals are disabled"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    approved_spender = setup["approved_spender"]
    receiver = setup["receiver"]
    
    # Transfers should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.transferFrom(artist.address, receiver.address, TOKEN_ID, sender=approved_spender)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_transferFrom_by_operator(setup):
    """Test transferFrom by approved operator - should fail because approvals are disabled"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    approved_operator = setup["approved_operator"]
    receiver = setup["receiver"]
    
    # Transfers should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.transferFrom(artist.address, receiver.address, TOKEN_ID, sender=approved_operator)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_safeTransferFrom(setup):
    """Test safeTransferFrom method - should fail because transfers are disabled"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    receiver = setup["receiver"]
    
    # Transfers should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.safeTransferFrom(artist.address, receiver.address, TOKEN_ID, sender=artist)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_safeTransferFrom_with_data(setup):
    """Test safeTransferFrom with data - should fail because transfers are disabled"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    receiver = setup["receiver"]
    
    # Transfers should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.safeTransferFrom(artist.address, receiver.address, TOKEN_ID, b"test data", sender=artist)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_supportsInterface(setup):
    """Test supportsInterface method"""
    art_piece = setup["art_piece"]
    
    # Test ERC721 interface
    assert art_piece.supportsInterface(INTERFACE_ID_ERC721) is True
    
    # Test ERC165 interface
    assert art_piece.supportsInterface(INTERFACE_ID_ERC165) is True
    
    # Test unsupported interface
    assert art_piece.supportsInterface(0x12345678) is False

def test_tokenURI(setup):
    """Test tokenURI method"""
    art_piece = setup["art_piece"]
    
    # Test valid token ID
    token_uri = art_piece.tokenURI(TOKEN_ID)
    assert isinstance(token_uri, str)
    
    # Test invalid token ID
    with pytest.raises(Exception) as excinfo:
        art_piece.tokenURI(2)  # Invalid token ID
    
    error_message = str(excinfo.value).lower()
    assert "single id" in error_message or "only" in error_message

def test_name_and_symbol(setup):
    """Test name and symbol methods"""
    art_piece = setup["art_piece"]
    
    # Test name
    assert art_piece.name() == "ArtPiece"
    
    # Test symbol
    assert art_piece.symbol() == "ART"

def test_checkOwner(setup):
    """Test checkOwner method"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner (original uploader)
    
    # Check that checkOwner returns the effective owner
    assert art_piece.checkOwner() == artist.address
    assert art_piece.getOwner() == artist.address

def test_transferFrom_unauthorized(setup):
    """Test transferFrom by unauthorized caller - should fail because transfers are disabled"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]  # Artist is the effective owner
    owner = setup["owner"]  # Not the effective owner
    receiver = setup["receiver"]
    
    # Transfers should be disabled regardless of authorization
    with pytest.raises(Exception) as excinfo:
        art_piece.transferFrom(artist.address, receiver.address, TOKEN_ID, sender=owner)
    
    error_message = str(excinfo.value).lower()
    assert "disabled" in error_message or "transfers" in error_message

def test_getApproved(setup):
    """Test getApproved method - should return zero address since approvals are disabled"""
    art_piece = setup["art_piece"]
    
    # Since approvals are disabled, getApproved should return zero address
    approved = art_piece.getApproved(TOKEN_ID)
    assert approved == ZERO_ADDRESS

def test_isApprovedForAll(setup):
    """Test isApprovedForAll method - should return False since approvals are disabled"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    approved_operator = setup["approved_operator"]
    
    # Since approvals are disabled, isApprovedForAll should return False
    is_approved = art_piece.isApprovedForAll(artist.address, approved_operator.address)
    assert is_approved is False

def test_art_piece_specific_methods(setup):
    """Test ArtPiece-specific methods that extend ERC721"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    owner = setup["owner"]
    
    # Test commission-related methods
    assert art_piece.getArtist() == artist.address
    assert art_piece.getCommissioner() == owner.address
    
    # Test hub attachment
    assert art_piece.getArtCommissionHubAddress() == ZERO_ADDRESS
    
    # Test verification status
    assert art_piece.isUnverifiedCommission() is True  # commissioner != artist, not verified
    assert art_piece.isFullyVerifiedCommission() is False
    
    # Test data access
    assert art_piece.getTokenURIData() == TEST_TOKEN_URI_DATA
    assert art_piece.title() == TEST_TITLE
    assert art_piece.description() == TEST_DESCRIPTION
    assert art_piece.aiGenerated() == TEST_AI_GENERATED 