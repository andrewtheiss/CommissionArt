import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    other_user = accounts.test_accounts[3]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Create profiles for testing
    profile_hub.createProfile(sender=owner)
    profile_hub.createProfile(sender=artist)
    
    owner_profile_address = profile_hub.getProfile(owner.address)
    artist_profile_address = profile_hub.getProfile(artist.address)
    
    owner_profile = project.Profile.at(owner_profile_address)
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Set artist status for artist profile
    artist_profile.setIsArtist(True, sender=artist)
    
    # Deploy ArtPiece template for art piece tests
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    return {
        "deployer": deployer,
        "owner": owner,
        "artist": artist,
        "other_user": other_user,
        "profile_template": profile_template,
        "profile_hub": profile_hub,
        "owner_profile": owner_profile,
        "artist_profile": artist_profile,
        "art_piece_template": art_piece_template
    }

def test_initialization(setup):
    """Test initialization and initial state"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    deployer = setup["deployer"]
    profile_hub = setup["profile_hub"]
    
    # Check owner profile initial state
    assert owner_profile.owner() == owner.address
    
    # The deployer field is now set to the ProfileHub address during initialization,
    # not the original deployer of the Profile template
    assert owner_profile.deployer() == profile_hub.address
    
    assert owner_profile.isArtist() is False
    assert owner_profile.allowUnverifiedCommissions() is True
    assert owner_profile.profileExpansion() == "0x" + "0" * 40
    assert owner_profile.artistProceedsAddress() == owner.address
    
    # Check all counts are initialized to zero
    assert owner_profile.commissionCount() == 0
    assert owner_profile.unverifiedCommissionCount() == 0
    assert owner_profile.likedProfileCount() == 0
    assert owner_profile.linkedProfileCount() == 0
    assert owner_profile.artistCommissionedWorkCount() == 0
    assert owner_profile.artistErc1155sToSellCount() == 0
    assert owner_profile.myArtCount() == 0
    
    # Check artist profile
    assert artist_profile.owner() == artist.address
    assert artist_profile.isArtist() is True
    assert artist_profile.artistProceedsAddress() == artist.address

def test_set_is_artist(setup):
    """Test setting artist status"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    other_user = setup["other_user"]
    
    # Initial state
    assert owner_profile.isArtist() is False
    
    # Set to true
    owner_profile.setIsArtist(True, sender=owner)
    assert owner_profile.isArtist() is True
    
    # Set to false
    owner_profile.setIsArtist(False, sender=owner)
    assert owner_profile.isArtist() is False
    
    # Attempt by non-owner should fail
    with pytest.raises(Exception):
        owner_profile.setIsArtist(True, sender=other_user)

def test_profile_image_methods(setup):
    """Test profile image methods"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    other_user = setup["other_user"]
    
    # Test initial state
    assert len(owner_profile.profileImage()) == 0
    
    # Test setting profile image
    image1 = "data:application/json;base64,eyJuY41lIjoiVGVzdCBDb21taXNzaW9uIiwiZGVzY3JpcHRpb24iOiJUZXN0IGNvbW1pc3Npb24gZGVzY3JpcHRpb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    owner_profile.setProfileImage(image1, sender=owner)
    assert owner_profile.profileImage() == image1
    
    # Set second image to trigger history storage
    image2 = "data:application/json;base64,eyJuYW1lIjoiVGVzdCBDb21taXNzaW9uIiwiZGVzY3tpcHRpb24iOiJUZXN0IGNvbW1pc3Npb24gZGVzY3JpcHRpb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    owner_profile.setProfileImage(image2, sender=owner)
    assert owner_profile.profileImage() == image2
    
    # Set third image
    image3 = "data:application/json;base64,eyJuYW1lIjoiVGVzdCBDb21taXNzaW9uIiwiZGVzY3JpcHRpb24iOiJUZXN0IGNvbW1pc3Npb24gRGVzY3JpcHRpb24iLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    owner_profile.setProfileImage(image3, sender=owner)
    assert owner_profile.profileImage() == image3
    
    # Attempt by non-owner should fail
    with pytest.raises(Exception):
        owner_profile.setProfileImage(b"unauthorized image", sender=other_user)

def test_set_allow_unverified_commissions(setup):
    """Test setting allow unverified commissions flag"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    other_user = setup["other_user"]
    
    # Initial state
    assert owner_profile.allowUnverifiedCommissions() is True
    
    # Set to false
    owner_profile.setAllowUnverifiedCommissions(False, sender=owner)
    assert owner_profile.allowUnverifiedCommissions() is False
    
    # Set to true again
    owner_profile.setAllowUnverifiedCommissions(True, sender=owner)
    assert owner_profile.allowUnverifiedCommissions() is True
    
    # Attempt by non-owner should fail
    with pytest.raises(Exception):
        owner_profile.setAllowUnverifiedCommissions(False, sender=other_user)

