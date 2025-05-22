import pytest
from ape import accounts, project
from eth_account import Account
import eth_utils
import secrets

@pytest.fixture
def array_manager():
    return project.ArrayManager.deploy(sender=accounts.test_accounts[0])

@pytest.fixture
def test_addresses():
    return [accounts.test_accounts[i] for i in range(1, 6)]

@pytest.fixture
def many_addresses():
    """Generate over 50 valid Ethereum addresses"""
    addresses = []
    for i in range(60):  # Generate 60 addresses
        priv_key = secrets.token_hex(32)
        account = Account.from_key(priv_key)
        addresses.append(eth_utils.to_checksum_address(account.address))
    return addresses

# Existing tests remain unchanged until the new tests are added below

def test_initial_state(array_manager):
    """Test initial state of the contract"""
    assert array_manager.get_length() == 0

def test_add_to_array(array_manager, test_addresses):
    """Test adding items to the array"""
    array_manager.add_to_array(test_addresses[0], sender=accounts.test_accounts[0])
    assert array_manager.contains(test_addresses[0])
    assert array_manager.get_length() == 1
    
    array_manager.add_to_array(test_addresses[1], sender=accounts.test_accounts[0])
    array_manager.add_to_array(test_addresses[2], sender=accounts.test_accounts[0])
    assert array_manager.get_length() == 3
    
    with pytest.raises(Exception):
        array_manager.add_to_array(test_addresses[0], sender=accounts.test_accounts[0])

def test_remove_from_array(array_manager, test_addresses):
    """Test removing items from the array"""
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    initial_length = array_manager.get_length()
    
    array_manager.remove_from_array(test_addresses[0], sender=accounts.test_accounts[0])
    assert not array_manager.contains(test_addresses[0])
    assert array_manager.get_length() == initial_length - 1
    
    array_manager.remove_from_array(test_addresses[2], sender=accounts.test_accounts[0])
    assert not array_manager.contains(test_addresses[2])
    assert array_manager.get_length() == initial_length - 2
    
    array_manager.remove_from_array(test_addresses[4], sender=accounts.test_accounts[0])
    assert not array_manager.contains(test_addresses[4])
    assert array_manager.get_length() == initial_length - 3
    
    with pytest.raises(Exception):
        array_manager.remove_from_array(test_addresses[0], sender=accounts.test_accounts[0])

def test_contains(array_manager, test_addresses):
    """Test the contains method"""
    assert not array_manager.contains(test_addresses[0])
    
    array_manager.add_to_array(test_addresses[0], sender=accounts.test_accounts[0])
    assert array_manager.contains(test_addresses[0])
    assert not array_manager.contains(test_addresses[1])
    
    array_manager.remove_from_array(test_addresses[0], sender=accounts.test_accounts[0])
    assert not array_manager.contains(test_addresses[0])

def test_get_length(array_manager, test_addresses):
    """Test the get_length method"""
    assert array_manager.get_length() == 0
    
    for i, addr in enumerate(test_addresses, 1):
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
        assert array_manager.get_length() == i
    
    for i, addr in enumerate(test_addresses):
        array_manager.remove_from_array(addr, sender=accounts.test_accounts[0])
        assert array_manager.get_length() == len(test_addresses) - i - 1

def test_get_at(array_manager, test_addresses):
    """Test the get_at method"""
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    for i, addr in enumerate(test_addresses):
        assert array_manager.get_at(i) == addr
    
    with pytest.raises(Exception):
        array_manager.get_at(len(test_addresses), sender=accounts.test_accounts[0])

def test_set_at(array_manager, test_addresses):
    """Test the set_at method"""
    for addr in test_addresses[:3]:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    array_manager.set_at(0, test_addresses[3], sender=accounts.test_accounts[0])
    array_manager.set_at(2, test_addresses[4], sender=accounts.test_accounts[0])
    
    assert array_manager.get_at(0) == test_addresses[3]
    assert array_manager.get_at(1) == test_addresses[1]
    assert array_manager.get_at(2) == test_addresses[4]
    
    assert array_manager.get_length() == 3
    
    with pytest.raises(Exception):
        array_manager.set_at(3, test_addresses[0], sender=accounts.test_accounts[0])

