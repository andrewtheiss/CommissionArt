import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    
    # Deploy templates
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with all required templates
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
    
    # Get the created profiles
    artist_profile_address = profile_factory.getProfile(artist.address)
    commissioner_profile_address = profile_factory.getProfile(commissioner.address)
    
    artist_profile_contract = project.Profile.at(artist_profile_address)
    commissioner_profile_contract = project.Profile.at(commissioner_profile_address)
    
    # Set artist flag
    artist_profile_contract.setIsArtist(True, sender=artist)
    
    # Enable unverified commissions for both profiles
    artist_profile_contract.setAllowUnverifiedCommissions(True, sender=artist)
    commissioner_profile_contract.setAllowUnverifiedCommissions(True, sender=commissioner)
    
    # Set up mutual whitelisting so profiles can update each other's verification status
    artist_profile_contract.addToWhitelist(commissioner.address, sender=artist)
    commissioner_profile_contract.addToWhitelist(artist.address, sender=commissioner)
    
    # Create generic commission hub for commissioner
    art_commission_hub_owners.createGenericCommissionHub(commissioner.address, sender=deployer)
    commissioner_hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(commissioner.address, 0, 1, False)
    commissioner_hub_address = commissioner_hubs[0]
    
    # Create a commission art piece attached to the commissioner's hub
    # Use call() to get the return value instead of the transaction receipt
    art_piece_address = artist_profile_contract.createArtPiece.call(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        commissioner_hub_address,  # Attach to commissioner's hub
        False,  # is_profile_art
        sender=artist
    )
    
    # Now actually execute the transaction
    artist_profile_contract.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        commissioner_hub_address,  # Attach to commissioner's hub
        False,  # is_profile_art
        sender=artist
    )
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "profile_factory": profile_factory,
        "art_commission_hub_owners": art_commission_hub_owners,
        "artist_profile": artist_profile_contract,
        "commissioner_profile": commissioner_profile_contract,
        "art_piece": project.ArtPiece.at(art_piece_address),
        "commissioner_hub": project.ArtCommissionHub.at(commissioner_hub_address)
    }

def test_verify_commission_updates_both_profiles(setup):
    """Test that verifyArtLinkedToMyCommission updates both artist and commissioner profiles"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # The art piece should already be in the artist's unverified list from creation
    # But we need to explicitly add it to the commissioner's profile since the automatic linking
    # during creation might not have worked due to whitelisting/permission issues
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Verify the commission is in unverified lists for both profiles
    artist_unverified = artist_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    
    assert art_piece.address in artist_unverified, "Should be in artist's unverified list"
    assert art_piece.address in commissioner_unverified, "Should be in commissioner's unverified list"
    
    # Verify initial verification status
    assert not art_piece.artistVerified(), "Artist should not be verified initially"
    assert not art_piece.commissionerVerified(), "Commissioner should not be verified initially"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified initially"
    
    # Act - Commissioner verifies the commission
    commissioner_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=commissioner)
    
    # Assert - Commissioner should be verified but not fully verified yet
    assert not art_piece.artistVerified(), "Artist should still not be verified"
    assert art_piece.commissionerVerified(), "Commissioner should now be verified"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Act - Artist verifies the commission
    artist_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=artist)
    
    # Assert - Should now be fully verified
    assert art_piece.artistVerified(), "Artist should now be verified"
    assert art_piece.commissionerVerified(), "Commissioner should still be verified"
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Assert - Should be moved to verified list in both profiles
    artist_verified = artist_profile.getCommissionsByOffset(0, 10, False)
    commissioner_verified = commissioner_profile.getCommissionsByOffset(0, 10, False)
    
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Assert - Should be removed from unverified list in both profiles
    artist_unverified = artist_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissionsByOffset(0, 10, False)
    
    assert art_piece.address not in artist_unverified, "Should not be in artist's unverified list"
    assert art_piece.address not in commissioner_unverified, "Should not be in commissioner's unverified list"

def test_verify_commission_updates_commission_role(setup):
    """Test that verifyArtLinkedToMyCommission correctly records the commission role"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Manually add the commission to the commissioner's profile
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Act - Both parties verify the commission
    commissioner_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=commissioner)
    artist_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=artist)
    
    # Assert - Check commission role is set correctly for artist
    assert artist_profile.myCommissionRole(art_piece.address), "Artist profile should have artist role (true)"
    
    # Assert - Check commission role is set correctly for commissioner
    assert not commissioner_profile.myCommissionRole(art_piece.address), "Commissioner profile should have commissioner role (false)"

