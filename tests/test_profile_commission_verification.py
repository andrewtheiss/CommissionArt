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
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)

    # Deploy ProfileSocial template
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    # Deploy ProfileFactoryAndRegistry with both templates
    profile_factory = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        sender=deployer
    )
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Set the template in the factory
    profile_factory.updateProfileTemplateContract(project.Profile.deploy(sender=deployer), sender=deployer)
    
    # Create profiles for artist and commissioner
    profile_factory.createProfile(sender=artist)
    profile_factory.createProfile(sender=commissioner)
    
    # Get the created profiles
    artist_profile = profile_factory.getProfile(artist.address)
    commissioner_profile = profile_factory.getProfile(commissioner.address)
    
    # Deploy ArtCommissionHub
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Initialize the hub with hub_owner
    chain_id = 1
    nft_contract = deployer.address
    token_id = 1
    commission_hub.initialize(chain_id, nft_contract, token_id, hub_owner.address, sender=deployer)
    
    # Create a commission art piece
    artist_profile_contract = project.Profile(artist_profile)
    
    # Set artist flag
    artist_profile_contract.setIsArtist(True, sender=artist)
    
    # Create art piece as a commission
    art_piece_address = artist_profile_contract.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        commission_hub.address,  # art_commission_hub
        False,  # is_profile_art
        sender=artist
    )
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "hub_owner": hub_owner,
        "profile_factory": profile_factory,
        "artist_profile": artist_profile_contract,
        "commissioner_profile": project.Profile(commissioner_profile),
        "commission_hub": commission_hub,
        "art_piece": project.ArtPiece(art_piece_address)
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
    
    # Verify the commission should start as unverified
    assert not art_piece.isFullyVerifiedCommission(), "Commission should start unverified"
    
    # Verify it's in the unverified list for artist
    unverified_commissions = artist_profile.getUnverifiedCommissions(0, 10)
    assert art_piece.address in unverified_commissions, "Should be in artist's unverified list"
    
    # Add to commissioner's profile
    commissioner_profile.addCommission(art_piece.address, sender=commissioner)
    
    # Verify it's in the unverified list for commissioner
    unverified_commissions = commissioner_profile.getUnverifiedCommissions(0, 10)
    assert art_piece.address in unverified_commissions, "Should be in commissioner's unverified list"
    
    # Act - Verify as commissioner
    art_piece.verifyAsCommissioner(sender=commissioner)
    
    # Act - Verify as artist
    art_piece.verifyAsArtist(sender=artist)
    
    # Verify the commission is now verified
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be verified"
    
    # Act - Update verification status in both profiles
    artist_profile.updateCommissionVerificationStatus(art_piece.address, sender=artist)
    commissioner_profile.updateCommissionVerificationStatus(art_piece.address, sender=commissioner)
    
    # Assert - Should be moved to verified list in artist profile
    verified_commissions = artist_profile.getCommissions(0, 10)
    assert art_piece.address in verified_commissions, "Should be in artist's verified list"
    
    # Assert - Should be removed from unverified list in artist profile
    unverified_commissions = artist_profile.getUnverifiedCommissions(0, 10)
    assert art_piece.address not in unverified_commissions, "Should not be in artist's unverified list"
    
    # Assert - Should be moved to verified list in commissioner profile
    verified_commissions = commissioner_profile.getCommissions(0, 10)
    assert art_piece.address in verified_commissions, "Should be in commissioner's verified list"
    
    # Assert - Should be removed from unverified list in commissioner profile
    unverified_commissions = commissioner_profile.getUnverifiedCommissions(0, 10)
    assert art_piece.address not in unverified_commissions, "Should not be in commissioner's unverified list"
    
    # Assert - Should be in commissioner's myArt collection
    my_art = commissioner_profile.getArtPieces(0, 10)
    assert art_piece.address in my_art, "Should be in commissioner's myArt collection"

def test_update_commission_verification_status_updates_role(setup):
    """Test that updateCommissionVerificationStatus updates the commission role mapping"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Verify as both parties to make it fully verified
    art_piece.verifyAsCommissioner(sender=commissioner)
    art_piece.verifyAsArtist(sender=artist)
    
    # Act - Update verification status
    artist_profile.updateCommissionVerificationStatus(art_piece.address, sender=artist)
    commissioner_profile.updateCommissionVerificationStatus(art_piece.address, sender=commissioner)
    
    # Assert - Check commission role is set correctly for artist
    assert artist_profile.commissionRole(art_piece.address), "Artist profile should have artist role (true)"
    
    # Assert - Check commission role is set correctly for commissioner
    assert not commissioner_profile.commissionRole(art_piece.address), "Commissioner profile should have commissioner role (false)"

def test_update_commission_verification_status_non_involved_party(setup):
    """Test that updateCommissionVerificationStatus fails for non-involved parties"""
    # Arrange
    deployer = setup["deployer"]
    artist_profile = setup["artist_profile"]
    art_piece = setup["art_piece"]
    
    # Create a new profile for a non-involved party
    profile_factory = setup["profile_factory"]
    profile_factory.createProfile(sender=deployer)
    non_involved_profile = project.Profile(profile_factory.getProfile(deployer.address))
    
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
    commissioner_profile.addCommission(art_piece.address, sender=commissioner)
    
    # Initial state - both profiles should have the commission in unverified list
    artist_unverified = artist_profile.getUnverifiedCommissions(0, 10)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissions(0, 10)
    assert art_piece.address in artist_unverified, "Should be in artist's unverified list"
    assert art_piece.address in commissioner_unverified, "Should be in commissioner's unverified list"
    
    # Act - Commissioner verifies through profile
    commissioner_profile.verifyCommission(art_piece.address, sender=commissioner)
    
    # Assert - Commission should still be unverified overall
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Act - Artist verifies through profile
    artist_profile.verifyCommission(art_piece.address, sender=artist)
    
    # Assert - Commission should now be verified overall
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Assert - Both profiles should have the commission in verified lists
    artist_verified = artist_profile.getCommissions(0, 10)
    commissioner_verified = commissioner_profile.getCommissions(0, 10)
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Assert - Both profiles should not have the commission in unverified lists
    artist_unverified = artist_profile.getUnverifiedCommissions(0, 10)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissions(0, 10)
    assert art_piece.address not in artist_unverified, "Should not be in artist's unverified list"
    assert art_piece.address not in commissioner_unverified, "Should not be in commissioner's unverified list" 