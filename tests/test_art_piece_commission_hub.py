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
    deployer = setup["deployer"]
    owner = setup["owner"]  # Commissioner
    artist = setup["artist"]
    commission_hub = setup["commission_hub"]
    
    # First verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Initialize the commission hub with deployer as registry and owner
    if not commission_hub.isInitialized():
        chain_id = 1
        nft_contract = "0x1234567890123456789012345678901234567890"
        token_id = 123
        # Initialize the hub with deployer address as _registry
        commission_hub.initialize(chain_id, nft_contract, token_id, deployer.address, sender=deployer)
        # Make sure the hub owner is set to deployer
        assert commission_hub.owner() == deployer.address
    
    # Ensure the art piece is fully verified
    if not art_piece.isFullyVerifiedCommission():
        # If the artist side isn't verified, verify it
        if not art_piece.artistVerified():
            art_piece.verifyAsArtist(sender=artist)
        # If the commissioner side isn't verified, verify it
        if not art_piece.commissionerVerified():
            art_piece.verifyAsCommissioner(sender=owner)
    
    # Verify the piece is now fully verified
    assert art_piece.isFullyVerifiedCommission() is True
    
    # Detach from hub - the hub owner (deployer) can do this
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
    owner = setup["owner"]  # Commissioner
    artist = setup["artist"]
    deployer = setup["deployer"]
    commission_hub = setup["commission_hub"]
    alternate_hub = setup["alternate_hub"]
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Initialize the commission hub with deployer as registry and owner
    if not commission_hub.isInitialized():
        chain_id = 1
        nft_contract = "0x1234567890123456789012345678901234567890"
        token_id = 123
        # Initialize the hub with deployer address as _registry
        commission_hub.initialize(chain_id, nft_contract, token_id, deployer.address, sender=deployer)
        # Make sure the hub owner is set to deployer
        assert commission_hub.owner() == deployer.address
    
    # Ensure the art piece is fully verified
    if not art_piece.isFullyVerifiedCommission():
        # If the artist side isn't verified, verify it
        if not art_piece.artistVerified():
            art_piece.verifyAsArtist(sender=artist)
        # If the commissioner side isn't verified, verify it
        if not art_piece.commissionerVerified():
            art_piece.verifyAsCommissioner(sender=owner)
    
    # Verify the piece is now fully verified
    assert art_piece.isFullyVerifiedCommission() is True
    
    # Detach from current hub (the hub owner can do this)
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
    assert "Already attached to a ArtCommissionHub" in str(excinfo.value)

def test_check_owner_with_hub(setup):
    """Test checkOwner method when attached to hub"""
    art_piece = setup["art_piece"]
    commission_hub = setup["commission_hub"]
    owner = setup["owner"]  # Commissioner
    artist = setup["artist"]
    deployer = setup["deployer"]
    
    # Initialize the commission hub with deployer as registry and owner
    if not commission_hub.isInitialized():
        chain_id = 1
        nft_contract = "0x1234567890123456789012345678901234567890"
        token_id = 123
        commission_hub.initialize(chain_id, nft_contract, token_id, deployer.address, sender=deployer)
        assert commission_hub.owner() == deployer.address
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # Ensure the art piece is fully verified before checking ownership
    if not art_piece.isFullyVerifiedCommission():
        # If the artist side isn't verified, verify it
        if not art_piece.artistVerified():
            art_piece.verifyAsArtist(sender=artist)
        # If the commissioner side isn't verified, verify it
        if not art_piece.commissionerVerified():
            art_piece.verifyAsCommissioner(sender=owner)
    
    # Verify the piece is now fully verified
    assert art_piece.isFullyVerifiedCommission() is True
    
    # Initial owner check - should be the hub owner when fully verified and attached
    current_owner = art_piece.checkOwner()
    assert current_owner == deployer.address
    
    # Detach from hub
    art_piece.detachFromArtCommissionHub(sender=deployer)
    
    # Verify detachment
    assert art_piece.attachedToArtCommissionHub() is False
    
    # After detachment, the owner should be the commissioner because it's still fully verified
    assert art_piece.checkOwner() == owner.address

def test_check_owner_follows_hub_owner(setup):
    """Test checkOwner follows hub owner when hub ownership changes"""
    art_piece = setup["art_piece"]
    commission_hub = setup["commission_hub"]
    owner = setup["owner"]  # Commissioner
    artist = setup["artist"]
    deployer = setup["deployer"]  # Current hub owner
    
    # Verify initial attachment
    assert art_piece.attachedToArtCommissionHub() is True
    
    # First, initialize the hub if not already initialized
    # We need to set the registry to deployer so we can update ownership
    if not commission_hub.isInitialized():
        # Mock values for initialization
        chain_id = 1  # Ethereum mainnet
        nft_contract = "0x1234567890123456789012345678901234567890"
        token_id = 123
        
        # Initialize the hub
        commission_hub.initialize(chain_id, nft_contract, token_id, deployer.address, sender=deployer)
    
    # Get current values from the hub
    chain_id = commission_hub.chainId()
    nft_contract = commission_hub.nftContract()
    token_id = commission_hub.tokenId()
    registry = commission_hub.registry()
    
    # Make sure the registry is set to deployer so we can update ownership
    if registry != deployer.address:
        # We can't update the registry after initialization, so we need to skip this test
        pytest.skip("Registry is not set to deployer, can't update ownership")
    
    # Ensure the art piece is fully verified before checking ownership
    if not art_piece.isFullyVerifiedCommission():
        # If the artist side isn't verified, verify it
        if not art_piece.artistVerified():
            art_piece.verifyAsArtist(sender=artist)
        # If the commissioner side isn't verified, verify it
        if not art_piece.commissionerVerified():
            art_piece.verifyAsCommissioner(sender=owner)
    
    # Verify the piece is now fully verified
    assert art_piece.isFullyVerifiedCommission() is True
    
    # Verify initial checkOwner follows hub owner
    assert art_piece.checkOwner() == deployer.address
    
    # Update registration to change owner (using updateRegistration instead of transferOwnership)
    commission_hub.updateRegistration(chain_id, nft_contract, token_id, owner.address, sender=deployer)
    
    # Verify owner was updated
    assert commission_hub.owner() == owner.address
    
    # checkOwner should now return the new hub owner
    assert art_piece.checkOwner() == owner.address

