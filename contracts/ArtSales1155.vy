# @version 0.4.1

# ArtSales1155: Handles ERC1155 sales and mappings for a single Profile
# This contract is forever tied to a Profile (profileAddress)
# Direct mutation is allowed by the owner (set at initialization)
# All mutating methods require msg.sender == self.owner

profileAddress: public(address)
owner: public(address)

# Artist ERC1155s for sale
artistErc1155sToSell: public(DynArray[address, 1000])
artistErc1155sToSellCount: public(uint256)
artistCommissionToErc1155Map: public(HashMap[address, address])
artistProceedsAddress: public(address)

# Collector ERC1155s
collectorErc1155s: public(DynArray[address, 1000])
collectorErc1155Count: public(uint256)

# Events (placeholders)
event ERC1155Added: erc1155: address
# ... (add more as needed)

@deploy
def __init__(_profile_address: address, _owner: address):
    assert _profile_address != empty(address), "Profile address required"
    assert _owner != empty(address), "Owner address required"
    self.profileAddress = _profile_address
    self.owner = _owner
    self.artistProceedsAddress = _profile_address
    self.artistErc1155sToSellCount = 0
    self.collectorErc1155Count = 0

# Artist ERC1155s
@external
def addAdditionalMintErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can call"
    assert _erc1155 not in self.artistErc1155sToSell, "ERC1155 already added"
    self.artistErc1155sToSell.append(_erc1155)
    self.artistErc1155sToSellCount += 1
    log ERC1155Added(erc1155=_erc1155)

@external
def removeAdditionalMintErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can call"
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.artistErc1155sToSell), bound=1000):
        if self.artistErc1155sToSell[i] == _erc1155:
            index = i
            found = True
            break
    assert found, "ERC1155 not found"
    if index < len(self.artistErc1155sToSell) - 1:
        last_item: address = self.artistErc1155sToSell[len(self.artistErc1155sToSell) - 1]
        self.artistErc1155sToSell[index] = last_item
    self.artistErc1155sToSell.pop()
    self.artistErc1155sToSellCount -= 1

@view
@external
def getAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.artistErc1155sToSell)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.artistErc1155sToSell[start + i])
    return result

@view
@external
def getRecentAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.artistErc1155sToSell)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.artistErc1155sToSell[start - i])
    return result

# Map Commission to Mint ERC1155
@external
def mapCommissionToMintErc1155(_commission: address, _erc1155: address):
    """
    Map a commission to an ERC1155. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    self.artistCommissionToErc1155Map[_commission] = _erc1155

@external
def removeMapCommissionToMintErc1155(_commission: address):
    """
    Remove a commission to ERC1155 mapping. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    self.artistCommissionToErc1155Map[_commission] = empty(address)

@view
@external
def getMapCommissionToMintErc1155(_commission: address) -> address:
    return self.artistCommissionToErc1155Map[_commission]

# Collector ERC1155s
@external
def addCollectorErc1155(_erc1155: address):
    """
    Add an ERC1155 to the collector list. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    assert _erc1155 not in self.collectorErc1155s, "ERC1155 already added"
    self.collectorErc1155s.append(_erc1155)
    self.collectorErc1155Count += 1

@external
def removeCollectorErc1155(_erc1155: address):
    """
    Remove an ERC1155 from the collector list. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.collectorErc1155s), bound=1000):
        if self.collectorErc1155s[i] == _erc1155:
            index = i
            found = True
            break
    assert found, "ERC1155 not found"
    if index < len(self.collectorErc1155s) - 1:
        last_item: address = self.collectorErc1155s[len(self.collectorErc1155s) - 1]
        self.collectorErc1155s[index] = last_item
    self.collectorErc1155s.pop()
    self.collectorErc1155Count -= 1

@view
@external
def getCollectorErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.collectorErc1155s)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.collectorErc1155s[start + i])
    return result

@view
@external
def getRecentCollectorErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.collectorErc1155s)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.collectorErc1155s[start - i])
    return result

@view
@external
def getLatestCollectorErc1155s() -> DynArray[address, 5]:
    result: DynArray[address, 5] = []
    if self.collectorErc1155Count == 0:
        return result
    items_to_return: uint256 = min(5, self.collectorErc1155Count)
    for i: uint256 in range(0, items_to_return, bound=5):
        if i < self.collectorErc1155Count:
            idx: uint256 = self.collectorErc1155Count - 1 - i
            result.append(self.collectorErc1155s[idx])
    return result

@view
@external
def isCollectorErc1155(_erc1155: address) -> bool:
    for i: uint256 in range(0, len(self.collectorErc1155s), bound=1000):
        if self.collectorErc1155s[i] == _erc1155:
            return True
    return False

@external
def addArtistErc1155ToSell(_erc1155: address):
    """
    Add an ERC1155 to the artist's for-sale list. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    assert _erc1155 not in self.artistErc1155sToSell, "ERC1155 already added"
    self.artistErc1155sToSell.append(_erc1155)
    self.artistErc1155sToSellCount += 1
    log ERC1155Added(erc1155=_erc1155)

@external
def removeArtistErc1155ToSell(_erc1155: address):
    """
    Remove an ERC1155 from the artist's for-sale list. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.artistErc1155sToSell), bound=1000):
        if self.artistErc1155sToSell[i] == _erc1155:
            index = i
            found = True
            break
    assert found, "ERC1155 not found"
    if index < len(self.artistErc1155sToSell) - 1:
        last_item: address = self.artistErc1155sToSell[len(self.artistErc1155sToSell) - 1]
        self.artistErc1155sToSell[index] = last_item
    self.artistErc1155sToSell.pop()
    self.artistErc1155sToSellCount -= 1

@external
def addMyCommission(_commission: address):
    """
    Add a commission to the artist's commission list. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    # ... rest of logic ...

@external
def removeMyCommission(_commission: address):
    """
    Remove a commission from the artist's commission list. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    # ... rest of logic ...

@external
def setArtistProceedsAddress(_proceeds_address: address):
    """
    Set the proceeds address for this artist's sales. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can set proceeds address"
    assert _proceeds_address != empty(address), "Invalid proceeds address"
    self.artistProceedsAddress = _proceeds_address

@view
@external
def getArtistProceedsAddress() -> address:
    """
    Get the current proceeds address for this artist's sales.
    """
    return self.artistProceedsAddress
