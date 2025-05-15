import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    hub_owner = accounts.test_accounts[3]
    
    # Deploy ProfileFactoryAndRegistry
    profile_factory = project.ProfileFactoryAndRegistry.deploy(sender=deployer)
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Set the template in the factory
    profile_factory.updateProfileTemplateContract(project.Profile.deploy(sender=deployer), sender=deployer)
    
    # Create profiles for artist and commissioner
    profile_factory.createProfile(sender=artist)
    profile_factory.createProfile(sender=commissioner)
    
    # Get the created profiles
    artist_profile = profile_factory.getProfileByOwner(artist.address)
    commissioner_profile = profile_factory.getProfileByOwner(commissioner.address)
    
    # Deploy ArtCommissionHub
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Initialize the hub with hub_owner
    chain_id = 1
    nft_contract = deployer.address
    token_id = 1
    commission_hub.initialize(chain_id, nft_contract, token_id, hub_owner.address, sender=deployer)
    
    # Set artist flag
    artist_profile_contract = project.Profile(artist_profile)
    artist_profile_contract.setIsArtist(True, sender=artist)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "hub_owner": hub_owner,
        "profile_factory": profile_factory,
        "artist_profile": artist_profile_contract,
        "commissioner_profile": project.Profile(commissioner_profile),
        "commission_hub": commission_hub,
        "art_piece_template": art_piece_template
    }

def test_complete_commission_verification_flow(setup):
    """Test the complete commission verification flow between artist and commissioner"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Step 1: Artist creates a commission art piece for the commissioner
    art_piece_address = artist_profile.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Commission Flow",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        ZERO_ADDRESS,  # No commission hub
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece = project.ArtPiece(art_piece_address)
    
    # Verify initial state
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert art_piece.artistVerified(), "Artist side should be verified initially (artist is uploader)"
    assert not art_piece.commissionerVerified(), "Commissioner side should not be verified initially"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Check that it's in the artist's unverified list
    artist_unverified = artist_profile.getUnverifiedCommissions(0, 10)
    assert art_piece_address in artist_unverified, "Should be in artist's unverified list"
    
    # Step 2: Add the commission to the commissioner's profile
    commissioner_profile.addCommission(art_piece_address, sender=commissioner)
    
    # Check that it's in the commissioner's unverified list
    commissioner_unverified = commissioner_profile.getUnverifiedCommissions(0, 10)
    assert art_piece_address in commissioner_unverified, "Should be in commissioner's unverified list"
    
    # Step 3: Commissioner verifies the commission
    commissioner_profile.verifyCommission(art_piece_address, sender=commissioner)
    
    # Verify state after commissioner verification
    assert art_piece.artistVerified(), "Artist side should still be verified"
    assert art_piece.commissionerVerified(), "Commissioner side should now be verified"
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Step 4: Check that the commission is moved to verified lists in both profiles
    # and removed from unverified lists
    
    # Check artist profile
    artist_verified = artist_profile.getCommissions(0, 10)
    artist_unverified = artist_profile.getUnverifiedCommissions(0, 10)
    assert art_piece_address in artist_verified, "Should be in artist's verified list"
    assert art_piece_address not in artist_unverified, "Should not be in artist's unverified list"
    
    # Check commissioner profile
    commissioner_verified = commissioner_profile.getCommissions(0, 10)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissions(0, 10)
    assert art_piece_address in commissioner_verified, "Should be in commissioner's verified list"
    assert art_piece_address not in commissioner_unverified, "Should not be in commissioner's unverified list"
    
    # Step 5: Check that the commission is added to commissioner's myArt collection
    commissioner_art = commissioner_profile.getArtPieces(0, 10)
    assert art_piece_address in commissioner_art, "Should be in commissioner's myArt collection"
    
    # Step 6: Check that commission roles are set correctly
    assert artist_profile.commissionRole(art_piece_address), "Artist profile should have artist role (true)"
    assert not commissioner_profile.commissionRole(art_piece_address), "Commissioner profile should have commissioner role (false)"

def test_commission_verification_with_hub(setup):
    """Test commission verification flow with a commission hub"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Step 1: Artist creates a commission art piece for the commissioner with a hub
    art_piece_address = artist_profile.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Hub Commission",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        commission_hub.address,  # With commission hub
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece = project.ArtPiece(art_piece_address)
    
    # Verify initial state
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert art_piece.artistVerified(), "Artist side should be verified initially (artist is uploader)"
    assert not art_piece.commissionerVerified(), "Commissioner side should not be verified initially"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    assert art_piece.attachedToArtCommissionHub(), "Should be attached to commission hub"
    
    # Step 2: Add the commission to the commissioner's profile
    commissioner_profile.addCommission(art_piece_address, sender=commissioner)
    
    # Step 3: Commissioner verifies the commission
    commissioner_profile.verifyCommission(art_piece_address, sender=commissioner)
    
    # Verify state after verification
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Step 4: Check that the commission is moved to verified lists in both profiles
    artist_verified = artist_profile.getCommissions(0, 10)
    commissioner_verified = commissioner_profile.getCommissions(0, 10)
    assert art_piece_address in artist_verified, "Should be in artist's verified list"
    assert art_piece_address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Step 5: Check that the commission is in the hub's verified art list
    hub_verified = commission_hub.getVerifiedArtPieces(0, 10)
    assert art_piece_address in hub_verified, "Should be in hub's verified list"
    
    # Step 6: Check ownership - should be the hub owner
    assert art_piece.getOwner() == setup["hub_owner"].address, "Owner should be the hub owner"

