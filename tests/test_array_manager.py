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

def test_initial_state(array_manager):
    """Test initial state of the contract"""
    assert array_manager.get_length() == 0

def test_add_to_array(array_manager, test_addresses):
    """Test adding items to the array"""
    # Add an address
    array_manager.add_to_array(test_addresses[0], sender=accounts.test_accounts[0])
    assert array_manager.contains(test_addresses[0])
    assert array_manager.get_length() == 1
    
    # Add multiple addresses
    array_manager.add_to_array(test_addresses[1], sender=accounts.test_accounts[0])
    array_manager.add_to_array(test_addresses[2], sender=accounts.test_accounts[0])
    assert array_manager.get_length() == 3
    
    # Test duplicate prevention
    with pytest.raises(Exception):
        array_manager.add_to_array(test_addresses[0], sender=accounts.test_accounts[0])

def test_remove_from_array(array_manager, test_addresses):
    """Test removing items from the array"""
    # Add multiple addresses
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    initial_length = array_manager.get_length()
    
    # Remove first item
    array_manager.remove_from_array(test_addresses[0], sender=accounts.test_accounts[0])
    assert not array_manager.contains(test_addresses[0])
    assert array_manager.get_length() == initial_length - 1
    
    # Remove middle item
    array_manager.remove_from_array(test_addresses[2], sender=accounts.test_accounts[0])
    assert not array_manager.contains(test_addresses[2])
    assert array_manager.get_length() == initial_length - 2
    
    # Remove last item
    array_manager.remove_from_array(test_addresses[4], sender=accounts.test_accounts[0])
    assert not array_manager.contains(test_addresses[4])
    assert array_manager.get_length() == initial_length - 3
    
    # Try to remove non-existent item
    with pytest.raises(Exception):
        array_manager.remove_from_array(test_addresses[0], sender=accounts.test_accounts[0])

def test_contains(array_manager, test_addresses):
    """Test the contains method"""
    # Empty array
    assert not array_manager.contains(test_addresses[0])
    
    # Add and check
    array_manager.add_to_array(test_addresses[0], sender=accounts.test_accounts[0])
    assert array_manager.contains(test_addresses[0])
    assert not array_manager.contains(test_addresses[1])
    
    # Remove and check
    array_manager.remove_from_array(test_addresses[0], sender=accounts.test_accounts[0])
    assert not array_manager.contains(test_addresses[0])

def test_get_length(array_manager, test_addresses):
    """Test the get_length method"""
    # Empty array
    assert array_manager.get_length() == 0
    
    # Add items and check length
    for i, addr in enumerate(test_addresses, 1):
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
        assert array_manager.get_length() == i
    
    # Remove items and check length
    for i, addr in enumerate(test_addresses):
        array_manager.remove_from_array(addr, sender=accounts.test_accounts[0])
        assert array_manager.get_length() == len(test_addresses) - i - 1

def test_get_at(array_manager, test_addresses):
    """Test the get_at method"""
    # Add items
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Check all indices
    for i, addr in enumerate(test_addresses):
        assert array_manager.get_at(i) == addr
    
    # Test out of bounds
    with pytest.raises(Exception):
        array_manager.get_at(len(test_addresses), sender=accounts.test_accounts[0])

def test_set_at(array_manager, test_addresses):
    """Test the set_at method"""
    # Add items
    for addr in test_addresses[:3]:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Set items at different positions
    array_manager.set_at(0, test_addresses[3], sender=accounts.test_accounts[0])
    array_manager.set_at(2, test_addresses[4], sender=accounts.test_accounts[0])
    
    # Check items were set correctly
    assert array_manager.get_at(0) == test_addresses[3]
    assert array_manager.get_at(1) == test_addresses[1]  # Unchanged
    assert array_manager.get_at(2) == test_addresses[4]
    
    # Test length unchanged
    assert array_manager.get_length() == 3
    
    # Test out of bounds
    with pytest.raises(Exception):
        array_manager.set_at(3, test_addresses[0], sender=accounts.test_accounts[0])

