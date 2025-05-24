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

def test_get_array_by_offset_back_pagination(array_manager, test_addresses):
    """Test back pagination with get_array_by_offset (reverse = True) - Canonical Semantics
    
    Description: Verifies fetching items using canonical reverse pagination.
    Canonical semantics: _offset = items to skip from end, _count = items to return
    """
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Skip 0 from end, get 2 items → [E, D] (newest first)
    result = array_manager.get_array_by_offset(0, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[4]  # E (newest)
    assert result[1] == test_addresses[3]  # D
    
    # Skip 1 from end, get 2 items → [D, C] 
    result = array_manager.get_array_by_offset(1, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[3]  # D
    assert result[1] == test_addresses[2]  # C
    
    # Skip 3 from end, get 2 items → [B, A]
    result = array_manager.get_array_by_offset(3, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[1]  # B
    assert result[1] == test_addresses[0]  # A
    
    # Skip 4 from end, get 2 items → [A] (only 1 available)
    result = array_manager.get_array_by_offset(4, 2, True)
    assert len(result) == 1
    assert result[0] == test_addresses[0]  # A (oldest)

def test_get_array_by_offset_edge_cases(array_manager, test_addresses):
    """Test edge cases for get_array_by_offset - Canonical Semantics
    
    Description: Ensures the method handles extreme or invalid inputs gracefully.
    Canonical semantics: Forward _offset=start index, Reverse _offset=skip from end
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
    result = array_manager.get_array_by_offset(0, 0, True)
    assert len(result) == 0
    
    # Test with offset >= length for forward pagination
    result = array_manager.get_array_by_offset(5, 10, False)
    assert len(result) == 0
    
    # Test with offset >= length for reverse pagination (skip too many)
    result = array_manager.get_array_by_offset(5, 10, True)
    assert len(result) == 0  # Skip 5 items from 5-item array = nothing left
    
    # Test boundary conditions
    result = array_manager.get_array_by_offset(4, 1, False)  # Last item forward
    assert len(result) == 1
    assert result[0] == test_addresses[4]
    
    result = array_manager.get_array_by_offset(4, 1, True)   # Skip 4, get oldest
    assert len(result) == 1
    assert result[0] == test_addresses[0]

def test_get_array_by_offset_mimic_page_based(array_manager, test_addresses):
    """Test mimicking page-based pagination with get_array_by_offset - Canonical Semantics
    
    Description: Demonstrates how to use canonical semantics for page-based patterns.
    Canonical semantics: Forward uses start index, Reverse uses skip-from-end
    """
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Forward pagination: page-based (oldest first)
    page_size = 2
    page = 0
    offset = page * page_size  # Page 0: offset = 0
    result = array_manager.get_array_by_offset(offset, page_size, False)
    assert len(result) == 2
    assert result[0] == test_addresses[0]  # A
    assert result[1] == test_addresses[1]  # B
    
    # Reverse pagination: newest-first approach
    # To get newest 2 items: skip 0 from end
    result = array_manager.get_array_by_offset(0, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[4]  # E (newest)
    assert result[1] == test_addresses[3]  # D
    
    # To get next 2 newest items: skip 2 from end
    result = array_manager.get_array_by_offset(2, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[2]  # C
    assert result[1] == test_addresses[1]  # B

def test_get_array_by_offset_large_array(array_manager, many_addresses):
    """Test get_array_by_offset with a large array (over 50 items) - Canonical Semantics
    
    Description: Ensures correct behavior with large arrays using canonical semantics.
    Tests the 100-item cap and verifies both forward and reverse pagination work correctly.
    """
    for addr in many_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Forward pagination tests
    # Fetch first 60 items (all of them since we have 60)
    result = array_manager.get_array_by_offset(0, 100, False)
    assert len(result) == 60  # All items
    for i in range(len(result)):
        assert result[i] == many_addresses[i]
    
    # Fetch from middle
    result = array_manager.get_array_by_offset(30, 10, False)
    assert len(result) == 10
    for i in range(len(result)):
        assert result[i] == many_addresses[30 + i]
    
    # Reverse pagination tests
    # Get newest 20 items (skip 0 from end)
    result = array_manager.get_array_by_offset(0, 20, True)
    assert len(result) == 20
    for i in range(len(result)):
        expected_index = 59 - i  # Start from index 59 (newest) and go backwards
        assert result[i] == many_addresses[expected_index]
    
    # Skip 10 newest, get next 15
    result = array_manager.get_array_by_offset(10, 15, True)
    assert len(result) == 15
    for i in range(len(result)):
        expected_index = 49 - i  # Start from index 49 (skip 10 from end) and go backwards
        assert result[i] == many_addresses[expected_index]

def test_pagination_edge_case_issues(array_manager, test_addresses):
    """Diagnostic test - shows how get_array_slice_reverse works vs canonical get_array_by_offset"""
    
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test: Requesting more items than available from the end
    slice_result = array_manager.get_array_slice_reverse(0, 10)  # Page 0, size 10
    canonical_result = array_manager.get_array_by_offset(0, 10, True)  # Skip 0, get 10
    
    print(f"slice_result length: {len(slice_result)}")  # Expected: 5
    print(f"slice_result: {slice_result}")
    print(f"canonical_result length: {len(canonical_result)}")  # Expected: 5
    print(f"canonical_result: {canonical_result}")
    
    # Both should return all 5 items in reverse order
    assert len(slice_result) == 5
    assert len(canonical_result) == 5
    
    # Verify they match
    for i in range(len(slice_result)):
        assert slice_result[i] == canonical_result[i]

def test_reverse_pagination_calculation_error(array_manager):
    """Test specific reverse pagination scenarios - Canonical Semantics"""
    
    # Add exactly 5 items: [A, B, C, D, E]
    addresses = [accounts.test_accounts[i] for i in range(1, 6)]
    for addr in addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test canonical reverse pagination patterns
    
    # Skip 0, get 3 → [E, D, C]
    result = array_manager.get_array_by_offset(0, 3, True)
    assert len(result) == 3
    assert result[0] == addresses[4]  # E
    assert result[1] == addresses[3]  # D
    assert result[2] == addresses[2]  # C
    
    # Skip 3, get 3 → [B, A] (only 2 available)
    result = array_manager.get_array_by_offset(3, 3, True)
    assert len(result) == 2
    assert result[0] == addresses[1]  # B
    assert result[1] == addresses[0]  # A

def test_get_array_by_offset_off_by_one_error(array_manager):
    """Test boundary conditions with get_array_by_offset - Canonical Semantics"""
    
    # Add exactly 3 items: [A, B, C] at indices [0, 1, 2]
    addresses = [accounts.test_accounts[i] for i in range(1, 4)]
    for addr in addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test 1: Get all items in reverse (skip 0, get 3)
    result = array_manager.get_array_by_offset(0, 3, True)
    assert len(result) == 3
    assert result[0] == addresses[2]  # C (newest, index 2)
    assert result[1] == addresses[1]  # B (index 1)
    assert result[2] == addresses[0]  # A (oldest, index 0)
    
    # Test 2: Edge case - skip more than available
    result = array_manager.get_array_by_offset(3, 1, True)
    assert len(result) == 0  # Skip 3 items from 3-item array = nothing left
    
    # Test 3: Skip exactly available-1 
    result = array_manager.get_array_by_offset(2, 2, True)
    assert len(result) == 1  # Skip 2, only 1 left
    assert result[0] == addresses[0]  # A (oldest)
    
    # Test 4: Empty array handling
    array_manager.clear_array(sender=accounts.test_accounts[0])
    result = array_manager.get_array_by_offset(0, 10, True)
    assert len(result) == 0  # Should handle empty array gracefully

def test_pagination_consistency_issue(array_manager):
    """Test consistency between different pagination methods - Canonical Semantics
    
    Shows how get_array_slice_reverse can be replicated using canonical get_array_by_offset
    """
    
    # Add 10 items
    addresses = []
    for i in range(10):
        priv_key = secrets.token_hex(32)
        account = Account.from_key(priv_key)
        addr = eth_utils.to_checksum_address(account.address)
        addresses.append(addr)
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test: get_array_slice_reverse vs canonical get_array_by_offset
    page = 0
    size = 3
    
    # Method 1: get_array_slice_reverse (page-based)
    result1 = array_manager.get_array_slice_reverse(page, size)
    
    # Method 2: get_array_by_offset using canonical semantics
    # To replicate page-based reverse: skip (page * size) from end
    skip_from_end = page * size  # page 0 = skip 0, page 1 = skip 3, etc.
    result2 = array_manager.get_array_by_offset(skip_from_end, size, True)
    
    print(f"get_array_slice_reverse result: {result1}")
    print(f"get_array_by_offset result: {result2}")
    
    # They should be the same when using proper canonical conversion
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

def test_get_latest_several_array_items(array_manager, test_addresses):
    """Test getting the latest items from the array"""
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Get the latest 2 items using get_array_slice_reverse (page-based)
    result = array_manager.get_array_slice_reverse(0, 2)
    assert len(result) == 2
    assert result[0] == test_addresses[4]  # Newest item (last added)
    assert result[1] == test_addresses[3]  # Second newest item
    
    # Alternative: Get latest 2 items using get_array_by_offset (canonical semantics)
    # Skip 0 items from end, get 2 items backwards = get newest 2 items
    result2 = array_manager.get_array_by_offset(0, 2, True)
    assert len(result2) == 2
    assert result2[0] == test_addresses[4]  # Newest item
    assert result2[1] == test_addresses[3]  # Second newest item

def test_canonical_forward_pagination_all_cases(array_manager, test_addresses):
    """Test all forward pagination cases for get_array_by_offset (canonical implementation)"""
    # Array: [A, B, C, D, E] (5 items, indices 0-4)
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Case 1: getArrayByOffset(0, 3, False) → [A, B, C] - First 3 items
    result = array_manager.get_array_by_offset(0, 3, False)
    assert len(result) == 3
    assert result[0] == test_addresses[0]  # A
    assert result[1] == test_addresses[1]  # B
    assert result[2] == test_addresses[2]  # C
    
    # Case 2: getArrayByOffset(2, 2, False) → [C, D] - Skip first 2, get next 2
    result = array_manager.get_array_by_offset(2, 2, False)
    assert len(result) == 2
    assert result[0] == test_addresses[2]  # C
    assert result[1] == test_addresses[3]  # D
    
    # Case 3: getArrayByOffset(4, 10, False) → [E] - Start at index 4, only 1 available
    result = array_manager.get_array_by_offset(4, 10, False)
    assert len(result) == 1
    assert result[0] == test_addresses[4]  # E
    
    # Case 4: getArrayByOffset(5, 2, False) → [] - Offset beyond array bounds
    result = array_manager.get_array_by_offset(5, 2, False)
    assert len(result) == 0
    
    # Case 5: getArrayByOffset(0, 50, False) → [A, B, C, D, E] - Get all items
    result = array_manager.get_array_by_offset(0, 50, False)
    assert len(result) == 5
    assert result[0] == test_addresses[0]  # A
    assert result[1] == test_addresses[1]  # B
    assert result[2] == test_addresses[2]  # C
    assert result[3] == test_addresses[3]  # D
    assert result[4] == test_addresses[4]  # E

def test_canonical_reverse_pagination_all_cases(array_manager, test_addresses):
    """Test all reverse pagination cases for get_array_by_offset (canonical implementation)"""
    # Array: [A, B, C, D, E] (5 items, indices 0-4)
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Case 1: getArrayByOffset(0, 3, True) → [E, D, C] - Last 3 items (newest first)
    result = array_manager.get_array_by_offset(0, 3, True)
    assert len(result) == 3
    assert result[0] == test_addresses[4]  # E (newest)
    assert result[1] == test_addresses[3]  # D
    assert result[2] == test_addresses[2]  # C
    
    # Case 2: getArrayByOffset(1, 2, True) → [D, C] - Skip newest, get next 2
    result = array_manager.get_array_by_offset(1, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[3]  # D
    assert result[1] == test_addresses[2]  # C
    
    # Case 3: getArrayByOffset(2, 2, True) → [C, B] - Skip 2 newest, get next 2
    result = array_manager.get_array_by_offset(2, 2, True)
    assert len(result) == 2
    assert result[0] == test_addresses[2]  # C
    assert result[1] == test_addresses[1]  # B
    
    # Case 4: getArrayByOffset(4, 2, True) → [A] - Skip 4 newest, only oldest remains
    result = array_manager.get_array_by_offset(4, 2, True)
    assert len(result) == 1
    assert result[0] == test_addresses[0]  # A (oldest)
    
    # Case 5: getArrayByOffset(5, 2, True) → [] - Offset beyond array bounds
    result = array_manager.get_array_by_offset(5, 2, True)
    assert len(result) == 0
    
    # Case 6: getArrayByOffset(0, 50, True) → [E, D, C, B, A] - All items, newest first
    result = array_manager.get_array_by_offset(0, 50, True)
    assert len(result) == 5
    assert result[0] == test_addresses[4]  # E (newest)
    assert result[1] == test_addresses[3]  # D
    assert result[2] == test_addresses[2]  # C
    assert result[3] == test_addresses[1]  # B
    assert result[4] == test_addresses[0]  # A (oldest)

def test_canonical_common_pagination_patterns(array_manager, test_addresses):
    """Test common pagination patterns using get_array_by_offset"""
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Pattern 1: Get first page
    page_size = 2
    result = array_manager.get_array_by_offset(0, page_size, False)
    assert len(result) == 2
    assert result[0] == test_addresses[0]
    assert result[1] == test_addresses[1]
    
    # Pattern 2: Get next page  
    current_offset = page_size  # After first page
    result = array_manager.get_array_by_offset(current_offset, page_size, False)
    assert len(result) == 2
    assert result[0] == test_addresses[2]
    assert result[1] == test_addresses[3]
    
    # Pattern 3: Get final page (partial)
    current_offset = 2 * page_size  # After second page
    result = array_manager.get_array_by_offset(current_offset, page_size, False)
    assert len(result) == 1  # Only 1 item left
    assert result[0] == test_addresses[4]
    
    # Pattern 4: Get all items forward
    result = array_manager.get_array_by_offset(0, 50, False)
    assert len(result) == 5
    for i in range(5):
        assert result[i] == test_addresses[i]
    
    # Pattern 5: Get all items reverse (newest first)
    result = array_manager.get_array_by_offset(0, 50, True)
    assert len(result) == 5
    for i in range(5):
        assert result[i] == test_addresses[4 - i]  # Reverse order

def test_canonical_edge_cases(array_manager, test_addresses):
    """Test edge cases for the canonical get_array_by_offset implementation"""
    
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
    result = array_manager.get_array_by_offset(0, 0, True)
    assert len(result) == 0
    
    # Test forward pagination beyond bounds
    result = array_manager.get_array_by_offset(10, 5, False)
    assert len(result) == 0
    
    # Test reverse pagination beyond bounds  
    result = array_manager.get_array_by_offset(10, 5, True)
    assert len(result) == 0
    
    # Test single item requests
    result = array_manager.get_array_by_offset(2, 1, False)
    assert len(result) == 1
    assert result[0] == test_addresses[2]
    
    result = array_manager.get_array_by_offset(2, 1, True)
    assert len(result) == 1
    assert result[0] == test_addresses[2]  # Skip 2 from end (E,D), get C
