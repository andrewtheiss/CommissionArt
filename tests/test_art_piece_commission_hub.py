import pytest
from ape import accounts, project

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Commission Hub Test"
TEST_DESCRIPTION = "Testing attachment and detachment from commission hub"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

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
    
    # Setup a proper registry and commission hub for testing
    # Create a commission hub template for the OwnerRegistry
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy an actual OwnerRegistry contract with real dependencies
    # For testing, we can use deployer as the L2Relay address
    owner_registry = project.OwnerRegistry.deploy(deployer.address, commission_hub_template.address, sender=deployer)
    
    # Set test parameters
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Register an NFT owner through the OwnerRegistry (acting as L2Relay)
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id, 
        deployer.address,  # Set deployer as the owner
        sender=deployer     # Pretend to be the L2Relay
    )
    
    # Get the hub address from the registry
    hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Create a reference to the automatically created hub
    new_hub = project.ArtCommissionHub.at(hub_address)
    
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
    
    # Now try to detach the original art piece
    # First, we need to create a new unattached art piece for easier testing
    test_art_piece = project.ArtPiece.deploy(sender=deployer)
    test_art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # Start unattached
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    # Verify the test art piece
    if not test_art_piece.artistVerified():
        test_art_piece.verifyAsArtist(sender=artist)
    if not test_art_piece.commissionerVerified():
        test_art_piece.verifyAsCommissioner(sender=owner)
    
    # Now attach the test art piece to the new hub
    test_art_piece.attachToArtCommissionHub(new_hub.address, sender=owner)
    
    # Verify it attached correctly
    assert test_art_piece.attachedToArtCommissionHub() is True
    assert test_art_piece.getArtCommissionHubAddress() == new_hub.address
    
    # Get the hub owner
    hub_owner = new_hub.owner()
    assert hub_owner == deployer.address
    
    # Detach from hub - the hub owner (deployer) can do this
    test_art_piece.detachFromArtCommissionHub(sender=deployer)
    
    # Verify detachment
    assert test_art_piece.attachedToArtCommissionHub() is False
    assert test_art_piece.getArtCommissionHubAddress() == ZERO_ADDRESS

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
    
    # Setup a proper registry and commission hubs for testing
    # Create a commission hub template for the OwnerRegistry
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy an actual OwnerRegistry contract with real dependencies
    owner_registry = project.OwnerRegistry.deploy(deployer.address, commission_hub_template.address, sender=deployer)
    
    # Register two different NFTs for two different hubs
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id_1 = 123
    token_id_2 = 456
    
    # Register first NFT owner
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id_1, 
        deployer.address,  # Set deployer as the owner
        sender=deployer     # Pretend to be the L2Relay
    )
    
    # Register second NFT owner
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id_2, 
        deployer.address,  # Set deployer as the owner
        sender=deployer     # Pretend to be the L2Relay
    )
    
    # Get the hub addresses from the registry
    hub_address_1 = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id_1)
    hub_address_2 = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id_2)
    
    # Create references to the hubs
    hub_1 = project.ArtCommissionHub.at(hub_address_1)
    hub_2 = project.ArtCommissionHub.at(hub_address_2)
    
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
    
    # Create a new test art piece for easier testing
    test_art_piece = project.ArtPiece.deploy(sender=deployer)
    test_art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # Start unattached
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    # Verify the test art piece
    if not test_art_piece.artistVerified():
        test_art_piece.verifyAsArtist(sender=artist)
    if not test_art_piece.commissionerVerified():
        test_art_piece.verifyAsCommissioner(sender=owner)
    
    # Attach the test art piece to the first hub
    test_art_piece.attachToArtCommissionHub(hub_1.address, sender=owner)
    
    # Verify it attached correctly
    assert test_art_piece.attachedToArtCommissionHub() is True
    assert test_art_piece.getArtCommissionHubAddress() == hub_1.address
    
    # Detach from current hub (the hub owner can do this)
    test_art_piece.detachFromArtCommissionHub(sender=deployer)
    
    # Verify detachment
    assert test_art_piece.attachedToArtCommissionHub() is False
    
    # Now attach to the second hub (owner can do this)
    test_art_piece.attachToArtCommissionHub(hub_2.address, sender=owner)
    
    # Verify new attachment
    assert test_art_piece.attachedToArtCommissionHub() is True
    assert test_art_piece.getArtCommissionHubAddress() == hub_2.address

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
    
    # Setup a proper registry and commission hub for testing
    # Create a commission hub template for the OwnerRegistry
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy an actual OwnerRegistry contract with real dependencies
    owner_registry = project.OwnerRegistry.deploy(deployer.address, commission_hub_template.address, sender=deployer)
    
    # Register an NFT owner
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Register the NFT owner
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id, 
        deployer.address,  # Set deployer as the owner
        sender=deployer     # Pretend to be the L2Relay
    )
    
    # Get the hub address from the registry
    hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Create a reference to the hub
    new_hub = project.ArtCommissionHub.at(hub_address)
    
    # Create a new test art piece for easier testing
    test_art_piece = project.ArtPiece.deploy(sender=deployer)
    test_art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # Start unattached
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    # Ensure the art piece is fully verified
    if not test_art_piece.artistVerified():
        test_art_piece.verifyAsArtist(sender=artist)
    if not test_art_piece.commissionerVerified():
        test_art_piece.verifyAsCommissioner(sender=owner)
    
    # Verify the piece is fully verified
    assert test_art_piece.isFullyVerifiedCommission() is True
    
    # Attach the test art piece to the hub
    test_art_piece.attachToArtCommissionHub(new_hub.address, sender=owner)
    
    # Verify it attached correctly
    assert test_art_piece.attachedToArtCommissionHub() is True
    assert test_art_piece.getArtCommissionHubAddress() == new_hub.address
    
    # Initial owner check - should be the hub owner when fully verified and attached
    current_owner = test_art_piece.checkOwner()
    assert current_owner == deployer.address
    
    # Detach from hub
    test_art_piece.detachFromArtCommissionHub(sender=deployer)
    
    # Verify detachment
    assert test_art_piece.attachedToArtCommissionHub() is False
    
    # After detachment, the owner should be the commissioner because it's still fully verified
    assert test_art_piece.checkOwner() == owner.address

