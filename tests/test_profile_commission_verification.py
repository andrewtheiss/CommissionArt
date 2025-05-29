import pytest
from ape import accounts, project
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

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with all templates
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
    
    # Create a commission hub for testing
    art_commission_hub_owners.createGenericCommissionHub(hub_owner.address, sender=deployer)
    
    # Get the hub address
    hubs_list = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(hub_owner.address, 0, 1, False)
    hub_address = hubs_list[0]
    commission_hub = project.ArtCommissionHub.at(hub_address)
    
    # Create a commission art piece
    art_piece_tx = artist_profile.createArtPiece(
        art_piece_template.address,
        TEST_TOKEN_URI_DATA,
        TEST_TOKEN_URI_DATA_FORMAT,
        TEST_TITLE,
        TEST_DESCRIPTION,
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        commission_hub.address,  # art_commission_hub
        False,  # is_profile_art
        sender=artist
    )
    
    # Get the art piece address from the artist's recent art pieces
    art_pieces = artist_profile.getArtPiecesByOffset(0, 1, True)
    art_piece_address = art_pieces[0]
    art_piece = project.ArtPiece.at(art_piece_address)
    
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
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template,
        "art_piece": art_piece,
        "art_piece_template": art_piece_template
    }

def test_update_commission_verification_status_permissions(setup):
    """Test that only authorized users can call updateCommissionVerificationStatus"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    hub_owner = setup["hub_owner"]
    deployer = setup["deployer"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Add commission to commissioner's profile first so they have permission
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Act & Assert - Profile owner can call
    artist_profile.updateCommissionVerificationStatus(art_piece.address, sender=artist)
    
    # Act & Assert - Commissioner can call
    commissioner_profile.updateCommissionVerificationStatus(art_piece.address, sender=commissioner)
    
    # Act & Assert - Hub owner can call
    artist_profile.updateCommissionVerificationStatus(art_piece.address, sender=hub_owner)
    
    # Act & Assert - Unauthorized user cannot call
    with pytest.raises(Exception) as excinfo:
        artist_profile.updateCommissionVerificationStatus(art_piece.address, sender=deployer)
    assert "No permission" in str(excinfo.value)

def test_update_commission_verification_status_moves_commission(setup):
    """Test that updateCommissionVerificationStatus moves commission from unverified to verified"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Note: Artist side is already verified when creating the commission
    assert art_piece.artistVerified(), "Artist should be verified after creation"
    assert not art_piece.commissionerVerified(), "Commissioner should not be verified yet"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Verify it's in the unverified list for artist
    unverified_commissions = artist_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    assert art_piece.address in unverified_commissions, "Should be in artist's unverified list"
    
    # Add to commissioner's profile
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Verify it's in the unverified list for commissioner
    unverified_commissions = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    assert art_piece.address in unverified_commissions, "Should be in commissioner's unverified list"
    
    # Act - Verify as commissioner (artist is already verified)
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # Verify the commission is now verified
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be verified"
    
    # Act - Update verification status in both profiles
    artist_profile.updateCommissionVerificationStatus(art_piece.address, sender=artist)
    commissioner_profile.updateCommissionVerificationStatus(art_piece.address, sender=commissioner)
    
    # Assert - Should be moved to verified list in artist profile
    verified_commissions = artist_profile.getCommissionsByOffset(0, 10, False)
    assert art_piece.address in verified_commissions, "Should be in artist's verified list"
    
    # Assert - Should be removed from unverified list in artist profile
    unverified_commissions = artist_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    assert art_piece.address not in unverified_commissions, "Should not be in artist's unverified list"
    
    # Assert - Should be moved to verified list in commissioner profile
    verified_commissions = commissioner_profile.getCommissionsByOffset(0, 10, False)
    assert art_piece.address in verified_commissions, "Should be in commissioner's verified list"
    
    # Assert - Should be removed from unverified list in commissioner profile
    unverified_commissions = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    assert art_piece.address not in unverified_commissions, "Should not be in commissioner's unverified list"
    
    # Assert - Should be in commissioner's myArt collection
    my_art = commissioner_profile.getArtPiecesByOffset(0, 10, False)
    assert art_piece.address in my_art, "Should be in commissioner's myArt collection"

def test_update_commission_verification_status_updates_role(setup):
    """Test that updateCommissionVerificationStatus updates the commission role mapping"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Add to commissioner's profile first
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Verify as commissioner (artist is already verified from creation)
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # Act - Update verification status
    artist_profile.updateCommissionVerificationStatus(art_piece.address, sender=artist)
    commissioner_profile.updateCommissionVerificationStatus(art_piece.address, sender=commissioner)
    
    # Assert - Check commission role is set correctly for artist
    assert artist_profile.myCommissionRole(art_piece.address), "Artist profile should have artist role (true)"
    
    # Assert - Check commission role is set correctly for commissioner
    assert not commissioner_profile.myCommissionRole(art_piece.address), "Commissioner profile should have commissioner role (false)"

def test_update_commission_verification_status_non_involved_party(setup):
    """Test that updateCommissionVerificationStatus fails for non-involved parties"""
    # Arrange
    deployer = setup["deployer"]
    profile_factory = setup["profile_factory"]
    art_piece = setup["art_piece"]
    
    # Create a new profile for a non-involved party
    profile_factory.createProfile(deployer.address, sender=deployer)
    non_involved_profile_address = profile_factory.getProfile(deployer.address)
    non_involved_profile = project.Profile.at(non_involved_profile_address)
    
    # Act & Assert - Non-involved profile owner cannot update
    with pytest.raises(Exception) as excinfo:
        non_involved_profile.updateCommissionVerificationStatus(art_piece.address, sender=deployer)
    assert "not involved" in str(excinfo.value)

def test_cross_profile_verification_sync(setup):
    """Test that verification status is properly synchronized across profiles"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Add to commissioner's profile
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Initial state - both profiles should have the commission in unverified list
    # Note: Artist is already verified from creation
    artist_unverified = artist_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    assert art_piece.address in artist_unverified, "Should be in artist's unverified list"
    assert art_piece.address in commissioner_unverified, "Should be in commissioner's unverified list"
    
    # Verify initial verification status
    assert art_piece.artistVerified(), "Artist should already be verified from creation"
    assert not art_piece.commissionerVerified(), "Commissioner should not be verified yet"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Act - Commissioner verifies through profile
    commissioner_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=commissioner)
    
    # Assert - Commission should now be verified overall
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Assert - Both profiles should have the commission in verified lists
    artist_verified = artist_profile.getCommissionsByOffset(0, 10, False)
    commissioner_verified = commissioner_profile.getCommissionsByOffset(0, 10, False)
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Assert - Both profiles should not have the commission in unverified lists
    artist_unverified = artist_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    assert art_piece.address not in artist_unverified, "Should not be in artist's unverified list"
    assert art_piece.address not in commissioner_unverified, "Should not be in commissioner's unverified list" 