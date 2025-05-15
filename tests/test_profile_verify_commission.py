import pytest
from ape import accounts, project
from ape.utils import ZERO_ADDRESS

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    
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
    
    # Set artist flag
    artist_profile_contract = project.Profile(artist_profile)
    artist_profile_contract.setIsArtist(True, sender=artist)
    
    # Create a commission art piece
    art_piece_address = artist_profile_contract.createArtPiece(
        art_piece_template.address,
        b"test_data",
        "avif",
        "Test Commission",
        "Test Description",
        True,  # is_artist
        commissioner.address,  # other_party (commissioner)
        False,  # ai_generated
        ZERO_ADDRESS,  # No commission hub
        False,  # is_profile_art
        sender=artist
    )
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "profile_factory": profile_factory,
        "artist_profile": artist_profile_contract,
        "commissioner_profile": project.Profile(commissioner_profile),
        "art_piece": project.ArtPiece(art_piece_address)
    }

def test_verify_commission_updates_both_profiles(setup):
    """Test that verifyCommission updates both artist and commissioner profiles"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # First add the commission to the commissioner's profile
    commissioner_profile.addCommission(art_piece.address, sender=commissioner)
    
    # Verify the commission is in unverified lists for both profiles
    artist_unverified = artist_profile.getUnverifiedCommissions(0, 10)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissions(0, 10)
    
    assert art_piece.address in artist_unverified, "Should be in artist's unverified list"
    assert art_piece.address in commissioner_unverified, "Should be in commissioner's unverified list"
    
    # Act - Commissioner verifies the commission
    commissioner_profile.verifyCommission(art_piece.address, sender=commissioner)
    
    # Assert - Should still be unverified since only one party verified
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Act - Artist verifies the commission
    artist_profile.verifyCommission(art_piece.address, sender=artist)
    
    # Assert - Should now be fully verified
    assert art_piece.isFullyVerifiedCommission(), "Commission should now be fully verified"
    
    # Assert - Should be moved to verified list in both profiles
    artist_verified = artist_profile.getCommissions(0, 10)
    commissioner_verified = commissioner_profile.getCommissions(0, 10)
    
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Assert - Should be removed from unverified list in both profiles
    artist_unverified = artist_profile.getUnverifiedCommissions(0, 10)
    commissioner_unverified = commissioner_profile.getUnverifiedCommissions(0, 10)
    
    assert art_piece.address not in artist_unverified, "Should not be in artist's unverified list"
    assert art_piece.address not in commissioner_unverified, "Should not be in commissioner's unverified list"

def test_verify_commission_adds_to_commissioner_my_art(setup):
    """Test that verifyCommission adds the commission to the commissioner's myArt collection"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # First add the commission to the commissioner's profile
    commissioner_profile.addCommission(art_piece.address, sender=commissioner)
    
    # Check commissioner's myArt collection before verification
    commissioner_art_before = commissioner_profile.getArtPieces(0, 10)
    assert art_piece.address not in commissioner_art_before, "Should not be in commissioner's myArt collection yet"
    
    # Act - Both parties verify the commission
    commissioner_profile.verifyCommission(art_piece.address, sender=commissioner)
    artist_profile.verifyCommission(art_piece.address, sender=artist)
    
    # Assert - Should be added to commissioner's myArt collection
    commissioner_art_after = commissioner_profile.getArtPieces(0, 10)
    assert art_piece.address in commissioner_art_after, "Should be in commissioner's myArt collection after verification"

def test_verify_commission_updates_commission_role(setup):
    """Test that verifyCommission correctly records the commission role"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # First add the commission to both profiles
    commissioner_profile.addCommission(art_piece.address, sender=commissioner)
    
    # Act - Both parties verify the commission
    commissioner_profile.verifyCommission(art_piece.address, sender=commissioner)
    artist_profile.verifyCommission(art_piece.address, sender=artist)
    
    # Assert - Check commission role is set correctly for artist
    assert artist_profile.commissionRole(art_piece.address), "Artist profile should have artist role (true)"
    
    # Assert - Check commission role is set correctly for commissioner
    assert not commissioner_profile.commissionRole(art_piece.address), "Commissioner profile should have commissioner role (false)"

def test_verify_commission_cross_profile_update(setup):
    """Test that verifyCommission updates the other party's profile through ProfileFactoryAndRegistry"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # First add the commission to the artist's profile only
    # The commissioner's profile should be updated automatically when verified
    
    # Act - Both parties verify the commission
    artist_profile.verifyCommission(art_piece.address, sender=artist)
    commissioner_profile.verifyCommission(art_piece.address, sender=commissioner)
    
    # Assert - Should be in verified list for both profiles
    artist_verified = artist_profile.getCommissions(0, 10)
    commissioner_verified = commissioner_profile.getCommissions(0, 10)
    
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list"
    
    # Assert - Should be in commissioner's myArt collection
    commissioner_art = commissioner_profile.getArtPieces(0, 10)
    assert art_piece.address in commissioner_art, "Should be in commissioner's myArt collection"

def test_verify_commission_already_verified(setup):
    """Test that verifyCommission handles already verified commissions correctly"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece = setup["art_piece"]
    
    # First add the commission to both profiles
    commissioner_profile.addCommission(art_piece.address, sender=commissioner)
    
    # Both parties verify the commission
    commissioner_profile.verifyCommission(art_piece.address, sender=commissioner)
    artist_profile.verifyCommission(art_piece.address, sender=artist)
    
    # Act & Assert - Try to verify again as artist
    with pytest.raises(Exception) as excinfo:
        artist_profile.verifyCommission(art_piece.address, sender=artist)
    assert "Already verified by artist" in str(excinfo.value)
    
    # Act & Assert - Try to verify again as commissioner
    with pytest.raises(Exception) as excinfo:
        commissioner_profile.verifyCommission(art_piece.address, sender=commissioner)
    assert "Already verified by commissioner" in str(excinfo.value)

def test_verify_commission_different_order(setup):
    """Test that verification works regardless of which party verifies first"""
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    artist_profile = setup["artist_profile"]
    commissioner_profile = setup["commissioner_profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Create a new commission piece with commissioner as uploader
    art_piece = project.ArtPiece.deploy(sender=setup["deployer"])
    art_piece.initialize(
        b"test_data",
        "avif",
        "Commissioner First",
        "Test Description",
        commissioner.address,  # commissioner_input
        artist.address,  # artist_input
        ZERO_ADDRESS,  # No commission hub
        False,  # ai_generated
        sender=setup["deployer"]
    )
    
    # Add to both profiles
    artist_profile.addCommission(art_piece.address, sender=artist)
    commissioner_profile.addCommission(art_piece.address, sender=commissioner)
    
    # Verify initial state
    assert art_piece.commissionerVerified(), "Commissioner side should be verified initially"
    assert not art_piece.artistVerified(), "Artist side should not be verified initially"
    assert not art_piece.isFullyVerifiedCommission(), "Commission should not be fully verified yet"
    
    # Act - Artist verifies first (even though commissioner is already verified implicitly)
    artist_profile.verifyCommission(art_piece.address, sender=artist)
    
    # Assert - Should now be fully verified
    assert art_piece.isFullyVerifiedCommission(), "Commission should be fully verified"
    
    # Assert - Should be in verified lists for both profiles
    artist_verified = artist_profile.getCommissions(0, 10)
    commissioner_verified = commissioner_profile.getCommissions(0, 10)
    assert art_piece.address in artist_verified, "Should be in artist's verified list"
    assert art_piece.address in commissioner_verified, "Should be in commissioner's verified list" 