def test_commissioner_initiated_verification(setup):
    """Test verification flow when commissioner initiates the process"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Step 1: Create a commission art piece with commissioner as uploader
    art_piece = project.ArtPiece.deploy(sender=setup["deployer"])
    art_piece.initialize(
        b"test_data",
        "avif",
        "Commissioner Initiated",
        "Test Description",
        commissioner.address,  # commissioner_input (uploader)
        artist.address,  # artist_input
        ZERO_ADDRESS,  # No commission hub
        False,  # ai_generated
        sender=setup["deployer"]
    )
    
    # Verify initial state
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    assert not art_piece.artistVerified(), "Artist side should not be verified initially"
    assert art_piece.commissionerVerified(), "Commissioner side should be verified initially (commissioner is uploader)"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Step 2: Add the commission to both profiles
    artist_profile.addCommission(art_piece.address, sender=artist)
    commissioner_profile.addCommission(art_piece.address, sender=commissioner)
    
    # Step 3: Artist verifies the commission
    artist_profile.verifyCommission(art_piece.address, sender=artist)
    
    # Verify state after verification
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Step 4: Check that the commission is moved to verified lists in both profiles
    artist_verified = artist_profile.getCommissions(0, 10)
    commissioner_verified = commissioner_profile.getCommissions(0, 10)
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Step 5: Check that the commission is added to commissioner's myArt collection
    commissioner_art = commissioner_profile.getArtPieces(0, 10)
    assert art_piece.address in commissioner_art, "Should be in commissioner's myArt collection"

def test_update_commission_verification_status_manual(setup):
    """Test manually updating commission verification status"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Step 1: Artist creates a commission art piece for the commissioner
    art_piece_address = artist_profile.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Manual Update",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        ZERO_ADDRESS,  # No commission hub
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece = project.ArtPiece(art_piece_address)
    
    # Step 2: Add the commission to the commissioner's profile
    commissioner_profile.addCommission(art_piece_address, sender=commissioner)
    
    # Step 3: Verify the commission directly on the art piece
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # Verify the commission is now fully verified
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Step 4: Manually update verification status in both profiles
    artist_profile.updateCommissionVerificationStatus(art_piece_address, sender=artist)
    commissioner_profile.updateCommissionVerificationStatus(art_piece_address, sender=commissioner)
    
    # Step 5: Check that the commission is moved to verified lists in both profiles
    artist_verified = artist_profile.getCommissions(0, 10)
    commissioner_verified = commissioner_profile.getCommissions(0, 10)
    assert art_piece_address in artist_verified, "Should be in artist's verified list"
    assert art_piece_address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Step 6: Check that the commission is added to commissioner's myArt collection
    commissioner_art = commissioner_profile.getArtPieces(0, 10)
    assert art_piece_address in commissioner_art, "Should be in commissioner's myArt collection"

    # Assert the art piece was created correctly
    assert art_piece.getCommissioner() == commissioner.address, "Commissioner should be set correctly"
    assert art_piece.getArtist() == artist.address, "Artist should be set correctly"
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    
    # Assert the art piece is in the unverified commissions list
    unverified_commissions = artist_profile.getUnverifiedCommissions(0, 10)
    assert art_piece_address in unverified_commissions, "Art piece should be in unverified commissions"
    
    # Assert the art piece is not in the verified commissions list
    verified_commissions = artist_profile.getCommissions(0, 10)
    assert art_piece_address not in verified_commissions, "Art piece should not be in verified commissions yet"

    # Assert the art piece was created correctly
    assert art_piece.getCommissioner() == commissioner.address, "Commissioner should be set correctly"
    assert art_piece.getArtist() == artist.address, "Artist should be set correctly"
    assert art_piece.isUnverifiedCommission(), "Should be an unverified commission"
    
    # Assert the art piece is in the unverified commissions list for the commissioner
    unverified_commissions = commissioner_profile.getUnverifiedCommissions(0, 10)
    assert art_piece_address in unverified_commissions, "Art piece should be in commissioner's unverified commissions" 