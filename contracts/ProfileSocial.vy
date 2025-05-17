# @version 0.4.1

# ProfileSocial Contract
# Handles social features (liked profiles, linked profiles) for a Profile

PAGE_SIZE: constant(uint256) = 20
MAX_ITEMS: constant(uint256) = 10**8

owner: public(address)
profile: public(address)  # The address of the profile this social contract belongs to
likedProfiles: public(DynArray[address, MAX_ITEMS])
likedProfileCount: public(uint256)
linkedProfiles: public(DynArray[address, MAX_ITEMS])
linkedProfileCount: public(uint256)
tags: public(DynArray[address, MAX_ITEMS])
tagCount: public(uint256)

@external
def initialize(_owner: address, _profile: address):
    """
    @notice Initialize the ProfileSocial contract with the owner and profile addresses
    @param _owner The address to set as the owner
    @param _profile The address of the linked Profile contract
    """
    assert self.owner == empty(address), "Already initialized"
    assert _profile != empty(address), "Profile address cannot be empty"
    self.owner = _owner
    self.profile = _profile
    self.likedProfileCount = 0
    self.linkedProfileCount = 0

@external
def addLikedProfile(_profile: address):
    """
    @notice Add a profile to the liked profiles list
    @param _profile The address of the profile to like
    """
    assert msg.sender == self.owner, "Only owner can add liked profile"
    assert _profile not in self.likedProfiles, "Profile already liked"
    self.likedProfiles.append(_profile)
    self.likedProfileCount += 1

@external
def removeLikedProfile(_profile: address):
    """
    @notice Remove a profile from the liked profiles list
    @param _profile The address of the profile to remove
    """
    assert msg.sender == self.owner, "Only owner can remove liked profile"
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.likedProfiles), bound=1000):
        if self.likedProfiles[i] == _profile:
            index = i
            found = True
            break
    assert found, "Profile not found"
    if index < len(self.likedProfiles) - 1:
        last_item: address = self.likedProfiles[len(self.likedProfiles) - 1]
        self.likedProfiles[index] = last_item
    self.likedProfiles.pop()
    self.likedProfileCount -= 1

@view
@external
def getLikedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    """
    @notice Get a paginated list of liked profiles
    @param _page The page number
    @param _page_size The number of items per page
    @return A list of liked profile addresses
    """
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.likedProfiles)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.likedProfiles[start + i])
    return result

@view
@external
def getRecentLikedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    """
    @notice Get a paginated list of the most recent liked profiles
    @param _page The page number
    @param _page_size The number of items per page
    @return A list of liked profile addresses
    """
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.likedProfiles)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.likedProfiles[start - i])
    return result

@external
def linkProfile(_profile: address):
    """
    @notice Link another profile to this profile
    @param _profile The address of the profile to link
    """
    assert msg.sender == self.owner, "Only owner can add linked profile"
    assert _profile not in self.linkedProfiles, "Profile already linked"
    self.linkedProfiles.append(_profile)
    self.linkedProfileCount += 1

@external
def removeLinkedProfile(_profile: address):
    """
    @notice Remove a linked profile
    @param _profile The address of the profile to remove
    """
    assert msg.sender == self.owner, "Only owner can remove linked profile"
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.linkedProfiles), bound=1000):
        if self.linkedProfiles[i] == _profile:
            index = i
            found = True
            break
    assert found, "Linked profile not found"
    if index < len(self.linkedProfiles) - 1:
        last_item: address = self.linkedProfiles[len(self.linkedProfiles) - 1]
        self.linkedProfiles[index] = last_item
    self.linkedProfiles.pop()
    self.linkedProfileCount -= 1

@view
@external
def getLinkedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    """
    @notice Get a paginated list of linked profiles
    @param _page The page number
    @param _page_size The number of items per page
    @return A list of linked profile addresses
    """
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.linkedProfiles)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.linkedProfiles[start + i])
    return result

@view
@external
def getRecentLinkedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    """
    @notice Get a paginated list of the most recent linked profiles
    @param _page The page number
    @param _page_size The number of items per page
    @return A list of linked profile addresses
    """
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.linkedProfiles)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.linkedProfiles[start - i])
    return result

# @external
# def addTag(_art_piece_address: address):
#     self.tags.append(_art_piece_address)
#     self.tagCount += 1
    
