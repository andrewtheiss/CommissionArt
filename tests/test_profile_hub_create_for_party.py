import pytest
from ape import accounts, project
import time
import base64
import json

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    artist = accounts.test_accounts[1]
    commissioner = accounts.test_accounts[2]
    new_user = accounts.test_accounts[3]
    blacklister = accounts.test_accounts[4]
    whitelister = accounts.test_accounts[5]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with the template
    profile_factory_and_regsitry = project.ProfileFactoryAndRegistry.deploy(profile_template.address, sender=deployer)
    
    # Deploy ArtPiece template for createArtPiece tests
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy ArtCommissionHub for art piece registration
    commission_hub = project.ArtCommissionHub.deploy(sender=deployer)
    
    # Create profiles for blacklister and whitelister for testing permissions
    profile_factory_and_regsitry.createProfile(sender=blacklister)
    profile_factory_and_regsitry.createProfile(sender=whitelister)
    
    blacklister_profile = project.Profile.at(profile_factory_and_regsitry.getProfile(blacklister.address))
    whitelister_profile = project.Profile.at(profile_factory_and_regsitry.getProfile(whitelister.address))
    
    return {
        "deployer": deployer,
        "artist": artist,
        "commissioner": commissioner,
        "new_user": new_user,
        "blacklister": blacklister,
        "whitelister": whitelister,
        "blacklister_profile": blacklister_profile,
        "whitelister_profile": whitelister_profile,
        "profile_template": profile_template,
        "profile_factory_and_regsitry": profile_factory_and_regsitry,
        "art_piece_template": art_piece_template,
        "commission_hub": commission_hub
    }

def test_artist_creates_art_for_new_commissioner(setup):
    """
    Test an artist creating art for a commissioner who doesn't have a profile yet.
    This should:
    1. Create a profile for the artist if they don't have one
    2. Create a profile for the commissioner
    3. Create the art piece
    4. Add the art to the commissioner's unverified commissions
    """
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    art_piece_template = setup["art_piece_template"]
    commission_hub = setup["commission_hub"]
    
    # Verify neither user has a profile yet
    assert profile_factory_and_regsitry.hasProfile(artist.address) == False
    assert profile_factory_and_regsitry.hasProfile(commissioner.address) == False
    
    # Sample art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQXJ0IENvbW1pc3Npb24iLCJkZXNjcmlwdGlvbiI6IkFydCBjcmVhdGVkIGZvciBjb21taXNzaW9uZXIiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "Commission Art"
    description = "Art created for commissioner"
    is_artist = True  # Artist is creating the art
    
    # Act - Create art piece for commissioner
    profile_factory_and_regsitry.createArtPieceForParty(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        commissioner.address,  # Commissioner is the other party
        commission_hub.address,
        False,  # Not AI generated
        sender=artist
    )
    
    # Assert - Verify profiles were created
    assert profile_factory_and_regsitry.hasProfile(artist.address) == True
    assert profile_factory_and_regsitry.hasProfile(commissioner.address) == True
    
    # Get profile addresses
    artist_profile_address = profile_factory_and_regsitry.getProfile(artist.address)
    commissioner_profile_address = profile_factory_and_regsitry.getProfile(commissioner.address)
    
    # Load the profile contracts
    artist_profile = project.Profile.at(artist_profile_address)
    commissioner_profile = project.Profile.at(commissioner_profile_address)
    
    # Verify the profile owners are set correctly
    assert artist_profile.owner() == artist.address
    assert commissioner_profile.owner() == commissioner.address
    
    # Verify art piece was created and added to artist's collection
    assert artist_profile.myArtCount() == 1
    
    # Get the art piece
    latest_art_pieces = artist_profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Verify art piece was added to commissioner's unverified commissions
    unverified_commissions = commissioner_profile.getUnverifiedCommissions(0, 10)
    assert len(unverified_commissions) == 1
    assert unverified_commissions[0] == art_piece_address
    
    # Load and verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == commissioner.address  # Commissioner owns the art
    assert art_piece.getArtist() == artist.address  # Artist created it
    assert art_piece.getTokenURIData() == token_uri_data
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description
    assert art_piece.getArtCommissionHubAddress() == commission_hub.address

