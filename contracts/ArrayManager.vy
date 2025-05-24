# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

## Usage:
"""
getArtPiecesByOffset: Comprehensive Usage Guide
==============================================

This method provides flexible pagination through the art pieces array with both 
forward and reverse traversal options.

Parameters:
    _offset (uint256): Starting position for pagination
    _count (uint256): Number of items to retrieve (max 50)
    reverse (bool): Direction of pagination (False = oldest→newest, True = newest→oldest)

Returns:
    DynArray[address, 50]: List of art piece addresses

FORWARD PAGINATION (reverse=False)
==================================
Traverses from oldest to newest items (index 0 → myArtCount-1)

Example array: [A, B, C, D, E] (5 items, indices 0-4)

Usage examples:
    getArtPiecesByOffset(0, 3, False)  → [A, B, C]    # First 3 items
    getArtPiecesByOffset(2, 2, False)  → [C, D]       # Skip first 2, get next 2
    getArtPiecesByOffset(4, 10, False) → [E]          # Start at index 4, only 1 available
    getArtPiecesByOffset(5, 2, False)  → []           # Offset beyond array bounds
    getArtPiecesByOffset(0, 50, False) → [A, B, C, D, E]  # Get all (limited by array size)

Common patterns:
    - Get first page: getArtPiecesByOffset(0, pageSize, False)
    - Get next page: getArtPiecesByOffset(currentOffset + pageSize, pageSize, False)
    - Get all items: getArtPiecesByOffset(0, 50, False)

REVERSE PAGINATION (reverse=True) - After Fix
=============================================
Traverses from newest to oldest items (index myArtCount-1 → 0)
_offset represents how many items to skip from the END of the array

Example array: [A, B, C, D, E] (5 items, indices 0-4)

Usage examples:
    getArtPiecesByOffset(0, 3, True)  → [E, D, C]     # Last 3 items (newest first)
    getArtPiecesByOffset(1, 2, True)  → [D, C]        # Skip newest, get next 2
    getArtPiecesByOffset(2, 2, True)  → [C, B]        # Skip 2 newest, get next 2
    getArtPiecesByOffset(4, 2, True)  → [A]           # Skip 4 newest, only oldest remains
    getArtPiecesByOffset(5, 2, True)  → []            # Offset beyond array bounds
    getArtPiecesByOffset(0, 50, True) → [E, D, C, B, A]  # All items, newest first

Common patterns:
    - Get latest items: getArtPiecesByOffset(0, pageSize, True)
    - Get previous page: getArtPiecesByOffset(currentOffset + pageSize, pageSize, True)
    - Get N oldest items: getArtPiecesByOffset(myArtCount - N, N, True)

PAGINATION STRATEGIES
====================

1. Standard Forward Pagination (oldest → newest):
   page = 0
   while True:
       items = getArtPiecesByOffset(page * 10, 10, False)
       if len(items) == 0:
           break
       process(items)
       page += 1

2. Reverse Chronological Display (newest → oldest):
   page = 0
   while True:
       items = getArtPiecesByOffset(page * 10, 10, True)
       if len(items) == 0:
           break
       display(items)
       page += 1

3. Get Middle Range:
   # Get items 10-19 (11th through 20th items)
   items = getArtPiecesByOffset(10, 10, False)

4. Get Last N Items:
   # Get last 5 items in chronological order
   items = getArtPiecesByOffset(0, 5, True)
   
5. Check if More Pages Exist:
   items = getArtPiecesByOffset(offset, pageSize, reverse)
   hasMore = len(items) == pageSize  # If full page returned, likely more exist

EDGE CASES
==========
- Empty array: Always returns []
- _count > 50: Limited to 50 items per call
- _offset >= myArtCount: Returns []
- _count = 0: Returns []
- Requesting more items than available: Returns only available items

IMPLEMENTATION NOTES
===================
- Uses DynArray with max size 50 to comply with EVM gas limits
- Efficient O(n) iteration where n = min(_count, 50)
- No array reversal needed - items are selected in correct order
- Safe against out-of-bounds access
"""

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
    @dev Forward pagination: _offset is starting index, _count is number of items
         Reverse pagination: _offset is number of items to skip from end, _count is number of items
    @param _offset For forward: starting index. For reverse: items to skip from end
    @param _count Number of items to return (capped at 100)
    @param reverse Direction: False = forward (oldest first), True = reverse (newest first)
    @return A list of up to 100 addresses from the array
    """
    result: DynArray[address, 100] = []
    array_length: uint256 = len(self.my_array)
    
    # Handle empty array
    if array_length == 0:
        return result
    
    if not reverse:
        # FORWARD PAGINATION: _offset is starting index
        if _offset >= array_length:
            return result  # Offset beyond array bounds
        
        available_items: uint256 = array_length - _offset
        count: uint256 = min(min(_count, available_items), 100)
        
        for i: uint256 in range(0, count, bound=100):
            result.append(self.my_array[_offset + i])
    else:
        # REVERSE PAGINATION: _offset is items to skip from end
        if _offset >= array_length:
            return result  # Skip more items than exist
            
        # Calculate starting index (skip _offset items from the end)
        start_index: uint256 = array_length - 1 - _offset
        available_items: uint256 = start_index + 1  # Items available going backwards
        count: uint256 = min(min(_count, available_items), 100)
        
        for i: uint256 in range(0, count, bound=100):
            index: uint256 = start_index - i
            result.append(self.my_array[index])
    
    return result