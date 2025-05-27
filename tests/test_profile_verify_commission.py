import pytest
from ape import accounts, project, chain
from ape.utils import ZERO_ADDRESS

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFCM1JKVFVVSDVBb1NEdUZvQ0FBQUFBMUpSRUZVZU5xVEVFRUFBQUE1VVBBRHhpVXFJVzRBQUFBQlNVVk9SSzVDWUlJPSJ9"
TEST_TITLE = "Test Commission"
TEST_DESCRIPTION = "Test Description"
TEST_TOKEN_URI_DATA_FORMAT = "avif"

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    hub_owner = accounts.test_accounts[3]
    
    # Deploy all templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with all templates
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        commission_hub_template.address,
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
    
    # Create profiles for artist and commissioner
    profile_factory.createProfile(artist.address, sender=deployer)
    profile_factory.createProfile(commissioner.address, sender=deployer)
    profile_factory.createProfile(hub_owner.address, sender=deployer)
    
    # Get the created profiles
    artist_profile_address = profile_factory.getProfile(artist.address)
    commissioner_profile_address = profile_factory.getProfile(commissioner.address)
    
    artist_profile = project.Profile.at(artist_profile_address)
    commissioner_profile = project.Profile.at(commissioner_profile_address)
    
    # Set artist flag
    artist_profile.setIsArtist(True, sender=artist)
    
    # Enable unverified commissions for both profiles
    artist_profile.setAllowUnverifiedCommissions(True, sender=artist)
    commissioner_profile.setAllowUnverifiedCommissions(True, sender=commissioner)
    
    # Create a commission hub for testing
    art_commission_hub_owners.createGenericCommissionHub(hub_owner.address, sender=deployer)
    
    # Get the hub address
    hubs_list = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(hub_owner.address, 0, 1, False)
    hub_address = hubs_list[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "hub_owner": hub_owner,
        "profile_factory": profile_factory,
        "art_commission_hub_owners": art_commission_hub_owners,
        "artist_profile": artist_profile,
        "commissioner_profile": commissioner_profile,
        "commission_hub": commission_hub,
        "art_piece_template": art_piece_template
    }

