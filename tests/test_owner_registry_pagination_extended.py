import pytest
from ape import accounts, project
import time
from eth_utils import to_checksum_address

# Define constant for zero address
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

@pytest.fixture
def setup():
    # Get accounts for testing - use test_accounts which are available in the test environment
    deployer = accounts.test_accounts[0]
    user = accounts.test_accounts[1]
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileSocial template
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    
    # Deploy L2OwnershipRelay and ArtCommissionHub template
    l2_relay = project.L2OwnershipRelay.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)

    # Deploy ProfileFactoryAndRegistry with three templates
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address, 
        sender=deployer
    )
    
    # Deploy ArtCommissionHubOwners with the required parameters
    art_collection_ownership_registry = project.ArtCommissionHubOwners.deploy(
        l2_relay.address, 
        commission_hub_template.address, 
        art_piece_template.address,
        sender=deployer
    )
    
    # Set ArtCommissionHubOwners in ProfileFactoryAndRegistry
    profile_factory_and_registry.linkArtCommissionHubOwnersContract(art_collection_ownership_registry.address, sender=deployer)
    
    # Set ProfileFactoryAndRegistry in ArtCommissionHubOwners
    art_collection_ownership_registry.linkProfileFactoryAndRegistry(profile_factory_and_registry.address, sender=deployer)
    
    # Set L2OwnershipRelay to the deployer for testing purposes
    art_collection_ownership_registry.setL2OwnershipRelay(deployer.address, sender=deployer)
    
    # Create a profile for the user
    profile_factory_and_registry.createProfile(sender=user)
    user_profile_address = profile_factory_and_registry.getProfile(user.address)
    user_profile = project.Profile.at(user_profile_address)
    
    # Deploy multiple commission hubs for testing pagination
    commission_hubs = []
    for i in range(50):  # Create 50 commission hubs
        nft_contract = deployer.address
        token_id = i + 1
        art_collection_ownership_registry.registerNFTOwnerFromParentChain(1, nft_contract, token_id, user.address, sender=deployer)
        commission_hub_address = art_collection_ownership_registry.getArtCommissionHubByOwner(1, nft_contract, token_id)
        commission_hubs.append(commission_hub_address)
    
    return {
        "deployer": deployer,
        "user": user,
        "profile_factory_and_registry": profile_factory_and_registry,
        "art_collection_ownership_registry": art_collection_ownership_registry,
        "user_profile": user_profile,
        "commission_hubs": commission_hubs
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

def test_forward_pagination_offset_based(setup):
    """
    Test retrieving commission hubs using offset-based FORWARD pagination.
    """
    # Arrange
    user = setup["user"]
    art_collection_ownership_registry = setup["art_collection_ownership_registry"]
    commission_hubs = setup["commission_hubs"] # 50 hubs, oldest at [0], newest at [49]
    total_hubs_created = len(commission_hubs)
    
    test_cases = [
        {"offset": 0, "count": 10},  # First 10 items
        {"offset": 10, "count": 15}, # Middle section: hubs[10]..hubs[24]
        {"offset": 40, "count": 20}, # End section (request 20, get 10): hubs[40]..hubs[49]
        {"offset": 0, "count": 50},   # All 50 items
        {"offset": 0, "count": 100}, # More than available (request 100, get 50, as per contract MAX_ITEMS_PER_PAGE is 50)
        {"offset": 50, "count": 10},  # Offset at/beyond end, should be empty
        {"offset": 49, "count": 10}, # Request last one: hubs[49]
    ]
    
    for case in test_cases:
        offset = case["offset"]
        count = case["count"]
        
        hubs_page = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset, count, False)
        
        expected_hubs_segment = []
        if offset < total_hubs_created:
            start_index = offset
            # The contract function getCommissionHubsByOwnerWithOffset caps results at 50.
            num_to_fetch = min(count, total_hubs_created - start_index, 50)
            expected_hubs_segment = commission_hubs[start_index : start_index + num_to_fetch]
        
        assert len(hubs_page) == len(expected_hubs_segment), f"Forward: Failed for offset={offset}, count={count}. Got len {len(hubs_page)}, expected len {len(expected_hubs_segment)}"
        assert hubs_page == expected_hubs_segment, f"Forward: Mismatch for offset={offset}, count={count}. Got {hubs_page}, expected {expected_hubs_segment}"

def test_reverse_pagination_offset_based(setup):
    """
    Test retrieving commission hubs using offset-based REVERSE pagination.
    """
    # Arrange
    user = setup["user"]
    art_collection_ownership_registry = setup["art_collection_ownership_registry"]
    commission_hubs = setup["commission_hubs"] # 50 hubs, newest is at commission_hubs[49], oldest at commission_hubs[0]
    total_hubs_created = len(commission_hubs)

    test_cases = [
        {"offset_skip": 0, "count": 10},   # Last 10 items (newest first) -> hubs[49]..hubs[40]
        {"offset_skip": 10, "count": 15},  # Skip 10 newest, get next 15 -> hubs[39]..hubs[25]
        {"offset_skip": 40, "count": 20},  # Skip 40 newest, get next 20 (only 10 avail) -> hubs[9]..hubs[0]
        {"offset_skip": 0, "count": 50},    # All 50 items, newest first -> hubs[49]..hubs[0]
        {"offset_skip": 0, "count": 100},   # Request 100 (get 50), newest first -> hubs[49]..hubs[0]
        {"offset_skip": 50, "count": 10},   # Skip all 50, should be empty
        {"offset_skip": 49, "count": 10}  # Skip 49 newest, get oldest 1 -> hubs[0]
    ]

    for case in test_cases:
        offset_skip_from_end = case["offset_skip"]
        count = case["count"]
        
        hubs_page = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset_skip_from_end, count, True)
        
        expected_hubs_segment = []
        if offset_skip_from_end < total_hubs_created:
            newest_item_index_to_fetch = total_hubs_created - 1 - offset_skip_from_end
            items_available_backwards = newest_item_index_to_fetch + 1 
            # The contract function getCommissionHubsByOwnerWithOffset caps results at 50.
            num_to_fetch = min(count, items_available_backwards, 50)

            if num_to_fetch > 0:
                for i in range(num_to_fetch):
                    expected_hubs_segment.append(commission_hubs[newest_item_index_to_fetch - i])
        
        assert len(hubs_page) == len(expected_hubs_segment), f"Reverse: Failed for offset_skip={offset_skip_from_end}, count={count}. Got len {len(hubs_page)}, expected len {len(expected_hubs_segment)}"
        assert hubs_page == expected_hubs_segment, f"Reverse: Mismatch for offset_skip={offset_skip_from_end}, count={count}. Got {hubs_page}, expected {expected_hubs_segment}"

