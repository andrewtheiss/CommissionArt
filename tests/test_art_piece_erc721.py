import pytest
from ape import accounts, project
from eth_utils import to_checksum_address

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Test Artwork"
TEST_DESCRIPTION = "This is a test description for the artwork"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False

# ERC721 constants
INTERFACE_ID_ERC721 = 0x80ac58cd
INTERFACE_ID_ERC165 = 0x01ffc9a7
TOKEN_ID = 1

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    approved_spender = accounts.test_accounts[3]
    approved_operator = accounts.test_accounts[4]
    receiver = accounts.test_accounts[5]
    
    # Deploy ArtCommissionHub
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy ArtPiece contract
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the contract
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        commission_hub.address,
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    # Create ERC721Receiver contract for safe transfers
    try:
        erc721_receiver = project.TestERC721Receiver.deploy(sender=deployer)
    except Exception:
        # If TestERC721Receiver doesn't exist, set to None
        erc721_receiver = None
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "approved_spender": approved_spender,
        "approved_operator": approved_operator,
        "receiver": receiver,
        "commission_hub": commission_hub,
        "art_piece": art_piece,
        "erc721_receiver": erc721_receiver
    }

def test_balanceOf(setup):
    """Test balanceOf method"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    artist = setup["artist"]
    
    # Check balance of owner
    assert art_piece.balanceOf(owner.address) == 1
    
    # Check balance of non-owner
    assert art_piece.balanceOf(artist.address) == 0

def test_ownerOf(setup):
    """Test ownerOf method"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    
    # Check owner of token
    assert art_piece.ownerOf(TOKEN_ID) == owner.address
    
    # Test with invalid token ID
    with pytest.raises(Exception) as excinfo:
        art_piece.ownerOf(2)  # Invalid token ID
    assert "Invalid token ID" in str(excinfo.value)

def test_approve(setup):
    """Test approve method - should always fail with current design"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    approved_spender = setup["approved_spender"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.approve(approved_spender.address, TOKEN_ID, sender=owner)
    assert "Approvals are disabled" in str(excinfo.value)

def test_approve_unauthorized(setup):
    """Test approve by unauthorized caller - should always fail with current design"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    approved_spender = setup["approved_spender"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.approve(approved_spender.address, TOKEN_ID, sender=artist)
    assert "Approvals are disabled" in str(excinfo.value)

def test_setApprovalForAll(setup):
    """Test setApprovalForAll method - should always fail with current design"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    approved_operator = setup["approved_operator"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.setApprovalForAll(approved_operator.address, True, sender=owner)
    assert "Approvals are disabled" in str(excinfo.value)

def test_setApprovalForAll_self(setup):
    """Test that setApprovalForAll cannot approve caller - should always fail with current design"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.setApprovalForAll(owner.address, True, sender=owner)
    assert "Approvals are disabled" in str(excinfo.value)

def test_transferFrom(setup):
    """Test transferFrom method - should fail for hub-attached art pieces"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    receiver = setup["receiver"]
    deployer = setup["deployer"]
    
    # First verify if the piece is attached to a commission hub
    is_attached = art_piece.attachedToArtCommissionHub()
    
    if is_attached:
        # If attached, transfers should be blocked
        with pytest.raises(Exception) as excinfo:
            art_piece.transferFrom(owner.address, receiver.address, TOKEN_ID, sender=owner)
        assert "Transfers disabled for hub-attached art pieces" in str(excinfo.value)
    else:
        # If not attached, direct owner should be able to transfer
        art_piece.transferFrom(owner.address, receiver.address, TOKEN_ID, sender=owner)
        
        # Check new owner
        assert art_piece.ownerOf(TOKEN_ID) == receiver.address
        assert art_piece.getOwner() == receiver.address
        
        # Check balance updates
        assert art_piece.balanceOf(owner.address) == 0
        assert art_piece.balanceOf(receiver.address) == 1

def test_transferFrom_by_approved(setup):
    """Test transferFrom method by approved spender - should always fail"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    approved_spender = setup["approved_spender"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.approve(approved_spender.address, TOKEN_ID, sender=owner)
    assert "Approvals are disabled" in str(excinfo.value)

def test_transferFrom_by_operator(setup):
    """Test transferFrom method by approved operator - should always fail"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    approved_operator = setup["approved_operator"]
    
    # Approvals should be disabled
    with pytest.raises(Exception) as excinfo:
        art_piece.setApprovalForAll(approved_operator.address, True, sender=owner)
    assert "Approvals are disabled" in str(excinfo.value)

def test_safeTransferFrom(setup):
    """Test safeTransferFrom method to EOA - should fail for hub-attached art pieces"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    receiver = setup["receiver"]
    deployer = setup["deployer"]
    
    # First verify if the piece is attached to a commission hub
    is_attached = art_piece.everAttachedToHub()
    
    if is_attached:
        # If ever attached, transfers should be blocked
        with pytest.raises(Exception) as excinfo:
            art_piece.safeTransferFrom(owner.address, receiver.address, TOKEN_ID, sender=owner)
        assert "Transfers disabled for hub-attached art pieces" in str(excinfo.value)
    else:
        # If never attached, direct owner should be able to transfer
        art_piece.safeTransferFrom(owner.address, receiver.address, TOKEN_ID, sender=owner)
        
        # Check new owner
        assert art_piece.ownerOf(TOKEN_ID) == receiver.address
        assert art_piece.getOwner() == receiver.address