def test_commissioner_creates_art_for_existing_artist(setup):
    """
    Test a commissioner creating art for an artist who already has a profile.
    This should:
    1. Create a profile for the commissioner if they don't have one
    2. Create the art piece
    3. Add the art to the artist's unverified commissions
    """
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    art_piece_template = setup["art_piece_template"]
    
    # Create a profile for the artist first
    profile_factory_and_regsitry.createProfile(sender=artist)
    assert profile_factory_and_regsitry.hasProfile(artist.address) == True
    
    # Verify commissioner doesn't have a profile yet
    assert profile_factory_and_regsitry.hasProfile(commissioner.address) == False
    
    # Sample art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQ29tbWlzc2lvbiBSZXF1ZXN0IiwiZGVzY3JpcHRpb24iOiJDb21taXNzaW9uZXIgcmVxdWVzdGluZyBhcnQiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "Commission Request"
    description = "Commissioner requesting art"
    is_artist = False  # Commissioner is not the artist
    
    # Act - Create art piece for artist
    result = profile_factory_and_regsitry.createArtPieceForParty(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        artist.address,  # Artist is the other party
        ZERO_ADDRESS,  # No commission hub
        False,  # Not AI generated
        sender=commissioner
    )
    
    # Assert - Verify commissioner profile was created
    assert profile_factory_and_regsitry.hasProfile(commissioner.address) == True
    
    # Get profile addresses
    artist_profile_address = profile_factory_and_regsitry.getProfile(artist.address)
    commissioner_profile_address = profile_factory_and_regsitry.getProfile(commissioner.address)
    
    # Load the profile contracts
    artist_profile = project.Profile.at(artist_profile_address)
    commissioner_profile = project.Profile.at(commissioner_profile_address)
    
    # Verify art piece was created and added to commissioner's collection
    assert commissioner_profile.myArtCount() == 1
    
    # Get the art piece
    latest_art_pieces = commissioner_profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Verify art piece was added to artist's unverified commissions
    unverified_commissions = artist_profile.getUnverifiedCommissions(0, 10)
    assert len(unverified_commissions) == 1
    assert unverified_commissions[0] == art_piece_address
    
    # Load and verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == commissioner.address  # Commissioner owns the art
    assert art_piece.getArtist() == artist.address  # Artist created it
    assert art_piece.getTitle() == title
    assert art_piece.getDescription() == description

