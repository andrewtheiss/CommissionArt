import pytest
from ape import accounts, project

# Test data
TEST_TOKEN_URI_DATA = b"data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJCTndJREFBQUFCbEJNVkVYLy8vL24vNGJsQUFBQUJYUlNUbk1BUUtKZVVtUktBQUFBQWtsRVFWUUkxMkJnQUFNRE1BQUJoVUFCQUVtQ0FVQUFBQUJKUlU1RXJrSmdnZz09In0="
TEST_TITLE = "Commission Test"
TEST_DESCRIPTION = "Testing commission verification flow"
TEST_TOKEN_URI_DATA_FORMAT = "avif"
TEST_AI_GENERATED = False
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    """Setup function that deploys and initializes all contracts needed for testing"""
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    hub_owner = accounts.test_accounts[3]
    
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
    
    # Create profiles for test accounts
    profile_factory.createProfile(artist.address, sender=deployer)
    profile_factory.createProfile(commissioner.address, sender=deployer)
    profile_factory.createProfile(hub_owner.address, sender=deployer)
    
    # Get profile addresses
    artist_profile_address = profile_factory.getProfile(artist.address)
    commissioner_profile_address = profile_factory.getProfile(commissioner.address)
    hub_owner_profile_address = profile_factory.getProfile(hub_owner.address)
    
    # Create references to profiles
    artist_profile = project.Profile.at(artist_profile_address)
    commissioner_profile = project.Profile.at(commissioner_profile_address)
    hub_owner_profile = project.Profile.at(hub_owner_profile_address)
    
    # Create a commission hub through the registry - owned by hub_owner
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
        "commission_hub": commission_hub,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template,
        "hub_address": hub_address,
        "artist_profile": artist_profile,
        "commissioner_profile": commissioner_profile,
        "hub_owner_profile": hub_owner_profile,
        "art_piece_template": art_piece_template
    }