def test_safeTransferFrom_to_receiver(setup):
    """Test safeTransferFrom method to ERC721Receiver contract - should fail for hub-attached art pieces"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    erc721_receiver = setup["erc721_receiver"]
    deployer = setup["deployer"]  # Use deployer as fallback receiver if needed
    
    # First verify if the piece is attached to a commission hub
    is_attached = art_piece.everAttachedToHub()
    
    # Use deployer as a fallback receiver if ERC721Receiver contract is not available
    receiver_address = deployer.address
    if erc721_receiver is not None:
        receiver_address = erc721_receiver.address
    
    if is_attached:
        # If ever attached, transfers should be blocked regardless of the receiver
        with pytest.raises(Exception) as excinfo:
            art_piece.safeTransferFrom(owner.address, receiver_address, TOKEN_ID, sender=owner)
        assert "Transfers disabled for hub-attached art pieces" in str(excinfo.value)
    else:
        # If never attached, direct owner should be able to transfer
        art_piece.safeTransferFrom(owner.address, receiver_address, TOKEN_ID, sender=owner)
        
        # Check new owner
        assert art_piece.ownerOf(TOKEN_ID) == receiver_address
        assert art_piece.getOwner() == receiver_address

def test_supportsInterface(setup):
    """Test supportsInterface method"""
    art_piece = setup["art_piece"]
    
    # Check for ERC721 interface support
    assert art_piece.supportsInterface(INTERFACE_ID_ERC721) == True
    
    # Check for ERC165 interface support
    assert art_piece.supportsInterface(INTERFACE_ID_ERC165) == True
    
    # Check for unsupported interface
    assert art_piece.supportsInterface(0x12345678) == False

def test_tokenURI(setup):
    """Test tokenURI method"""
    art_piece = setup["art_piece"]
    
    # Get token URI
    uri = art_piece.tokenURI(TOKEN_ID)
    
    # We expect a valid URI (but could be empty as mentioned in the contract)
    assert isinstance(uri, str)
    
    # Test with invalid token ID
    with pytest.raises(Exception) as excinfo:
        art_piece.tokenURI(2)  # Invalid token ID
    assert "Invalid token ID" in str(excinfo.value)

def test_attachToArtCommissionHub(setup):
    """Test attachToArtCommissionHub method"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    deployer = setup["deployer"]
    commission_hub = setup["commission_hub"]
    
    # First verify the art piece is attached to the original commission hub
    assert art_piece.attachedToArtCommissionHub() is True
    assert art_piece.getArtCommissionHubAddress() == commission_hub.address
    
    # Detach from the current hub - only the current owner (deployer) can do this
    art_piece.detachFromArtCommissionHub(sender=deployer)
    
    # Verify detachment
    assert art_piece.attachedToArtCommissionHub() is False
    
    # Deploy a new ArtCommissionHub
    new_commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Attach to the new hub (owner can do this)
    art_piece.attachToArtCommissionHub(new_commission_hub.address, sender=owner)
    
    # Verify new attachment
    assert art_piece.attachedToArtCommissionHub() is True
    assert art_piece.getArtCommissionHubAddress() == new_commission_hub.address

def test_attachToArtCommissionHub_unauthorized(setup):
    """Test attachToArtCommissionHub by unauthorized caller"""
    art_piece = setup["art_piece"]
    deployer = setup["deployer"]
    
    # Deploy a new commission hub
    new_commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deployer (not owner or artist) tries to attach
    with pytest.raises(Exception) as excinfo:
        art_piece.attachToArtCommissionHub(new_commission_hub.address, sender=deployer)
    assert "Only owner or artist can attach" in str(excinfo.value)

def test_checkOwner(setup):
    """Test checkOwner method with and without commission hub"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    deployer = setup["deployer"]
    commission_hub = setup["commission_hub"]
    
    # First verify the art piece is attached to commission hub
    assert art_piece.attachedToArtCommissionHub() is True
    assert art_piece.getArtCommissionHubAddress() == commission_hub.address
    
    # When attached to a hub, checkOwner should return the hub's owner
    assert art_piece.checkOwner() == deployer.address  # Hub owner is deployer
    
    # Detach from hub
    art_piece.detachFromArtCommissionHub(sender=deployer)  # Hub owner can detach
    
    # Verify detachment
    assert art_piece.attachedToArtCommissionHub() is False
    
    # Even after detachment, checkOwner should still return the hub owner
    # because of the permanent relationship
    assert art_piece.checkOwner() == deployer.address 

def test_transferFrom_unauthorized(setup):
    """Test transferFrom by unauthorized caller - should fail for both attached and unattached pieces"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    artist = setup["artist"]
    receiver = setup["receiver"]
    
    # First verify if the piece is attached to a commission hub
    is_attached = art_piece.everAttachedToHub()
    
    if is_attached:
        # If ever attached, transfers should be blocked for everyone
        with pytest.raises(Exception) as excinfo:
            art_piece.transferFrom(owner.address, receiver.address, TOKEN_ID, sender=artist)
        assert "Transfers disabled for hub-attached art pieces" in str(excinfo.value)
    else:
        # If never attached, only the direct owner can transfer
        with pytest.raises(Exception) as excinfo:
            art_piece.transferFrom(owner.address, receiver.address, TOKEN_ID, sender=artist)
        assert "Only direct owner can transfer" in str(excinfo.value) 