def test_blacklisted_user_cannot_add_to_unverified(setup):
    """
    Test that a blacklisted user can create art for another party,
    but it won't be added to the other party's unverified commissions.
    """
    # Arrange
    blacklister = setup["blacklister"]
    new_user = setup["new_user"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    art_piece_template = setup["art_piece_template"]
    blacklister_profile = setup["blacklister_profile"]
    
    # Add new_user to blacklister's blacklist
    blacklister_profile.addToBlacklist(new_user.address, sender=blacklister)
    
    # Sample art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQmxhY2tsaXN0ZWQgQXJ0IiwiZGVzY3JpcHRpb24iOiJBcnQgZnJvbSBibGFja2xpc3RlZCB1c2VyIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQTNwSlJFRlVDTmRqL0E4REFBQU5BUDkvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
    title = "Blacklisted Art"
    description = "Art from blacklisted user"
    is_artist = True
    
    # Act - Create art piece for blacklister
    result = profile_factory_and_regsitry.createArtPieceForParty(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        blacklister.address,
        ZERO_ADDRESS,
        False,
        sender=new_user
    )
    
    # Assert - Verify new_user profile was created
    assert profile_factory_and_regsitry.hasProfile(new_user.address) == True
    
    # Get profile addresses
    new_user_profile_address = profile_factory_and_regsitry.getProfile(new_user.address)
    
    # Load the profile contracts
    new_user_profile = project.Profile.at(new_user_profile_address)
    
    # Verify art piece was created and added to new_user's collection
    assert new_user_profile.myArtCount() == 1
    
    # Get the art piece
    latest_art_pieces = new_user_profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Verify art piece was NOT added to blacklister's unverified commissions
    unverified_commissions = blacklister_profile.getUnverifiedCommissions(0, 10)
    assert len(unverified_commissions) == 0
    
    # Verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == blacklister.address  # Blacklister still owns the art
    assert art_piece.getArtist() == new_user.address  # New user is the artist

def test_whitelisted_user_adds_directly_to_verified(setup):
    """
    Test that a whitelisted user's art is added directly to verified commissions,
    bypassing the unverified stage.
    """
    # Arrange
    whitelister = setup["whitelister"]
    new_user = setup["new_user"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    art_piece_template = setup["art_piece_template"]
    whitelister_profile = setup["whitelister_profile"]
    
    # Add new_user to whitelister's whitelist
    whitelister_profile.addToWhitelist(new_user.address, sender=whitelister)
    
    # Verify new_user is actually on the whitelist
    assert whitelister_profile.whitelist(new_user.address) == True, "New user should be on whitelist"
    
    # Sample art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiV2hpdGVsaXN0ZWQgQXJ0IiwiZGVzY3JpcHRpb24iOiJBcnQgZnJvbSB3aGl0ZWxpc3RlZCB1c2VyIiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQTNwSlJFRlVDTmRqL0E4REFBQU5BUDkvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
    title = "Whitelisted Art"
    description = "Art from whitelisted user"
    is_artist = True
    
    # Act - Create art piece for whitelister
    result = profile_factory_and_regsitry.createArtPieceForParty(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        whitelister.address,
        ZERO_ADDRESS,
        False,
        sender=new_user
    )
    
    # Assert - Verify new_user profile was created
    assert profile_factory_and_regsitry.hasProfile(new_user.address) == True
    
    # Get profile addresses
    new_user_profile_address = profile_factory_and_regsitry.getProfile(new_user.address)
    
    # Load the profile contracts
    new_user_profile = project.Profile.at(new_user_profile_address)
    
    # Verify art piece was created and added to new_user's collection
    assert new_user_profile.myArtCount() == 1
    
    # Get the art piece
    latest_art_pieces = new_user_profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Print debug info
    print(f"New user address: {new_user.address}")
    print(f"Whitelister address: {whitelister.address}")
    print(f"Art piece address: {art_piece_address}")
    print(f"Is new_user whitelisted: {whitelister_profile.whitelist(new_user.address)}")
    
    # Verify art piece was added to whitelister's verified commissions
    verified_commissions = whitelister_profile.getCommissions(0, 10)
    print(f"Verified commissions count: {len(verified_commissions)}")
    
    # Verify art piece was NOT added to whitelister's unverified commissions
    unverified_commissions = whitelister_profile.getUnverifiedCommissions(0, 10)
    print(f"Unverified commissions count: {len(unverified_commissions)}")
    if len(unverified_commissions) > 0:
        print(f"Unverified commission: {unverified_commissions[0]}")
    
    assert len(verified_commissions) == 1
    assert verified_commissions[0] == art_piece_address
    
    # Verify art piece was NOT added to whitelister's unverified commissions
    assert len(unverified_commissions) == 0

def test_unverified_commissions_disabled(setup):
    """
    Test that when allowUnverifiedCommissions is disabled,
    art pieces are not added to unverified commissions.
    """
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    art_piece_template = setup["art_piece_template"]
    
    # Create profiles for both users
    profile_factory_and_regsitry.createProfile(sender=artist)
    profile_factory_and_regsitry.createProfile(sender=commissioner)
    
    # Get profile addresses
    artist_profile_address = profile_factory_and_regsitry.getProfile(artist.address)
    commissioner_profile_address = profile_factory_and_regsitry.getProfile(commissioner.address)
    
    # Load the profile contracts
    artist_profile = project.Profile.at(artist_profile_address)
    commissioner_profile = project.Profile.at(commissioner_profile_address)
    
    # Disable unverified commissions for artist
    artist_profile.setAllowUnverifiedCommissions(False, sender=artist)
    
    # Sample art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiTm8gVW52ZXJpZmllZCBBcnQiLCJkZXNjcmlwdGlvbiI6IkFydCB3aXRoIHVudmVyaWZpZWQgY29tbWlzc2lvbnMgZGlzYWJsZWQiLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "No Unverified Art"
    description = "Art with unverified commissions disabled"
    is_artist = False  # Commissioner is not the artist
    
    # Act - Create art piece for artist
    result = profile_factory_and_regsitry.createArtPieceForParty(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        artist.address,
        ZERO_ADDRESS,
        False,
        sender=commissioner
    )
    
    # Get the art piece
    latest_art_pieces = commissioner_profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Verify art piece was NOT added to artist's unverified commissions
    unverified_commissions = artist_profile.getUnverifiedCommissions(0, 10)
    assert len(unverified_commissions) == 0
    
    # Verify art piece was NOT added to artist's verified commissions either
    verified_commissions = artist_profile.getCommissions(0, 10)
    assert len(verified_commissions) == 0
    
    # Verify the art piece properties
    art_piece = project.ArtPiece.at(art_piece_address)
    assert art_piece.getOwner() == commissioner.address  # Commissioner owns the art
    assert art_piece.getArtist() == artist.address  # Artist created it

def test_ai_generated_flag_set_correctly(setup):
    """
    Test that the AI generated flag is set correctly on the art piece.
    """
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    art_piece_template = setup["art_piece_template"]
    
    # Sample art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiQUkgQXJ0IiwiZGVzY3JpcHRpb24iOiJBSSBnZW5lcmF0ZWQgYXJ0IiwiaW1hZ2UiOiJkYXRhOmltYWdlL3BuZztiYXNlNjQsaVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFRQUFBQUVDQUlBQUFCQ05DdkRBQUFBQTNwSlJFRlVDTmRqL0E4REFBQU5BUDkvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
    title = "AI Art"
    description = "AI generated art"
    is_artist = True
    
    # Act - Create AI generated art piece
    profile_factory_and_regsitry.createArtPieceForParty(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        commissioner.address,
        ZERO_ADDRESS,
        True,  # AI generated
        sender=artist
    )
    
    # Get the profile addresses
    artist_profile_address = profile_factory_and_regsitry.getProfile(artist.address)
    
    # Load the artist profile
    artist_profile = project.Profile.at(artist_profile_address)
    
    # Get the art piece from the artist's latest art pieces
    latest_art_pieces = artist_profile.getLatestArtPieces()
    assert len(latest_art_pieces) == 1
    art_piece_address = latest_art_pieces[0]
    
    # Load and verify the art piece
    art_piece = project.ArtPiece.at(art_piece_address)
    
    # Verify AI generated flag is set correctly
    assert art_piece.getAIGenerated() == True

def test_cannot_create_art_for_self(setup):
    """
    Test that a user cannot create art for themselves using createArtPieceForParty.
    """
    # Arrange
    artist = setup["artist"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    art_piece_template = setup["art_piece_template"]
    
    # Sample art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiU2VsZiBBcnQiLCJkZXNjcmlwdGlvbiI6IkFydCBmb3Igc2VsZiIsImltYWdlIjoiZGF0YTppbWFnZS9wbmc7YmFzZTY0LGlWQk9SdzBLR2dvQUFBQU5TVWhFVWdBQUFBUUFBQUFFQ0FJQUFBQKNOQ3ZEQUFBQUF4cEpSRUZVQ05kai9BOERBQUFOQVDkvaFpZYUFBQUFBRWxGVGtTdVFtQ0MifQ=="
    title = "Self Art"
    description = "Art for self"
    is_artist = True
    
    # Act & Assert - Attempt to create art for self should fail
    with pytest.raises(Exception):
        profile_factory_and_regsitry.createArtPieceForParty(
            art_piece_template.address,
            token_uri_data,
            "avif",
            title,
            description,
            is_artist,
            artist.address,  # Same as sender
            ZERO_ADDRESS,
            False,
            sender=artist
        )

def test_events_emitted_correctly(setup):
    """
    Test that the appropriate events are emitted when creating art for another party.
    """
    # Arrange
    artist = setup["artist"]
    commissioner = setup["commissioner"]
    profile_factory_and_regsitry = setup["profile_factory_and_regsitry"]
    art_piece_template = setup["art_piece_template"]
    
    # Sample art piece data
    token_uri_data = b"data:application/json;base64,eyJuYW1lIjoiRXZlbnQgQXJ0IiwiZGVzY3JpcHRpb24iOiJBcnQgZm9yIGV2ZW50IHRlc3RpbmciLCJpbWFnZSI6ImRhdGE6aW1hZ2UvcG5nO2Jhc2U2NCxpVkJPUncwS0dnb0FBQUFOU1VoRVVnQUFBQVFBQUFBRUNBSUFBQUJDTkN2REFBQUFBM3BKUkVGVUNOZGovQThEQUFBTkFQOS9oWllhQUFBQUFFbEZUa1N1UW1DQyJ9"
    title = "Event Art"
    description = "Art for event testing"
    is_artist = True
    
    # Act - Create art piece and capture events
    tx = profile_factory_and_regsitry.createArtPieceForParty(
        art_piece_template.address,
        token_uri_data,
        "avif",
        title,
        description,
        is_artist,
        commissioner.address,
        ZERO_ADDRESS,
        False,
        sender=artist
    )
    
    # Assert - Check for ProfileCreated events
    profile_created_events = [e for e in tx.decode_logs() if e.event_name == "ProfileCreated"]
    assert len(profile_created_events) == 2  # One for artist, one for commissioner
    
    # Check for ArtPieceCreated event
    art_piece_created_events = [e for e in tx.decode_logs() if e.event_name == "ArtPieceCreated"]
    assert len(art_piece_created_events) == 1
    
    # Check for ArtPieceCreatedForParty event
    art_piece_for_party_events = [e for e in tx.decode_logs() if e.event_name == "ArtPieceCreatedForParty"]
    assert len(art_piece_for_party_events) == 1
    
    # Verify ArtPieceCreatedForParty event data - access event data properly
    event = art_piece_for_party_events[0]
    assert event.creator == artist.address
    assert event.other_party == commissioner.address
    assert event.is_artist == is_artist 