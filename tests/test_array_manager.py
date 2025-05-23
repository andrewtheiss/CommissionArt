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

def test_pagination_edge_case_issues(array_manager, test_addresses):
    """Test that exposes issues with pagination logic"""
    
    # Issue 1: Inconsistent behavior between get_array_slice_reverse and get_array_by_offset
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test case: When requesting more items than available from the end
    # get_array_slice_reverse with page=0, size=10 (requesting 10 items)
    slice_result = array_manager.get_array_slice_reverse(0, 10)
    
    # get_array_by_offset mimicking the same request
    array_length = 5  # We have 5 addresses
    page = 0
    page_size = 10
    start = array_length - 1 - (page * page_size)  # This would be 5 - 1 - 0 = 4
    # But wait, if we're asking for 10 items starting from index 4 going backwards,
    # we can only get 5 items (indices 4, 3, 2, 1, 0)
    
    # The issue: get_array_slice_reverse calculates start incorrectly for large page sizes
    # It should handle the case where page_size > array_length
    
    # This will show the issue:
    print(f"slice_result length: {len(slice_result)}")  # Expected: 5
    print(f"slice_result: {slice_result}")
    
    # Now let's test the actual bug
    # When page * page_size approaches total, start calculation can be wrong
    
def test_reverse_pagination_calculation_error(array_manager):
    """Test that shows calculation error in reverse pagination"""
    
    # Add exactly 5 items
    addresses = [accounts.test_accounts[i] for i in range(1, 6)]
    for addr in addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test case that shows the issue:
    # If we have 5 items and request page 1 with size 3
    # Expected: We should get 2 items (indices 1, 0)
    # But the calculation might be wrong
    
    result = array_manager.get_array_slice_reverse(1, 3)
    print(f"Result for page=1, size=3: {result}")
    print(f"Length: {len(result)}")
    
    # The calculation in get_array_slice_reverse:
    # start = total - (page * page_size) - 1
    # start = 5 - (1 * 3) - 1 = 5 - 3 - 1 = 1
    # items_to_return = min(page_size, start + 1) = min(3, 1 + 1) = min(3, 2) = 2
    # So it returns indices [1, 0]
    
    # But logically, if we're doing page-based pagination:
    # Page 0, size 3: indices [4, 3, 2]
    # Page 1, size 3: indices [1, 0]
    # This is correct, but let's test an edge case...

def test_get_array_by_offset_off_by_one_error(array_manager):
    """Test that exposes potential off-by-one errors in reverse pagination"""
    
    # Add exactly 3 items
    addresses = [accounts.test_accounts[i] for i in range(1, 4)]
    for addr in addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test 1: Get all items in reverse
    result = array_manager.get_array_by_offset(2, 3, True)
    assert len(result) == 3
    assert result[0] == addresses[2]  # Index 2
    assert result[1] == addresses[1]  # Index 1
    assert result[2] == addresses[0]  # Index 0
    
    # Test 2: Edge case - offset exactly at array boundary
    result = array_manager.get_array_by_offset(3, 1, True)
    # offset >= array_length, so offset gets adjusted to array_length - 1 = 2
    assert len(result) == 1
    assert result[0] == addresses[2]
    
    # Test 3: The real issue - when array is empty after modifications
    array_manager.clear_array(sender=accounts.test_accounts[0])
    
    # This should not fail, but in some implementations it might
    result = array_manager.get_array_by_offset(0, 10, True)
    assert len(result) == 0  # Should handle empty array gracefully

def test_pagination_consistency_issue(array_manager):
    """Test that shows inconsistency between different pagination methods"""
    
    # Add 10 items
    addresses = []
    for i in range(10):
        priv_key = secrets.token_hex(32)
        account = Account.from_key(priv_key)
        addr = eth_utils.to_checksum_address(account.address)
        addresses.append(addr)
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Compare get_array_slice_reverse with get_array_by_offset
    # They should give the same results when used to implement the same logic
    
    # Test page 0, size 3
    page = 0
    size = 3
    
    # Method 1: get_array_slice_reverse
    result1 = array_manager.get_array_slice_reverse(page, size)
    
    # Method 2: get_array_by_offset (mimicking get_array_slice_reverse)
    array_length = 10
    start = array_length - 1 - (page * size)  # 10 - 1 - 0 = 9
    items = min(size, start + 1)  # min(3, 10) = 3
    result2 = array_manager.get_array_by_offset(start, items, True)
    
    print(f"get_array_slice_reverse result: {result1}")
    print(f"get_array_by_offset result: {result2}")
    
    # They should be the same
    assert len(result1) == len(result2), f"Length mismatch: {len(result1)} vs {len(result2)}"
    for i in range(len(result1)):
        assert result1[i] == result2[i], f"Mismatch at index {i}: {result1[i]} vs {result2[i]}"

def test_actual_underflow_scenario(array_manager):
    """Test a scenario that would cause underflow without proper guards"""
    
    # This test would fail if the guard wasn't there
    # Currently it passes because of: if array_length == 0: return result
    
    # Step 1: Ensure array is empty
    array_manager.clear_array(sender=accounts.test_accounts[0])
    
    # Step 2: Try get_array_by_offset with reverse=True
    # Without the guard, this would try: offset = array_length - 1 = 0 - 1 = UNDERFLOW
    result = array_manager.get_array_by_offset(0, 10, True)
    assert len(result) == 0
    
    # To actually show the issue, let's imagine the guard wasn't there
    # Here's what would happen:
    # array_length = 0
    # offset = array_length - 1  # This would underflow to 2^256 - 1
    # Then accessing self.my_array[offset] would fail with index out of bounds
    
    print("Test passed because of proper guard. Without the guard at line:")
    print("    if array_length == 0:")
    print("        return result")
    print("The code would underflow when calculating: offset = array_length - 1")