def test_commission_direct_verification_flow(setup):
    """Test direct verification on art piece without going through profile"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    commission_hub = setup["commission_hub"]
    art_piece_template = setup["art_piece_template"]
    
    # Act - Artist creates a commission art piece
    tx1 = artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,  # is_artist
        commissioner.address,  # other_party
        False,  # ai_generated
        commission_hub.address,
        False,  # is_profile_art
        sender=artist
    )
    
    # Get the art piece address from the return value
    art_piece_address = tx1.return_value
    print(f"Art piece address: {art_piece_address}")
    print(f"Transaction status: {tx1.status}")
    
    assert art_piece_address != ZERO_ADDRESS, "Art piece address should not be zero"
    
    # Verify the profile was updated
    profile = project.Profile.at(artist_profile.address)
    assert profile.myArtCount() == 1, "Profile should have 1 art piece"
    
    # Get the art piece from the profile's art list
    art_pieces = profile.getArtPiecesByOffset(0, 1, False)
    assert len(art_pieces) == 1, "Should have 1 art piece in the list"
    art_piece_address = art_pieces[0]
    
    # Whitelist the created art piece contract in ArtCommissionHubOwners
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    deployer = setup["deployer"]
    art_commission_hub_owners.setApprovedArtPiece(art_piece_address, True, sender=deployer)
    
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Assert - Verify initial state
    assert art_piece.artist() == artist.address, "Artist should be the creator"
    assert art_piece.commissioner() == commissioner.address, "Commissioner should be the other party"
    assert art_piece.artistVerified() == True, "Artist should be auto-verified when creating"  # Artist is auto-verified when creating
    assert art_piece.commissionerVerified() == False, "Commissioner should not be verified"
    assert art_piece.isFullyVerifiedCommission() == False, "Art piece should not be fully verified"
    
    # Act - Commissioner verifies directly on the art piece
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # Assert - Should now be fully verified
    assert art_piece.isFullyVerifiedCommission() == True
    
    # Check submission status
    submission_attempted, submission_successful = art_piece.getSubmissionStatus()
    print(f"Submission attempted: {submission_attempted}, successful: {submission_successful}")
    
    # Check if the hub is ready for submissions
    is_ready = commission_hub.isReadyForSubmissions()
    is_pending = commission_hub.isRegistrationPending()
    print(f"Hub ready: {is_ready}, registration pending: {is_pending}")
    
    # If submission failed, try to retry
    if submission_attempted and not submission_successful:
        # Check who is the hub owner
        hub_owner_addr = commission_hub.owner()
        print(f"Hub owner: {hub_owner_addr}")
        # Use the hub_owner account from setup
        hub_owner_account = setup["hub_owner"]
        art_piece.retryCommissionHubSubmission(sender=hub_owner_account)
    
    # Check both verified and unverified lists
    hub_verified = commission_hub.getVerifiedArtPiecesByOffset(0, 10)
    hub_unverified = commission_hub.getUnverifiedArtPiecesByOffset(0, 10)
    
    print(f"Hub verified list: {hub_verified}")
    print(f"Hub unverified list: {hub_unverified}")
    
    # The art piece should be in one of the lists
    assert art_piece.address in hub_verified or art_piece.address in hub_unverified, "Art piece not found in hub"
    
    # If it's in unverified, we need to verify it
    if art_piece.address in hub_unverified:
        # Verify the commission as the hub owner
        hub_owner_account = setup["hub_owner"]
        commission_hub.verifyCommission(art_piece.address, sender=hub_owner_account)
        
        # Now it should be in verified list
        hub_verified = commission_hub.getVerifiedArtPiecesByOffset(0, 10)
        assert art_piece.address in hub_verified

def test_whitelisting_effect_on_commission_placement(setup):
    """Test how whitelisting affects where commissions are placed"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    commission_hub = setup["commission_hub"]
    art_piece_template = setup["art_piece_template"]
    
    # Whitelist each other
    artist_profile.addToWhitelist(commissioner.address, sender=artist)
    commissioner_profile.addToWhitelist(artist.address, sender=commissioner)
    
    # Act - Create art piece
    tx1 = artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Whitelisted Commission",
        "Should go to verified due to whitelist",
        True,  # is_artist
        commissioner.address,
        False,  # ai_generated
        commission_hub.address,
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece_address = tx1.return_value
    
    # Get the art piece from the profile's art list (more reliable than return value)
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)  # Get most recent
    assert len(art_pieces) > 0, "Should have art pieces in the list"
    art_piece_address = art_pieces[0]
    
    # Whitelist the created art piece contract in ArtCommissionHubOwners
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    deployer = setup["deployer"]
    art_commission_hub_owners.setApprovedArtPiece(art_piece_address, True, sender=deployer)
    
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # The art piece should still need both verifications
    assert art_piece.artistVerified() == True
    assert art_piece.commissionerVerified() == False
    assert art_piece.isFullyVerifiedCommission() == False
    
    # But when commissioner adds it to their profile, it should go to verified list
    tx = commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Check if it went to verified list due to whitelisting
    commissioner_verified = commissioner_profile.getCommissionsByOffset(0, 10, False)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    
    # With whitelisting, it should go directly to verified in the profile
    # even though the art piece itself is not fully verified
    assert art_piece.address in commissioner_verified