def test_verify_commission_cross_profile_update(setup):
    """Test that verifyArtLinkedToMyCommission updates the other party's profile through ProfileFactoryAndRegistry"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Manually add the commission to the commissioner's profile
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Act - Both parties verify the commission
    artist_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=artist)
    commissioner_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=commissioner)
    
    # Assert - Should be in verified list for both profiles
    artist_verified = artist_profile.getCommissionsByOffset(0, 10, False)
    commissioner_verified = commissioner_profile.getCommissionsByOffset(0, 10, False)
    
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Assert - Should be in commissioner's myArt collection
    commissioner_art = commissioner_profile.getArtPiecesByOffset(0, 10, False)
    assert art_piece.address in commissioner_art, "Should be in commissioner's myArt collection"

def test_verify_commission_already_verified(setup):
    """Test that verifyArtLinkedToMyCommission handles already verified commissions correctly"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Manually add the commission to the commissioner's profile
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Both parties verify the commission
    commissioner_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=commissioner)
    artist_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=artist)
    
    # Act & Assert - Try to verify again as artist
    with pytest.raises(Exception) as excinfo:
        artist_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=artist)
    assert "Unverified" in str(excinfo.value) and "not found" in str(excinfo.value)
    
    # Act & Assert - Try to verify again as commissioner
    with pytest.raises(Exception) as excinfo:
        commissioner_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=commissioner)
    assert "Unverified" in str(excinfo.value) and "not found" in str(excinfo.value)

def test_verify_commission_different_order(setup):
    """Test that verifyArtLinkedToMyCommission works regardless of verification order"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # Manually add the commission to the commissioner's profile
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Act - Artist verifies first this time
    artist_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=artist)
    
    # Assert - Should not be fully verified yet
    assert art_piece.artistVerified(), "Artist should be verified"
    assert not art_piece.commissionerVerified(), "Commissioner should not be verified yet"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Act - Commissioner verifies second
    commissioner_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=commissioner)
    
    # Assert - Should now be fully verified
    assert art_piece.artistVerified(), "Artist should still be verified"
    assert art_piece.commissionerVerified(), "Commissioner should now be verified"
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Assert - Should be in verified list for both profiles
    artist_verified = artist_profile.getCommissionsByOffset(0, 10, False)
    commissioner_verified = commissioner_profile.getCommissionsByOffset(0, 10, False)
    
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list"

def test_verify_commission_requires_hub_attachment(setup):
    """Test that verification requires the art piece to be attached to a commission hub"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    art_piece_template = project.ArtPiece.deploy(sender=setup["deployer"])
    
    # Create an art piece WITHOUT attaching to a hub
    art_piece_address = artist_profile.createArtPiece.call(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission No Hub",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        ZERO_ADDRESS,  # No hub attachment
        False,  # is_profile_art
        sender=artist
    )
    
    # Execute the transaction
    artist_profile.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission No Hub",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        ZERO_ADDRESS,  # No hub attachment
        False,  # is_profile_art
        sender=artist
    )
    
    art_piece_no_hub = project.ArtPiece.at(art_piece_address)
    
    # Verify the art piece was created but has no hub
    assert art_piece_no_hub.getArtCommissionHubAddress() == ZERO_ADDRESS, "Art piece should not have a hub"
    
    # Act & Assert - Try to verify directly on the art piece without hub attachment should fail
    with pytest.raises(Exception) as excinfo:
        art_piece_no_hub.verifyAsArtist(sender=artist)
    assert "ArtPiece must be attached to a ArtCommissionHub" in str(excinfo.value)

def test_verify_commission_only_profile_owner_can_verify(setup):
    """Test that only the profile owner can call verifyArtLinkedToMyCommission"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    random_user = accounts.test_accounts[3]
    
    # Manually add the commission to the commissioner's profile
    commissioner_profile.linkArtPieceAsMyCommission(art_piece.address, sender=commissioner)
    
    # Act & Assert - Try to verify as random user should fail
    with pytest.raises(Exception) as excinfo:
        artist_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=random_user)
    assert "Only profile owner can verify" in str(excinfo.value)
    
    # Act & Assert - Try to verify commissioner's profile as artist should fail
    with pytest.raises(Exception) as excinfo:
        commissioner_profile.verifyArtLinkedToMyCommission(art_piece.address, sender=artist)
    assert "Only profile owner can verify" in str(excinfo.value) 