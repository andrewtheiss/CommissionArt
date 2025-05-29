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
    
    # Deploy Profile template
    profile_template = project.Profile.deploy(sender=deployer)
    
    # Deploy ProfileSocial template
    profile_social_template = project.ProfileSocial.deploy(sender=deployer)
    
    # Deploy ArtPiece template
    art_piece_template = project.ArtPiece.deploy(sender=deployer)

    # Deploy L2OwnershipRelay and ArtCommissionHub template for ArtCommissionHubOwners
    l2_relay = project.L2OwnershipRelay.deploy(sender=deployer)
    commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)

    # Deploy ArtEdition1155 template
    art_edition_1155_template = project.ArtEdition1155.deploy(sender=deployer)
    
    # Deploy ArtSales1155 template
    art_sales_1155_template = project.ArtSales1155.deploy(sender=deployer)
    
    # Deploy ProfileFactoryAndRegistry with both templates
    profile_factory_and_registry = project.ProfileFactoryAndRegistry.deploy(
        profile_template.address, profile_social_template.address, commission_hub_template.address, art_edition_1155_template.address, art_sales_1155_template.address,
        sender=deployer
    )
    
    # Deploy ArtCommissionHubOwners with the required parameters
    art_collection_ownership_registry = project.ArtCommissionHubOwners.deploy(
        l2_relay.address, 
        commission_hub_template.address, 
        art_piece_template.address,  # Added art_piece_template
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
    for i in range(25):  # Create 25 commission hubs
        # Use a different NFT contract address for each - use deployer's address with different indices
        nft_contract = deployer.address  # Use a valid address that already exists
        token_id = i + 1
        
        # Register NFT ownership - now the deployer is authorized as L2OwnershipRelay
        art_collection_ownership_registry.registerNFTOwnerFromParentChain(1, nft_contract, token_id, user.address, sender=deployer)
        
        # Get the created commission hub address
        # Note: getArtCommissionHubByOwner returns a single address, not what's needed for a list.
        # We need to retrieve it from the event or a direct lookup if the function returns the created hub.
        # For testing, we will assume it's correctly registered and fetchable via pagination.
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

def test_get_commission_hubs_for_owner_different_page_sizes(setup):
    """
    Test retrieving commission hubs with different page sizes using offset-based pagination.
    Covers forward pagination with various counts.
    """
    # Arrange
    user = setup["user"]
    art_collection_ownership_registry = setup["art_collection_ownership_registry"]
    commission_hubs = setup["commission_hubs"] # 25 hubs
    total_hubs_created = len(commission_hubs)

    test_cases = [
        {"offset": 0, "count": 5, "reverse": False},
        {"offset": 5, "count": 5, "reverse": False},
        {"offset": 0, "count": 10, "reverse": False},
        {"offset": 10, "count": 10, "reverse": False},
        {"offset": 20, "count": 10, "reverse": False}, # Request 10, get 5
        {"offset": 0, "count": 25, "reverse": False},  # Request all
        {"offset": 0, "count": 50, "reverse": False},  # Request more than available, capped at 50
        {"offset": 24, "count": 5, "reverse": False} # Request last one
    ]

    for case in test_cases:
        offset = case["offset"]
        count = case["count"]
        reverse = case["reverse"]

        hubs = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset, count, reverse)
        
        expected_start_index = offset
        
        # Calculate expected count based on availability and function's 50 item cap
        if offset >= total_hubs_created:
            expected_retrieved_count = 0
        else:
            expected_retrieved_count = min(count, total_hubs_created - offset)
        
        assert len(hubs) == expected_retrieved_count, f"Failed for offset={offset}, count={count}, reverse={reverse}"
        
        for i in range(len(hubs)):
            assert hubs[i] == commission_hubs[expected_start_index + i], f"Mismatch at index {i} for offset={offset}, count={count}"