def test_commission_role_tracking(setup):
    """Test that commission roles are properly tracked"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    commission_hub = setup["commission_hub"]
    art_piece_template = setup["art_piece_template"]
    
    # Create art piece
    tx1 = artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,  # is_artist
        commissioner.address,
        False,  # ai_generated
        commission_hub.address,
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece_address = tx1.return_value
    
    # Get the art piece from the profile's art list (more reliable than return value)
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)  # Get most recent
    assert len(art_pieces) > 0, "Should have art pieces in the list"
    art_piece_address = art_pieces[0]
    
    # Whitelist the created art piece contract in ArtCommissionHubOwners
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    deployer = setup["deployer"]
    art_commission_hub_owners.setApprovedArtPiece(art_piece_address, True, sender=deployer)
    
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Add to commissioner's profile
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Assert - Check roles
    # Artist profile should have role = True (is artist)
    assert artist_profile.myCommissionRole(art_piece.address) == True
    
    # Commissioner profile should have role = False (is commissioner)
    assert commissioner_profile.myCommissionRole(art_piece.address) == False

def test_personal_art_piece_creation(setup):
    """Test creating a personal art piece (not a commission)"""
    # Arrange
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    commission_hub = setup["commission_hub"]
    art_piece_template = setup["art_piece_template"]
    
    # Act - Create personal art piece (artist as both artist and commissioner)
    tx1 = artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Personal Art",
        "My personal artwork",
        True,  # is_artist
        artist.address,  # other_party is self
        False,  # ai_generated
        ZERO_ADDRESS,  # No hub for personal art
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece_address = tx1.return_value
    
    # Get the art piece from the profile's art list (more reliable than return value)
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)  # Get most recent
    assert len(art_pieces) > 0, "Should have art pieces in the list"
    art_piece_address = art_pieces[0]
    
    # Whitelist the created art piece contract in ArtCommissionHubOwners
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    deployer = setup["deployer"]
    art_commission_hub_owners.setApprovedArtPiece(art_piece_address, True, sender=deployer)
    
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Assert - Personal piece should be auto-verified
    assert art_piece.artist() == artist.address
    assert art_piece.commissioner() == artist.address
    assert art_piece.isPrivateOrNonCommissionPiece() == True
    assert art_piece.isFullyVerifiedCommission() == True

def test_blacklisting_behavior(setup):
    """Test blacklisting behavior in commission linking"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    commission_hub = setup["commission_hub"]
    art_piece_template = setup["art_piece_template"]
    
    # Commissioner blacklists artist
    commissioner_profile.addToBlacklist(artist.address, sender=commissioner)
    
    # Create art piece
    tx1 = artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Blacklisted Commission",
        "Should be rejected",
        True,  # is_artist
        commissioner.address,
        False,  # ai_generated
        commission_hub.address,
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece_address = tx1.return_value
    
    # Get the art piece from the profile's art list (more reliable than return value)
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)  # Get most recent
    assert len(art_pieces) > 0, "Should have art pieces in the list"
    art_piece_address = art_pieces[0]
    
    # Whitelist the created art piece contract in ArtCommissionHubOwners
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    deployer = setup["deployer"]
    art_commission_hub_owners.setApprovedArtPiece(art_piece_address, True, sender=deployer)
    
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Try to link - should return False and log a failure
    result = commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Check that it's not in any of commissioner's lists
    commissioner_verified = commissioner_profile.getCommissionsByOffset(0, 10, False)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    
    assert art_piece.address not in commissioner_verified
    assert art_piece.address not in commissioner_unverified

def test_commission_hub_submission_after_verification(setup):
    """Test that commissions are submitted to hub after full verification"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commission_hub = setup["commission_hub"]
    art_piece_template = setup["art_piece_template"]
    
    # Create art piece
    tx1 = artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        "Hub Test Commission",
        "Testing hub submission",
        True,  # is_artist
        commissioner.address,
        False,  # ai_generated
        commission_hub.address,
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece_address = tx1.return_value
    
    # Get the art piece from the profile's art list (more reliable than return value)
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)  # Get most recent
    assert len(art_pieces) > 0, "Should have art pieces in the list"
    art_piece_address = art_pieces[0]
    
    # Whitelist the created art piece contract in ArtCommissionHubOwners
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    deployer = setup["deployer"]
    art_commission_hub_owners.setApprovedArtPiece(art_piece_address, True, sender=deployer)
    
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Initially not in hub
    hub_verified = commission_hub.getVerifiedArtPiecesByOffset(0, 10)
    assert art_piece.address not in hub_verified
    
    # Verify as commissioner directly
    art_piece.verifyAsCommissioner(sender=commissioner)
    chain.mine()
    
    # Check both verified and unverified lists
    hub_verified = commission_hub.getVerifiedArtPiecesByOffset(0, 10)
    hub_unverified = commission_hub.getUnverifiedArtPiecesByOffset(0, 10)
    
    # The art piece should be in one of the lists (likely unverified since no special permissions)
    assert art_piece.address in hub_verified or art_piece.address in hub_unverified, "Art piece should be in hub"
    
    # If it's in unverified, verify it as the hub owner
    if art_piece.address in hub_unverified:
        hub_owner = setup["hub_owner"]
        commission_hub.verifyCommission(art_piece.address, sender=hub_owner)
        
        # Now it should be in verified list
        hub_verified = commission_hub.getVerifiedArtPiecesByOffset(0, 10)
        assert art_piece.address in hub_verified