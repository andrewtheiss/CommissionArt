import pytest
from ape import accounts, project

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    owner = accounts.test_accounts[1]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileHub
    profile_hub = project.ProfileHub.deploy(profile_template.address, sender=deployer)
    
    # Create a profile for testing
    profile_hub.createProfile(sender=owner)
    
    profile_address = profile_hub.getProfile(owner.address)
    profile = project.Profile.at(profile_address)
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    return {
        "deployer": deployer,
        "owner": owner,
        "profile": profile,
        "profile_hub": profile_hub,
        "art_piece_template": art_piece_template
    }

def test_minimal_commission_array(setup):
    """Test minimal commission array functionality"""
    owner = setup["owner"]
    profile = setup["profile"]
    art_piece_template = setup["art_piece_template"]
    
    # Test initial state
    assert profile.commissionCount() == 0
    
    # Create a real ArtPiece for testing
    # First, create the ArtPiece with minimal data
    token_uri_data = b"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    token_uri_format = "png"
    
    # Create a valid art piece
    art_piece = project.ArtPiece.deploy(sender=owner)
    art_piece.initialize(
        token_uri_data,
        token_uri_format,
        "Test Art",
        "Test Description",
        owner.address,  # Owner
        owner.address,  # Artist (same as owner for test)
        "0x0000000000000000000000000000000000000000",  # No commission hub
        False,  # Not AI generated
        sender=owner
    )
    
    # Test adding a commission
    profile.addCommission(art_piece.address, sender=owner)
    
    # Check count was updated
    assert profile.commissionCount() == 1
    
    # Check commission was added
    commissions = profile.getCommissions(0, 10)
    assert len(commissions) == 1
    assert commissions[0] == art_piece.address
    
    # Test removing the commission
    profile.removeCommission(art_piece.address, sender=owner)
    
    # Check count was updated
    assert profile.commissionCount() == 0
    
    # Check commission was removed
    commissions = profile.getCommissions(0, 10)
    assert len(commissions) == 0 