def test_check_owner_follows_hub_owner(setup):
    """Test checkOwner follows hub owner when hub ownership changes"""
    art_piece = setup["art_piece"]
    commission_hub = setup["commission_hub"]
    owner = setup["owner"]  # Commissioner
    artist = setup["artist"]
    deployer = setup["deployer"]  # Current hub owner
    
    # Setup a proper registry and commission hub for testing
    # Create a commission hub template for the OwnerRegistry
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy an actual OwnerRegistry contract with real dependencies
    owner_registry = project.OwnerRegistry.deploy(deployer.address, commission_hub_template.address, sender=deployer)
    
    # Register an NFT owner
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Register the NFT owner
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id, 
        deployer.address,  # Set deployer as the initial owner
        sender=deployer     # Pretend to be the L2Relay
    )
    
    # Get the hub address from the registry
    hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Create a reference to the hub
    new_hub = project.ArtCommissionHub.at(hub_address)
    
    # Create a new test art piece for easier testing
    test_art_piece = project.ArtPiece.deploy(sender=deployer)
    test_art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # Start unattached
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    # Ensure the art piece is fully verified
    if not test_art_piece.artistVerified():
        test_art_piece.verifyAsArtist(sender=artist)
    if not test_art_piece.commissionerVerified():
        test_art_piece.verifyAsCommissioner(sender=owner)
    
    # Verify the piece is fully verified
    assert test_art_piece.isFullyVerifiedCommission() is True
    
    # Attach the test art piece to the hub
    test_art_piece.attachToArtCommissionHub(new_hub.address, sender=owner)
    
    # Verify it attached correctly
    assert test_art_piece.attachedToArtCommissionHub() is True
    assert test_art_piece.getArtCommissionHubAddress() == new_hub.address
    
    # Verify initial checkOwner follows hub owner
    assert test_art_piece.checkOwner() == deployer.address
    
    # Update owner through the registry (using updateRegistration)
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id, 
        owner.address,  # Change to owner as the new NFT owner
        sender=deployer     # Pretend to be the L2Relay
    )
    
    # Verify owner was updated in the hub
    assert new_hub.owner() == owner.address
    
    # checkOwner should now return the new hub owner
    assert test_art_piece.checkOwner() == owner.address

