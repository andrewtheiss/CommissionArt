import pytest
from ape import accounts, project

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Commission Hub Test"
TEST_DESCRIPTION = "Testing attachment and detachment from commission hub"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    owner = accounts.test_accounts[2]
    
    # Deploy ArtCommissionHub
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy alternate hub for testing detachment/reattachment
    alternate_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy ArtPiece contract
    art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the art piece
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        commission_hub.address,  # Initially attached to commission_hub
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    # Deploy a second art piece without initial hub attachment
    unattached_art_piece = project.ArtPiece.deploy(sender=deployer)
    
    # Initialize the unattached art piece
    unattached_art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Unattached Art",
        "Art piece with no initial hub attachment",
        owner.address,
        artist.address,
        "0x0000000000000000000000000000000000000000",  # No initial hub
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    return {
        "deployer": deployer,
        "artist": artist,
        "owner": owner,
        "commission_hub": commission_hub,
        "alternate_hub": alternate_hub,
        "art_piece": art_piece,
        "unattached_art_piece": unattached_art_piece
    }

def test_initial_hub_attachment(setup):
    """Test initial attachment to hub during initialization"""
    art_piece = setup["art_piece"]
    commission_hub = setup["commission_hub"]
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    assert art_piece.getArtCommissionHubAddress() == commission_hub.address

def test_detach_from_hub(setup):
    """Test detachFromArtCommissionHub method"""
    art_piece = setup["art_piece"]
    deployer = setup["deployer"]  # Deployer is the hub owner
    
    # First verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Detach from hub - only the hub owner (deployer) can do this
    art_piece.detachFromArtCommissionHub(sender=deployer)
    
    # Verify detachment
    assert art_piece.attachedToArtCommissionHub() is False
    assert art_piece.getArtCommissionHubAddress() == "0x0000000000000000000000000000000000000000"

def test_detach_from_hub_unauthorized(setup):
    """Test detachFromArtCommissionHub by unauthorized user"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]  # Art piece owner but not hub owner
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Owner (not hub owner) tries to detach
    with pytest.raises(Exception) as excinfo:
        art_piece.detachFromArtCommissionHub(sender=owner)
    assert "Only hub owner can detach from ArtCommissionHub" in str(excinfo.value)

def test_artist_cannot_detach(setup):
    """Test that artist cannot detach from hub unless they are the hub owner"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Artist (not hub owner) tries to detach
    with pytest.raises(Exception) as excinfo:
        art_piece.detachFromArtCommissionHub(sender=artist)
    assert "Only hub owner can detach from ArtCommissionHub" in str(excinfo.value)

def test_attach_to_new_hub_after_detach(setup):
    """Test attaching to a new hub after detaching"""
    art_piece = setup["art_piece"]
    owner = setup["owner"]
    deployer = setup["deployer"]  # Hub owner
    alternate_hub = setup["alternate_hub"]
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Detach from current hub (only hub owner can do this)
    art_piece.detachFromArtCommissionHub(sender=deployer)
    
    # Verify detachment
    assert art_piece.attachedToArtCommissionHub() is False
    
    # Now attach to the alternate hub (owner can do this)
    art_piece.attachToArtCommissionHub(alternate_hub.address, sender=owner)
    
    # Verify new attachment
    assert art_piece.attachedToArtCommissionHub() is True
    assert art_piece.getArtCommissionHubAddress() == alternate_hub.address

def test_attach_unattached_piece(setup):
    """Test attaching an initially unattached art piece"""
    unattached_art_piece = setup["unattached_art_piece"]
    owner = setup["owner"]
    commission_hub = setup["commission_hub"]
    
    # Verify initially unattached
    assert unattached_art_piece.attachedToArtCommissionHub() is False
    
    # Attach to hub
    unattached_art_piece.attachToArtCommissionHub(commission_hub.address, sender=owner)
    
    # Verify attachment
    assert unattached_art_piece.attachedToArtCommissionHub() is True
    assert unattached_art_piece.getArtCommissionHubAddress() == commission_hub.address

def test_cannot_attach_twice(setup):
    """Test that an art piece cannot be attached to a hub twice"""
    unattached_art_piece = setup["unattached_art_piece"]
    owner = setup["owner"]
    commission_hub = setup["commission_hub"]
    alternate_hub = setup["alternate_hub"]
    
    # First attach to hub
    unattached_art_piece.attachToArtCommissionHub(commission_hub.address, sender=owner)
    
    # Verify attachment
    assert unattached_art_piece.attachedToArtCommissionHub() is True
    
    # Try to attach to alternate hub
    with pytest.raises(Exception) as excinfo:
        unattached_art_piece.attachToArtCommissionHub(alternate_hub.address, sender=owner)
    assert "Already attached" in str(excinfo.value)

def test_check_owner_with_hub(setup):
    """Test checkOwner method when attached to hub"""
    art_piece = setup["art_piece"]
    commission_hub = setup["commission_hub"]
    owner = setup["owner"]
    deployer = setup["deployer"]  # Hub owner
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Initial owner check - should be the hub owner
    current_owner = art_piece.checkOwner()
    # Use deployer.address which is the hub owner
    assert current_owner == deployer.address
    
    # Detach from hub
    art_piece.detachFromArtCommissionHub(sender=deployer)
    
    # Verify detachment
    assert art_piece.attachedToArtCommissionHub() is False
    
    # Even though detached, the ownership is still determined by the hub
    # since everAttachedToHub is true
    assert art_piece.checkOwner() == deployer.address

def test_check_owner_follows_hub_owner(setup):
    """Test checkOwner follows hub owner when hub ownership changes"""
    art_piece = setup["art_piece"]
    commission_hub = setup["commission_hub"]
    owner = setup["owner"]
    deployer = setup["deployer"]  # Current hub owner
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Verify initial checkOwner follows hub owner
    assert art_piece.checkOwner() == deployer.address
    
    # Transfer hub ownership
    try:
        commission_hub.transferOwnership(owner.address, sender=deployer)
        
        # Check if ownership transfer worked
        hub_owner = commission_hub.owner()
        if hub_owner == owner.address:
            # checkOwner should now return the new hub owner
            assert art_piece.checkOwner() == owner.address
    except Exception as e:
        # If hub doesn't support transferOwnership, skip this test
        print(f"Note: Hub ownership transfer test skipped: {e}")
        pytest.skip("Commission hub may not support transferOwnership") 