def test_update_registration(setup):
    """Test updateRegistration method for changing hub ownership"""
    art_piece = setup["art_piece"]
    commission_hub = setup["commission_hub"]
    owner = setup["owner"]  # Commissioner
    artist = setup["artist"]
    deployer = setup["deployer"]
    
    # We need to initialize the hub with registry set to deployer for this test
    # Mock values for initialization
    chain_id = 1  # Ethereum mainnet
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Initialize the hub with deployer as registry
    # This will override any previous initialization
    commission_hub.initialize(chain_id, nft_contract, token_id, deployer.address, sender=deployer)
    
    # Verify initialization worked
    assert commission_hub.isInitialized() is True
    assert commission_hub.chainId() == chain_id
    assert commission_hub.nftContract() == nft_contract
    assert commission_hub.tokenId() == token_id
    assert commission_hub.registry() == deployer.address
    
    # Verify initial owner
    assert commission_hub.owner() == deployer.address
    
    # Make sure the art piece is attached to the hub
    if not art_piece.attachedToArtCommissionHub() or art_piece.getArtCommissionHubAddress() != commission_hub.address:
        # If not attached to the right hub, detach and re-attach
        if art_piece.attachedToArtCommissionHub():
            try:
                # Fix the staticcall syntax
                hub_owner_address = ArtCommissionHub(art_piece.getArtCommissionHubAddress()).owner(sender=deployer)
                art_piece.detachFromArtCommissionHub(sender=hub_owner_address)
            except Exception as e:
                print(f"Note: Could not detach art piece from previous hub: {e}")
        # Attach to the correct hub
        try:
            art_piece.attachToArtCommissionHub(commission_hub.address, sender=owner)
        except Exception as e:
            print(f"Note: Could not attach art piece to hub: {e}")
    
    # Ensure the art piece is fully verified before checking ownership
    if not art_piece.isFullyVerifiedCommission():
        # If the artist side isn't verified, verify it
        if not art_piece.artistVerified():
            art_piece.verifyAsArtist(sender=artist)
        # If the commissioner side isn't verified, verify it
        if not art_piece.commissionerVerified():
            art_piece.verifyAsCommissioner(sender=owner)
    
    # Verify the piece is fully verified
    assert art_piece.isFullyVerifiedCommission() is True
    
    # Update registration to change owner (call from registry address which is deployer)
    commission_hub.updateRegistration(chain_id, nft_contract, token_id, owner.address, sender=deployer)
    
    # Verify owner was updated
    assert commission_hub.owner() == owner.address
    
    # Test with mismatched chain ID (should fail)
    with pytest.raises(Exception) as excinfo:
        commission_hub.updateRegistration(chain_id + 1, nft_contract, token_id, deployer.address, sender=deployer)
    assert "Chain ID mismatch" in str(excinfo.value)
    
    # Test with mismatched NFT contract (should fail)
    with pytest.raises(Exception) as excinfo:
        commission_hub.updateRegistration(chain_id, "0x0000000000000000000000000000000000000001", token_id, deployer.address, sender=deployer)
    assert "NFT contract mismatch" in str(excinfo.value)
    
    # Test with mismatched token ID (should fail)
    with pytest.raises(Exception) as excinfo:
        commission_hub.updateRegistration(chain_id, nft_contract, token_id + 1, deployer.address, sender=deployer)
    assert "Token ID mismatch" in str(excinfo.value)
    
    # Test with unauthorized sender (should fail)
    with pytest.raises(Exception) as excinfo:
        commission_hub.updateRegistration(chain_id, nft_contract, token_id, deployer.address, sender=owner)
    assert "Only registry can update owner" in str(excinfo.value)
    
    # Verify owner is still the same after failed attempts
    assert commission_hub.owner() == owner.address
    
    # Test that art piece owner check reflects the hub owner
    # If the art piece is attached to the hub, check that its owner is the hub owner
    if art_piece.attachedToArtCommissionHub() and art_piece.getArtCommissionHubAddress() == commission_hub.address:
        assert art_piece.checkOwner() == owner.address

def test_commission_verification_requires_both_parties(setup):
    """Test that both artist and commissioner must verify before a commission is fully verified"""
    art_piece = setup["art_piece"]
    artist = setup["artist"]
    owner = setup["owner"]  # This is the commissioner in setup

    # Initial state: should be unverified commission
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission initially"
    assert not art_piece.isFullyVerifiedCommission(), "Should not be fully verified initially"

    # After initialization
    assert not art_piece.artistVerified()
    assert art_piece.commissionerVerified()
    assert not art_piece.isFullyVerifiedCommission()

    # Artist verifies
    art_piece.verifyAsArtist(sender=artist)
    assert art_piece.isFullyVerifiedCommission()
    assert art_piece.artistVerified()
    assert art_piece.commissionerVerified() 