def test_clear_array(array_manager, test_addresses):
    """Test the clear_array method"""
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    assert array_manager.get_length() == len(test_addresses)
    
    array_manager.clear_array(sender=accounts.test_accounts[0])
    
    assert array_manager.get_length() == 0
    for addr in test_addresses:
        assert not array_manager.contains(addr)

def test_get_array_slice(array_manager, test_addresses):
    """Test the get_array_slice method"""
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    page = array_manager.get_array_slice(0, 2)
    assert len(page) == 2
    assert page[0] == test_addresses[0]
    assert page[1] == test_addresses[1]
    
    page = array_manager.get_array_slice(1, 2)
    assert len(page) == 2
    assert page[0] == test_addresses[2]
    assert page[1] == test_addresses[3]
    
    page = array_manager.get_array_slice(2, 2)
    assert len(page) == 1
    assert page[0] == test_addresses[4]
    
    page = array_manager.get_array_slice(10, 2)
    assert len(page) == 0
    
    page = array_manager.get_array_slice(0, 10)
    assert len(page) == len(test_addresses)
    for i, addr in enumerate(test_addresses):
        assert page[i] == addr

def test_get_array_slice_reverse(array_manager, test_addresses):
    """Test the get_array_slice_reverse method"""
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    page = array_manager.get_array_slice_reverse(0, 2)
    assert len(page) == 2
    assert page[0] == test_addresses[4]
    assert page[1] == test_addresses[3]
    
    page = array_manager.get_array_slice_reverse(1, 2)
    assert len(page) == 2
    assert page[0] == test_addresses[2]
    assert page[1] == test_addresses[1]
    
    page = array_manager.get_array_slice_reverse(2, 2)
    assert len(page) == 1
    assert page[0] == test_addresses[0]
    
    page = array_manager.get_array_slice_reverse(10, 2)
    assert len(page) == 0

def test_large_array(array_manager, many_addresses):
    """Test with over 50 addresses"""
    for addr in many_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    assert array_manager.get_length() == len(many_addresses)
    
    for addr in many_addresses:
        assert array_manager.contains(addr)
    
    page_size = 10
    page = array_manager.get_array_slice(0, page_size)
    assert len(page) == page_size
    for i in range(page_size):
        assert page[i] == many_addresses[i]
    
    page = array_manager.get_array_slice(3, page_size)
    assert len(page) == page_size
    for i in range(page_size):
        assert page[i] == many_addresses[30 + i]
    
    page = array_manager.get_array_slice_reverse(0, page_size)
    assert len(page) == page_size
    for i in range(page_size):
        assert page[i] == many_addresses[len(many_addresses) - 1 - i]
    
    for i in range(0, 30, 3):
        array_manager.remove_from_array(many_addresses[i], sender=accounts.test_accounts[0])
    
    for i in range(0, 30, 3):
        assert not array_manager.contains(many_addresses[i])
    
    array_manager.clear_array(sender=accounts.test_accounts[0])
    assert array_manager.get_length() == 0

# New tests for get_array_by_offset method

def test_get_array_by_offset_front_pagination(array_manager, test_addresses):
    """Test front pagination with get_array_by_offset (reverse = False)
    
    Description: Verifies fetching items from a given offset in ascending order.
    How it accesses the array: Starts at _offset and collects _count items moving forward.
    """
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Fetch from the beginning
    result = array_manager.get_array_by_offset(0, 2, False)
    assert len(result) == 2
    assert result[0] == test_addresses[0]
    assert result[1] == test_addresses[1]
    
    # Fetch from the middle
    result = array_manager.get_array_by_offset(2, 2, False)
    assert len(result) == 2
    assert result[0] == test_addresses[2]
    assert result[1] == test_addresses[3]
    
    # Fetch near the end (partial slice)
    result = array_manager.get_array_by_offset(4, 2, False)
    assert len(result) == 1
    assert result[0] == test_addresses[4]
    
    # Fetch with offset out of bounds
    result = array_manager.get_array_by_offset(5, 2, False)
    assert len(result) == 0

