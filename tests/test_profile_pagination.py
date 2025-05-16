import pytest
from ape import accounts, project
import time
from eth_utils import to_checksum_address

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    artist = accounts.test_accounts[2]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with the template
    # Deploy ProfileSocial template
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)


    # Deploy ProfileFactoryAndRegistry with both templates
    profile_factory_and_regsitry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address,
        profile_social_template.address,
        sender=deployer
    )
    
    # Create a profile for the user
    profile_factory_and_regsitry.createProfile(sender=user)
    user_profile_address = profile_factory_and_regsitry.getProfile(user.address)
    user_profile = project.Profile.at(user_profile_address)
    
    return {
        "deployer": deployer,
        "user": user,
        "artist": artist,
        "profile_factory_and_regsitry": profile_factory_and_regsitry,
        "user_profile": user_profile
    }

def test_art_pieces_pagination_empty(setup):
    """
    Test art pieces pagination with empty array
    """
    # Arrange
    user_profile = setup["user_profile"]
    
    # Get art pieces with offset 0
    result = user_profile.getArtPiecesByOffset(0, 10)
    
    # Verify empty array is returned
    assert len(result) == 0
    
    # Test with offset beyond available items
    result_empty = user_profile.getArtPiecesByOffset(100, 10)
    assert len(result_empty) == 0

def test_commissions_pagination_empty(setup):
    """
    Test commissions pagination with empty array
    """
    # Arrange
    user_profile = setup["user_profile"]
    
    # Get commissions with offset 0
    result = user_profile.getCommissionsByOffset(0, 10)
    
    # Verify empty array is returned
    assert len(result) == 0
    
    # Test with offset beyond available items
    result_empty = user_profile.getCommissionsByOffset(100, 10)
    assert len(result_empty) == 0

def test_unverified_commissions_pagination_empty(setup):
    """
    Test unverified commissions pagination with empty array
    """
    # Arrange
    user_profile = setup["user_profile"]
    
    # Get unverified commissions with offset 0
    result = user_profile.getUnverifiedCommissionsByOffset(0, 10)
    
    # Verify empty array is returned
    assert len(result) == 0
    
    # Test with offset beyond available items
    result_empty = user_profile.getUnverifiedCommissionsByOffset(100, 10)
    assert len(result_empty) == 0

def test_commission_hubs_pagination_empty(setup):
    """
    Test commission hubs pagination with empty array
    """
    # Arrange
    user_profile = setup["user_profile"]
    
    # Get commission hubs with offset 0
    result = user_profile.getCommissionHubsByOffset(0, 10)
    
    # Verify empty array is returned
    assert len(result) == 0
    
    # Test with offset beyond available items
    result_empty = user_profile.getCommissionHubsByOffset(100, 10)
    assert len(result_empty) == 0 