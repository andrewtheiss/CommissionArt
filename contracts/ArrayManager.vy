# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

PAGE_SIZE: constant(uint256) = 20
MAX_ITEMS: constant(uint256) = 100000

my_array: DynArray[address, 100000]

# Add an item to the dynamic array
@external
def add_to_array(_item: address):
    assert _item not in self.my_array, "Item already exists"
    self.my_array.append(_item)

# Remove an item from the dynamic array by swapping with the last element
@external
def remove_from_array(_item: address):
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.my_array), bound=1000):
        if self.my_array[i] == _item:
            index = i
            found = True
            break
    assert found, "Item not found"
    last_item: address = self.my_array[len(self.my_array) - 1]
    self.my_array[index] = last_item
    self.my_array.pop()

# Get a paginated slice of the dynamic array
@view
@external
def get_array_slice(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    total: uint256 = len(self.my_array)
    start: uint256 = _page * _page_size
    if start >= total:
        return result
    end: uint256 = start + _page_size
    if end > total:
        end = total
    # Cap at 100 to match return type
    max_return: uint256 = min(end - start, 100)
    for i: uint256 in range(start, start + max_return, bound=100):
        result.append(self.my_array[i])
    return result

# Get a paginated slice in reverse order (newest first)
@view
@external
def get_array_slice_reverse(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    total: uint256 = len(self.my_array)
    if total == 0 or _page * _page_size >= total:
        return result
    start: uint256 = total - (_page * _page_size) - 1
    items_to_return: uint256 = min(_page_size, start + 1)
    items_to_return = min(items_to_return, 100)  # Cap at 100
    for i: uint256 in range(0, items_to_return, bound=100):
        idx: uint256 = start - i
        if idx < total:
            result.append(self.my_array[idx])
    return result

# Check if an item exists in the array
@view
@external
def contains(_item: address) -> bool:
    return _item in self.my_array

# Get the length of the array
@view
@external
def get_length() -> uint256:
    return len(self.my_array)

# Get an element at a specific index
@view
@external
def get_at(_index: uint256) -> address:
    assert _index < len(self.my_array), "Index out of bounds"
    return self.my_array[_index]

# Set an element at a specific index
@external
def set_at(_index: uint256, _item: address):
    assert _index < len(self.my_array), "Index out of bounds"
    self.my_array[_index] = _item

# Clear the entire array
@external
def clear_array():
    self.my_array = []

# Remove an item from a dynamic array by swapping with the last element
@internal
def _removeFromArray(_array: DynArray[address, MAX_ITEMS], _item: address):
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(_array), bound=1000):
        if _array[i] == _item:
            index = i
            found = True
            break
    assert found, "Item not found"
    lastItem: address = _array[len(_array) - 1]
    _array[index] = lastItem
    _array.pop()

@view
@external
def get_array_by_offset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 100]:
    """
    @notice Returns a paginated list of items from the array using offset-based pagination.
    @dev This function supports fetching items from either the front or back of the array:
         - **Front Pagination (reverse = False)**: Fetches `_count` items starting from `_offset` in stored order (ascending indices).
         - **Back Pagination (reverse = True)**: Fetches `_count` items starting from `_offset` and moving backwards (descending indices).
         This allows flexible pagination strategies, including mimicking page-based pagination as follows:

         **To Mimic Page-Based Pagination:**
         - **For oldest first (ascending order):**
           - Set `_offset = _page * _page_size`
           - Set `_count = _page_size`
           - Set `reverse = False`
           - Example: Page 0, size 10 → `_offset = 0`, `_count = 10`, `reverse = False` (indices 0 to 9)
           - Example: Page 1, size 10 → `_offset = 10`, `_count = 10`, `reverse = False` (indices 10 to 19)
         - **For newest first (descending order):**
           - Calculate `start = array_length - 1 - (_page * _page_size)`
           - Calculate `items = min(_page_size, start + 1)`
           - Set `_offset = start`
           - Set `_count = items`
           - Set `reverse = True`
           - Example: Array length 15, page 0, size 10 → `_offset = 14`, `_count = 10`, `reverse = True` (indices 14 to 5)
           - Example: Array length 15, page 1, size 10 → `_offset = 4`, `_count = 5`, `reverse = True` (indices 4 to 0)

    @param _offset The starting index in the `my_array`.
                   - If `reverse = False`: Index from the start (0-based).
                   - If `reverse = True`: Index from which to start moving backwards.
    @param _count The number of items to return (capped at 100).
    @param reverse Boolean flag to control fetch direction:
                   - `False`: Forward from `_offset` (ascending).
                   - `True`: Backward from `_offset` (descending).
    @return A list of up to 100 addresses from the array.
    """
    result: DynArray[address, 100] = []
    offset: uint256 = _offset
    array_length: uint256 = len(self.my_array)
    if array_length == 0:
        return result

    if not reverse:
        # Front pagination: Fetch from offset forward
        if offset >= array_length:
            return result
        available_items: uint256 = array_length - offset
        count: uint256 = min(min(_count, available_items), 100)
        for i: uint256 in range(0, count, bound=100):
            result.append(self.my_array[offset + i])
    else:
        # Back pagination: Fetch from offset backward
        if offset >= array_length:
            offset = array_length - 1
        start: uint256 = offset
        available_items: uint256 = start + 1
        count: uint256 = min(min(_count, available_items), 100)
        for i: uint256 in range(0, count, bound=100):
            index: uint256 = start - i
            result.append(self.my_array[index])

    return result