def test_reverse_pagination_offset_based(setup):
    """
    Test retrieving commission hubs with offset-based reverse pagination.
    """
    # Arrange
    user = setup["user"]
    art_collection_ownership_registry = setup["art_collection_ownership_registry"]
    commission_hubs = setup["commission_hubs"] # 25 hubs, newest is at commission_hubs[24], oldest at commission_hubs[0]
    total_hubs_created = len(commission_hubs)

    test_cases = [
        {"offset": 0, "count": 5, "reverse": True},   # Last 5 items (newest first) -> hubs[24]..hubs[20]
        {"offset": 5, "count": 5, "reverse": True},   # Skip 5 newest, get next 5 -> hubs[19]..hubs[15]
        {"offset": 0, "count": 10, "reverse": True},  # Last 10 items -> hubs[24]..hubs[15]
        {"offset": 10, "count": 10, "reverse": True}, # Skip 10 newest, get next 10 -> hubs[14]..hubs[5]
        {"offset": 20, "count": 10, "reverse": True}, # Skip 20 newest, get next 10 (only 5 avail) -> hubs[4]..hubs[0]
        {"offset": 0, "count": 25, "reverse": True},  # Request all, newest first -> hubs[24]..hubs[0]
        {"offset": 0, "count": 50, "reverse": True},  # Request more than available -> hubs[24]..hubs[0]
        {"offset": 24, "count": 5, "reverse": True}  # Skip 24 newest, get oldest 1 -> hubs[0]
    ]

    for case in test_cases:
        offset_skip_from_end = case["offset"]
        count = case["count"]
        reverse = case["reverse"]

        hubs_page = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset_skip_from_end, count, reverse)
        
        # Calculate expected results
        if offset_skip_from_end >= total_hubs_created:
            expected_retrieved_count = 0
            expected_hubs_segment = []
        else:
            # For reverse: offset is items to skip from end.
            # Start index in original array for comparison: total_hubs_created - 1 - offset_skip_from_end
            # Example: 25 hubs. offset_skip_from_end=0. start_index = 24.
            # Example: 25 hubs. offset_skip_from_end=5. start_index = 19.
            
            actual_start_index_from_end = total_hubs_created - 1 - offset_skip_from_end
            
            # Number of items that can possibly be returned from this start_index backwards
            items_available_from_start = actual_start_index_from_end + 1
            
            expected_retrieved_count = min(count, items_available_from_start)
            
            expected_hubs_segment = []
            if expected_retrieved_count > 0:
                for i in range(expected_retrieved_count):
                    expected_hubs_segment.append(commission_hubs[actual_start_index_from_end - i])
        
        assert len(hubs_page) == expected_retrieved_count, f"Failed for offset={offset_skip_from_end}, count={count}, reverse={reverse}. Got {len(hubs_page)}, expected {expected_retrieved_count}"
        
        for i in range(len(hubs_page)):
            assert hubs_page[i] == expected_hubs_segment[i], f"Mismatch at index {i} for offset={offset_skip_from_end}, count={count}. Got {hubs_page[i]}, expected {expected_hubs_segment[i]}"


def test_get_commission_hubs_offset_out_of_bounds(setup):
    """
    Test retrieving commission hubs with offset beyond available data.
    """
    # Arrange
    user = setup["user"]
    art_collection_ownership_registry = setup["art_collection_ownership_registry"]
    total_hubs_created = len(setup["commission_hubs"]) # 25
    
    # Test requesting a page beyond available data (forward)
    offset = total_hubs_created + 5 # e.g., 30
    count = 10
    
    hubs = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset, count, False)
    assert len(hubs) == 0, "Forward pagination with offset out of bounds should return empty."

    # Test requesting a page beyond available data (reverse)
    # offset means skip N from end. If we skip all or more, should be empty.
    offset_skip_from_end = total_hubs_created + 5 # e.g., 30
    hubs_reverse = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset_skip_from_end, count, True)
    assert len(hubs_reverse) == 0, "Reverse pagination with offset (skip from end) out of bounds should return empty."

    offset_skip_from_end_exact = total_hubs_created # e.g., 25. Skipping all 25.
    hubs_reverse_exact = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(user.address, offset_skip_from_end_exact, count, True)
    assert len(hubs_reverse_exact) == 0, "Reverse pagination skipping exactly all items should return empty."


def test_get_commission_hubs_for_owner_count(setup):
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

def test_get_commission_hubs_for_nonexistent_owner(setup):
    """
    Test retrieving commission hubs for a user with no hubs
    """
    # Arrange
    deployer = setup["deployer"]  # Use deployer as a user with no hubs
    art_collection_ownership_registry = setup["art_collection_ownership_registry"]
    
    # Get hubs for user with no hubs - use a different account that has no hubs
    no_hub_user = accounts.test_accounts[2]
    hubs = art_collection_ownership_registry.getCommissionHubsByOwnerWithOffset(no_hub_user.address, 0, 10, False)
    
    # Verify empty array returned
    assert len(hubs) == 0
    
    # Verify count is 0
    hub_count = art_collection_ownership_registry.getCommissionHubCountByOwner(no_hub_user.address)
    assert hub_count == 0 