def test_clear_array(array_manager, test_addresses):
    """Test the clear_array method"""
    # Add items
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Verify items exist
    assert array_manager.get_length() == len(test_addresses)
    
    # Clear array
    array_manager.clear_array(sender=accounts.test_accounts[0])
    
    # Verify array is empty
    assert array_manager.get_length() == 0
    for addr in test_addresses:
        assert not array_manager.contains(addr)

def test_get_array_slice(array_manager, test_addresses):
    """Test the get_array_slice method"""
    # Add items
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test various page sizes and offsets
    # First page, size 2
    page = array_manager.get_array_slice(0, 2)
    assert len(page) == 2
    assert page[0] == test_addresses[0]
    assert page[1] == test_addresses[1]
    
    # Second page, size 2
    page = array_manager.get_array_slice(1, 2)
    assert len(page) == 2
    assert page[0] == test_addresses[2]
    assert page[1] == test_addresses[3]
    
    # Partial page (end of array)
    page = array_manager.get_array_slice(2, 2)
    assert len(page) == 1
    assert page[0] == test_addresses[4]
    
    # Out of bounds page
    page = array_manager.get_array_slice(10, 2)
    assert len(page) == 0
    
    # Entire array
    page = array_manager.get_array_slice(0, 10)
    assert len(page) == len(test_addresses)
    for i, addr in enumerate(test_addresses):
        assert page[i] == addr

def test_get_array_slice_reverse(array_manager, test_addresses):
    """Test the get_array_slice_reverse method"""
    # Add items
    for addr in test_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Test various page sizes and offsets
    # First page (newest first), size 2
    page = array_manager.get_array_slice_reverse(0, 2)
    assert len(page) == 2
    assert page[0] == test_addresses[4]
    assert page[1] == test_addresses[3]
    
    # Second page, size 2
    page = array_manager.get_array_slice_reverse(1, 2)
    assert len(page) == 2
    assert page[0] == test_addresses[2]
    assert page[1] == test_addresses[1]
    
    # Partial page (start of array)
    page = array_manager.get_array_slice_reverse(2, 2)
    assert len(page) == 1
    assert page[0] == test_addresses[0]
    
    # Out of bounds page
    page = array_manager.get_array_slice_reverse(10, 2)
    assert len(page) == 0

def test_large_array(array_manager, many_addresses):
    """Test with over 50 addresses"""
    # Add over 50 addresses
    for addr in many_addresses:
        array_manager.add_to_array(addr, sender=accounts.test_accounts[0])
    
    # Verify all addresses were added
    assert array_manager.get_length() == len(many_addresses)
    
    # Test contains for all addresses
    for addr in many_addresses:
        assert array_manager.contains(addr)
    
    # Test pagination with large array
    # First page
    page_size = 10
    page = array_manager.get_array_slice(0, page_size)
    assert len(page) == page_size
    for i in range(page_size):
        assert page[i] == many_addresses[i]
    
    # Middle page
    page = array_manager.get_array_slice(3, page_size)
    assert len(page) == page_size
    for i in range(page_size):
        assert page[i] == many_addresses[30 + i]
    
    # Test reverse pagination
    page = array_manager.get_array_slice_reverse(0, page_size)
    assert len(page) == page_size
    for i in range(page_size):
        assert page[i] == many_addresses[len(many_addresses) - 1 - i]
    
    # Remove some addresses
    for i in range(0, 30, 3):  # Remove every 3rd address
        array_manager.remove_from_array(many_addresses[i], sender=accounts.test_accounts[0])
    
    # Verify removed addresses
    for i in range(0, 30, 3):
        assert not array_manager.contains(many_addresses[i])
    
    # Clear the array
    array_manager.clear_array(sender=accounts.test_accounts[0])
    assert array_manager.get_length() == 0