def test_get_commission_hubs_offset_out_of_bounds(setup):
    """
    Test retrieving commission hubs with offset number beyond available data
    """
    # Arrange
    user = setup["user"]
    art_collection_ownership_registry = setup["art_collection_ownership_registry"]
    total_hubs_created = len(setup["commission_hubs"]) # 50
    
    # Test requesting a page beyond available data (forward)
    offset = total_hubs_created # e.g., 50. Offset 50 is out of bounds for 50 items (0-49)
    count = 10
    
    hubs_forward = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset, count, False)
    assert len(hubs_forward) == 0, "Forward pagination with offset at length should return empty."

    offset_beyond = total_hubs_created + 5 # e.g., 55
    hubs_forward_beyond = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset_beyond, count, False)
    assert len(hubs_forward_beyond) == 0, "Forward pagination with offset beyond length should return empty."

    # Test requesting a page beyond available data (reverse)
    # offset means skip N from end. If we skip all or more, should be empty.
    offset_skip_from_end_exact = total_hubs_created # e.g., 50. Skipping all 50.
    hubs_reverse_exact = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset_skip_from_end_exact, count, True)
    assert len(hubs_reverse_exact) == 0, "Reverse pagination skipping exactly all items should return empty."

    offset_skip_from_end_beyond = total_hubs_created + 5 # e.g., 55
    hubs_reverse_beyond = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset_skip_from_end_beyond, count, True)
    assert len(hubs_reverse_beyond) == 0, "Reverse pagination with offset (skip from end) beyond length should return empty."

def test_get_commission_hub_count(setup):
    """
    Test getCommissionHubCountByOwner returns the correct count
    """
    # Arrange
    user = setup["user"]
    art_collection_ownership_registry = setup["art_collection_ownership_registry"]
    commission_hubs = setup["commission_hubs"]
    
    # Get the count
    hub_count = art_collection_ownership_registry.getCommissionHubCountByOwner(user.address)
    
    # Verify correct count
    assert hub_count == len(commission_hubs)

@pytest.fixture
def setup_empty_user():
    """
    Setup for testing a user with no hubs
    """
    # Get accounts for testing
    deployer = accounts.test_accounts[0]
    user_with_no_hubs = accounts.test_accounts[2]
    
    # Deploy necessary contracts
    profile_template = project.Profile.deploy(sender=deployer)
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    art_piece_template = project.ArtPiece.deploy(sender=deployer)
    l2_relay = project.L2OwnershipRelay.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)

    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    art_collection_ownership_registry = project.ArtCommissionHubOwners.deploy(
        l2_relay.address, 
        commission_hub_template.address, 
        art_piece_template.address, 
        sender=deployer
    )
    
    # Set ArtCommissionHubOwners in ProfileFactoryAndRegistry
    profile_factory_and_registry.linkArtCommissionHubOwnersContract(art_collection_ownership_registry.address, sender=deployer)

    # Set ProfileFactoryAndRegistry in ArtCommissionHubOwners
    art_collection_ownership_registry.linkProfileFactoryAndRegistry(profile_factory_and_registry.address, sender=deployer)

    # Set L2OwnershipRelay to the deployer for testing purposes
    art_collection_ownership_registry.setL2OwnershipRelay(deployer.address, sender=deployer)
    
    return {
        "deployer": deployer,
        "user_with_no_hubs": user_with_no_hubs,
        "art_collection_ownership_registry": art_collection_ownership_registry
    ,
        "art_sales_1155_template": art_sales_1155_template,
        "art_edition_1155_template": art_edition_1155_template,
        "art_sales_1155_template": art_sales_1155_template}

def test_get_commission_hubs_for_user_with_no_hubs(setup_empty_user):
    """
    Test retrieving commission hubs for a user with no hubs using offset pagination.
    """
    # Arrange
    user_with_no_hubs = setup_empty_user["user_with_no_hubs"]
    art_collection_ownership_registry = setup_empty_user["art_collection_ownership_registry"]
    
    # Get hubs for user with no hubs (forward)
    hubs_forward = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user_with_no_hubs.address, 0, 10, False)
    assert len(hubs_forward) == 0, "Forward pagination for user with no hubs should return empty."
    
    # Get hubs for user with no hubs (reverse)
    hubs_reverse = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user_with_no_hubs.address, 0, 10, True)
    assert len(hubs_reverse) == 0, "Reverse pagination for user with no hubs should return empty."
    
    # Verify count is 0
    hub_count = art_collection_ownership_registry.getCommissionHubCountByOwner(user_with_no_hubs.address)
    assert hub_count == 0