def test_complete_commission_verification_flow(setup):
    """Test the complete commission verification flow from creation to final verification"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    hub_address = setup["hub_address"]
    commission_hub = setup["commission_hub"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    profile_factory = setup["profile_factory"]
    
    # Create art piece with commission hub attached
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        commissioner.address,
        artist.address,
        hub_address,  # Attach to commission hub
        TEST_AI_GENERATED,
        artist.address,  # original uploader
        profile_factory.address,
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Initial state - should be unverified commission
    assert art_piece.isUnverifiedCommission(), "Should be unverified commission initially"
    assert not art_piece.isFullyVerifiedCommission(), "Should not be fully verified initially"
    assert not art_piece.artistVerified(), "Artist should not be verified initially"
    assert not art_piece.commissionerVerified(), "Commissioner should not be verified initially"
    
    # Artist verifies first
    art_piece.verifyAsArtist(sender=artist)
    
    # Check state after artist verification
    assert art_piece.artistVerified(), "Artist should be verified"
    assert not art_piece.commissionerVerified(), "Commissioner should not be verified yet"
    assert not art_piece.isFullyVerifiedCommission(), "Should not be fully verified yet"
    
    # Commissioner verifies to complete verification
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # Check final state
    assert art_piece.artistVerified(), "Artist should still be verified"
    assert art_piece.commissionerVerified(), "Commissioner should now be verified"
    assert art_piece.isFullyVerifiedCommission(), "Should be fully verified now"
    
    # Check that commission was submitted to hub (should be in unverified list since no whitelist)
    assert commission_hub.countUnverifiedArtCommissions() == 1, "Should have 1 unverified commission in hub"
    assert commission_hub.countVerifiedArtCommissions() == 0, "Should have 0 verified commissions in hub"
    
    # The commission should be automatically linked to both profiles during verification
    # But the commissioner needs an additional call to get it in their art collection
    commissioner_profile.updateCommissionVerificationStatus(art_piece.address, sender=commissioner)
    
    # Check that commissions are linked to profiles
    # Artist should have it in their commissions
    artist_commissions = artist_profile.getCommissionsByOffset(0, 10, False)
    assert len(artist_commissions) == 1, "Should be in artist's commission list"
    assert artist_commissions[0] == art_piece.address, "Should be the correct art piece"
    
    # Commissioner should have it in their art collection
    commissioner_art = commissioner_profile.getArtPiecesByOffset(0, 10, False)
    assert len(commissioner_art) == 1, "Should be in commissioner's art collection"
    assert commissioner_art[0] == art_piece.address, "Should be the correct art piece"

def test_commission_verification_with_hub(setup):
    """Test commission verification when attached to a hub"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    hub_owner = setup["hub_owner"]
    hub_address = setup["hub_address"]
    commission_hub = setup["commission_hub"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Create art piece with commission hub attached
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        commissioner.address,
        artist.address,
        hub_address,  # Attach to commission hub
        TEST_AI_GENERATED,
        artist.address,  # original uploader
        profile_factory.address,
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Before verification, owner should be the original uploader (artist)
    assert art_piece.checkOwner() == artist.address, "Owner should be artist before verification"
    
    # Complete verification
    art_piece.verifyAsArtist(sender=artist)
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # After verification and hub attachment, owner should be hub owner
    assert art_piece.isFullyVerifiedCommission(), "Should be fully verified"
    assert art_piece.checkOwner() == hub_owner.address, "Owner should be hub owner after verification"

def test_commissioner_initiated_verification(setup):
    """Test verification flow when commissioner verifies first"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    hub_address = setup["hub_address"]
    commission_hub = setup["commission_hub"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Create art piece with commission hub attached
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        commissioner.address,
        artist.address,
        hub_address,  # Attach to commission hub
        TEST_AI_GENERATED,
        artist.address,  # original uploader
        profile_factory.address,
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Commissioner verifies first
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # Check state after commissioner verification
    assert not art_piece.artistVerified(), "Artist should not be verified yet"
    assert art_piece.commissionerVerified(), "Commissioner should be verified"
    assert not art_piece.isFullyVerifiedCommission(), "Should not be fully verified yet"
    
    # Artist verifies to complete verification
    art_piece.verifyAsArtist(sender=artist)
    
    # Check final state
    assert art_piece.artistVerified(), "Artist should now be verified"
    assert art_piece.commissionerVerified(), "Commissioner should still be verified"
    assert art_piece.isFullyVerifiedCommission(), "Should be fully verified now"

def test_update_commission_verification_status_manual(setup):
    """Test manual update of commission verification status through profiles"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    hub_address = setup["hub_address"]
    commission_hub = setup["commission_hub"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    profile_factory = setup["profile_factory"]
    
    # Create art piece with commission hub attached
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        commissioner.address,
        artist.address,
        hub_address,  # Attach to commission hub
        TEST_AI_GENERATED,
        artist.address,  # original uploader
        profile_factory.address,
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Enable unverified commissions for both profiles
    artist_profile.setAllowUnverifiedCommissions(True, sender=artist)
    commissioner_profile.setAllowUnverifiedCommissions(True, sender=commissioner)
    
    # Manually link the art piece to both profiles as unverified
    artist_profile.linkArtPieceAsMyCommission(art_piece.address, sender=artist)
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Check initial state - should be in unverified lists
    artist_unverified = artist_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    assert len(artist_unverified) == 1, "Should be in artist's unverified list"
    assert len(commissioner_unverified) == 1, "Should be in commissioner's unverified list"
    
    # Complete verification through art piece
    art_piece.verifyAsArtist(sender=artist)
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # Update verification status in profiles
    artist_profile.updateCommissionVerificationStatus(art_piece.address, sender=artist)
    commissioner_profile.updateCommissionVerificationStatus(art_piece.address, sender=commissioner)
    
    # Check final state - should be in verified lists and commissioner's art
    artist_verified = artist_profile.getCommissionsByOffset(0, 10, False)
    commissioner_verified = commissioner_profile.getCommissionsByOffset(0, 10, False)
    commissioner_art = commissioner_profile.getArtPiecesByOffset(0, 10, False)
    
    assert len(artist_verified) == 1, "Should be in artist's verified commission list"
    assert len(commissioner_verified) == 1, "Should be in commissioner's verified commission list"
    assert len(commissioner_art) == 1, "Should be in commissioner's art collection"

def test_verification_requires_commission_hub(setup):
    """Test that verification requires a commission hub to be attached"""
    deployer = setup["deployer"]
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    art_commission_hub_owners = setup["art_commission_hub_owners"]
    profile_factory = setup["profile_factory"]
    
    # Create art piece WITHOUT commission hub attached
    art_piece = project.ArtPiece.deploy(sender=deployer)
    art_piece.initialize(
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        commissioner.address,
        artist.address,
        ZERO_ADDRESS,  # No commission hub attached
        TEST_AI_GENERATED,
        artist.address,  # original uploader
        profile_factory.address,
        sender=deployer
    )
    
    # Approve the art piece
    art_commission_hub_owners.setApprovedArtPiece(art_piece.address, True, sender=deployer)
    
    # Verification should fail without a commission hub
    with pytest.raises(Exception) as excinfo:
        art_piece.verifyAsArtist(sender=artist)
    
    error_msg = str(excinfo.value).lower()
    assert "artcommissionhub" in error_msg or "hub" in error_msg, f"Error should mention commission hub requirement: {excinfo.value}"
    
    # Same for commissioner verification
    with pytest.raises(Exception) as excinfo:
        art_piece.verifyAsCommissioner(sender=commissioner)
    
    error_msg = str(excinfo.value).lower()
    assert "artcommissionhub" in error_msg or "hub" in error_msg, f"Error should mention commission hub requirement: {excinfo.value}"
    
    # Art piece should remain unverified
    assert not art_piece.artistVerified(), "Artist should not be verified"
    assert not art_piece.commissionerVerified(), "Commissioner should not be verified"
    assert not art_piece.isFullyVerifiedCommission(), "Should not be fully verified" 