def test_get_array_by_offset_back_pagination(array_manager, test_addresses):
    """Test back pagination with get_array_by_offset (reverse = True)
    
    Description: Verifies fetching items from a given offset in descending order.
    How it accesses the array: Starts at _offset and collects _count items moving backward.
    """
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Fetch from the end
    result = array_manager.get_array_by_offset(4, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[4]
    assert result[1] == test_addresses[3]
    
    # Fetch from the middle
    result = array_manager.get_array_by_offset(2, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[2]
    assert result[1] == test_addresses[1]
    
    # Fetch near the start (partial slice)
    result = array_manager.get_array_by_offset(0, 2, True)
    assert len(result) == 1
    assert result[0] == test_addresses[0]
    
    # Fetch with offset out of bounds (adjusted to last index)
    result = array_manager.get_array_by_offset(10, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[4]
    assert result[1] == test_addresses[3]

def test_get_array_by_offset_edge_cases(array_manager, test_addresses):
    """Test edge cases for get_array_by_offset
    
    Description: Ensures the method handles extreme or invalid inputs gracefully.
    How it accesses the array: Tests empty arrays, zero counts, and invalid offsets.
    """
    # Test with empty array
    result = array_manager.get_array_by_offset(0, 10, False)
    assert len(result) == 0
    result = array_manager.get_array_by_offset(0, 10, True)
    assert len(result) == 0
    
    # Add test addresses
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test with count = 0
    result = array_manager.get_array_by_offset(0, 0, False)
    assert len(result) == 0
    result = array_manager.get_array_by_offset(4, 0, True)
    assert len(result) == 0
    
    # Test with offset >= length for reverse = False
    result = array_manager.get_array_by_offset(5, 10, False)
    assert len(result) == 0
    
    # Test with offset >= length for reverse = True (adjusts to last index)
    result = array_manager.get_array_by_offset(10, 10, True)
    assert len(result) == 5  # Fetches from index 4 to 0
    for i, addr in enumerate(reversed(test_addresses)):
        assert result[i] == addr

def test_get_array_by_offset_mimic_page_based(array_manager, test_addresses):
    """Test mimicking page-based pagination with get_array_by_offset
    
    Description: Demonstrates replicating page-based pagination for oldest-first and newest-first.
    How it accesses the array: Calculates offset and count based on page number and size.
    """
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Mimic get_array_slice (oldest first)
    page_size = 2
    page = 0
    offset = page * page_size
    result = array_manager.get_array_by_offset(offset, page_size, False)
    assert len(result) == 2
    assert result[0] == test_addresses[0]
    assert result[1] == test_addresses[1]
    
    # Mimic get_array_slice_reverse (newest first)
    array_length = len(test_addresses)
    page = 0
    start = array_length - 1 - (page * page_size)
    items = min(page_size, start + 1)
    result = array_manager.get_array_by_offset(start, items, True)
    assert len(result) == 2
    assert result[0] == test_addresses[4]
    assert result[1] == test_addresses[3]

def test_get_array_by_offset_large_array(array_manager, many_addresses):
    """Test get_array_by_offset with a large array (over 50 items)
    
    Description: Ensures correct behavior with large arrays, including capping at 100 items.
    How it accesses the array: Tests fetching large slices and verifies the cap.
    """
    for addr in many_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Fetch a slice larger than 100 items (should be capped at 100)
    result = array_manager.get_array_by_offset(0, 150, False)
    assert len(result) == 60
    for i in range(len(result)):
        assert result[i] == many_addresses[i]
    
    # Fetch exactly 100 items
    result = array_manager.get_array_by_offset(0, 100, False)
    assert len(result) == 60
    for i in range(len(result)):
        assert result[i] == many_addresses[i]
    
    # Fetch fewer than 100 items
    result = array_manager.get_array_by_offset(50, 10, False)
    assert len(result) == 10
    for i in range(len(result)):
        assert result[i] == many_addresses[50 + i]
    
    # Reverse pagination with large array
    result = array_manager.get_array_by_offset(59, 20, True)
    assert len(result) == 20
    for i in range(len(result)):
        assert result[i] == many_addresses[59 - i]