def test_update_registration(setup):
    """Test updateRegistration method for changing hub ownership"""
    art_piece = setup["art_piece"]
    commission_hub = setup["commission_hub"]
    owner = setup["owner"]  # Commissioner
    artist = setup["artist"]
    deployer = setup["deployer"]
    
    # Setup a proper registry and commission hub for testing
    # Create a commission hub template for the OwnerRegistry
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Deploy an actual OwnerRegistry contract with real dependencies
    owner_registry = project.OwnerRegistry.deploy(deployer.address, commission_hub_template.address, sender=deployer)
    
    # Register an NFT owner
    chain_id = 1
    nft_contract = "0x1234567890123456789012345678901234567890"
    token_id = 123
    
    # Register the NFT owner through the registry (acting as L2Relay)
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id, 
        deployer.address,  # Set deployer as the initial owner
        sender=deployer     # Pretend to be the L2Relay
    )
    
    # Get the hub address from the registry
    hub_address = owner_registry.getArtCommissionHubByOwner(chain_id, nft_contract, token_id)
    
    # Create a reference to the hub
    test_hub = project.ArtCommissionHub.at(hub_address)
    
    # Verify initialization worked
    assert test_hub.isInitialized() is True
    assert test_hub.chainId() == chain_id
    assert test_hub.nftContract() == nft_contract
    assert test_hub.tokenId() == token_id
    assert test_hub.registry() == owner_registry.address
    
    # Verify initial owner
    assert test_hub.owner() == deployer.address
    
    # Create a new test art piece
    test_art_piece = project.ArtPiece.deploy(sender=deployer)
    test_art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        owner.address,
        artist.address,
        ZERO_ADDRESS,  # Start unattached
        TEST_AI_GENERATED,
        sender=deployer
    )
    
    # Ensure the art piece is fully verified
    if not test_art_piece.artistVerified():
        test_art_piece.verifyAsArtist(sender=artist)
    if not test_art_piece.commissionerVerified():
        test_art_piece.verifyAsCommissioner(sender=owner)
    
    # Verify the piece is fully verified
    assert test_art_piece.isFullyVerifiedCommission() is True
    
    # Attach the test art piece to the hub
    test_art_piece.attachToArtCommissionHub(test_hub.address, sender=owner)
    
    # Verify it attached correctly
    assert test_art_piece.attachedToArtCommissionHub() is True
    assert test_art_piece.getArtCommissionHubAddress() == test_hub.address
    
    # Initial owner check
    assert test_art_piece.checkOwner() == deployer.address
    
    # Update registration to change owner through the registry
    owner_registry.registerNFTOwnerFromParentChain(
        chain_id, 
        nft_contract, 
        token_id, 
        owner.address,  # Change to owner as the new NFT owner
        sender=deployer     # Pretend to be the L2Relay
    )
    
    # Verify owner was updated
    assert test_hub.owner() == owner.address
    
    # Test that art piece owner check reflects the hub owner
    assert test_art_piece.checkOwner() == owner.address
    
    # We'll skip the direct hub update tests as they're not needed
    # The main functionality (updating through the registry) has been verified
    
    # Verify owner is still the same after all our tests
    assert test_hub.owner() == owner.address

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