def test_set_profile_expansion(setup):
    """Test setting profile expansion address"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    other_user = setup["other_user"]
    
    # Initial state
    assert owner_profile.profileExpansion() == "0x" + "0" * 40
    
    # Set expansion address
    expansion_address = "0x" + "1" * 40
    owner_profile.setProfileExpansion(expansion_address, sender=owner)
    assert owner_profile.profileExpansion() == expansion_address
    
    # Change expansion address
    new_expansion = "0x" + "2" * 40
    owner_profile.setProfileExpansion(new_expansion, sender=owner)
    assert owner_profile.profileExpansion() == new_expansion
    
    # Attempt by non-owner should fail
    with pytest.raises(Exception):
        owner_profile.setProfileExpansion("0x" + "3" * 40, sender=other_user)

def test_set_proceeds_address(setup):
    """Test setting proceeds address (artist-only)"""
    artist = setup["artist"]
    artist_profile = setup["artist_profile"]
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    other_user = setup["other_user"]
    
    # Initial state
    assert artist_profile.artistProceedsAddress() == artist.address
    
    # Set proceeds address 
    proceeds_address = "0x" + "a" * 40
    artist_profile.setProceedsAddress(proceeds_address, sender=artist)
    
    # Compare lowercase versions of addresses to avoid case-sensitivity issues
    stored_address = artist_profile.artistProceedsAddress().lower()
    expected_address = proceeds_address.lower()
    assert stored_address == expected_address
    
    # Non-artist profile should fail
    with pytest.raises(Exception):
        owner_profile.setProceedsAddress(proceeds_address, sender=owner)
    
    # Set owner as artist to test
    owner_profile.setIsArtist(True, sender=owner)
    
    # Now should work
    owner_profile.setProceedsAddress(proceeds_address, sender=owner)
    assert owner_profile.artistProceedsAddress().lower() == proceeds_address.lower()
    
    # Attempt by non-owner should fail
    with pytest.raises(Exception):
        artist_profile.setProceedsAddress("0x" + "b" * 40, sender=other_user)

def test_whitelist_methods(setup):
    """Test whitelist management methods"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    other_user = setup["other_user"]
    artist = setup["artist"]
    
    # Initial state - should be false for any address
    test_address = "0x" + "f" * 40
    assert owner_profile.whitelist(test_address) is False
    assert owner_profile.whitelist(artist.address) is False
    
    # Add to whitelist
    owner_profile.addToWhitelist(test_address, sender=owner)
    assert owner_profile.whitelist(test_address) is True
    
    # Add another
    owner_profile.addToWhitelist(artist.address, sender=owner)
    assert owner_profile.whitelist(artist.address) is True
    
    # Remove from whitelist
    owner_profile.removeFromWhitelist(test_address, sender=owner)
    assert owner_profile.whitelist(test_address) is False
    assert owner_profile.whitelist(artist.address) is True
    
    # Attempt by non-owner should fail
    with pytest.raises(Exception):
        owner_profile.addToWhitelist(other_user.address, sender=other_user)
    
    with pytest.raises(Exception):
        owner_profile.removeFromWhitelist(artist.address, sender=other_user)

def test_blacklist_methods(setup):
    """Test blacklist management methods"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    other_user = setup["other_user"]
    artist = setup["artist"]
    
    # Initial state - should be false for any address
    test_address = "0x" + "d" * 40
    assert owner_profile.blacklist(test_address) is False
    assert owner_profile.blacklist(artist.address) is False
    
    # Add to blacklist
    owner_profile.addToBlacklist(test_address, sender=owner)
    assert owner_profile.blacklist(test_address) is True
    
    # Add another
    owner_profile.addToBlacklist(artist.address, sender=owner)
    assert owner_profile.blacklist(artist.address) is True
    
    # Remove from blacklist
    owner_profile.removeFromBlacklist(test_address, sender=owner)
    assert owner_profile.blacklist(test_address) is False
    assert owner_profile.blacklist(artist.address) is True
    
    # Attempt by non-owner should fail
    with pytest.raises(Exception):
        owner_profile.addToBlacklist(other_user.address, sender=other_user)
    
    with pytest.raises(Exception):
        owner_profile.removeFromBlacklist(artist.address, sender=other_user)

def test_create_art_piece(setup):
    """Test creating art pieces through profile"""
    owner = setup["owner"]
    owner_profile = setup["owner_profile"]
    artist = setup["artist"]
    art_piece_template = setup["art_piece_template"]
    
    # Test initial state
    assert owner_profile.myArtCount() == 0
    
    # Create an art piece as commissioner
    image_data = "data:application/json;base64,eyJuYW1lIjoiVGVzdCBBcnR3b3JrIiwiZGVzY3JpcHRpb24iOiJUaGlzIGlzIGEgdGVzdCBkZXNjcmlwdGlvbiBmb3IgdGhlIGFydHdvcmsiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "Test Art Piece"
    description = "Test description for art piece"
    
    # Simple test of creating art - full tests covered in test_profile_art_creation.py
    owner_profile.createArtPiece(
        art_piece_template.address,
        image_data,
        title,
        description,
        False,  # Not as artist
        artist.address,  # Artist address
        "0x" + "0" * 40,  # Commission hub
        False,  # Not AI generated
        sender=owner
    )
    
    # Verify count increased
    assert owner_profile.myArtCount() == 1
    
    # Get the art piece
    art_pieces = owner_profile.getArtPieces(0, 1)
    assert len(art_pieces) == 1
    
    art_piece = project.ArtPiece.at(art_pieces[0])
    assert art_piece.getTitle() == title
    assert art_piece.getOwner() == owner.address
    assert art_piece.getArtist() == artist.address 