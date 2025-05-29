# @version 0.4.1

# ArtSales1155: Handles ERC1155 sales and mappings for a single Profile
# This contract is forever tied to a Profile (profileAddress)
# Direct mutation is allowed by the owner (set at initialization)
# All mutating methods require msg.sender == self.owner

profileAddress: public(address)
owner: public(address)
artEdition1155Template: public(address)  # Template for creating ArtEdition1155 contracts
initialized: public(bool)  # Flag to track initialization for minimal proxy pattern

# Artist ERC1155s for sale
artistErc1155sToSell: public(DynArray[address, 10000000])
artistErc1155sToSellCount: public(uint256)
artistPieceToErc1155Map: public(HashMap[address, address])
artistProceedsAddress: public(address)

# Collector ERC1155s
collectorErc1155s: public(DynArray[address, 10000000])
collectorErc1155Count: public(uint256)

# Events (placeholders)
event ERC1155Added: erc1155: address
# ... (add more as needed)

# Interface for ProfileFactoryAndRegistry
interface ProfileFactoryAndRegistry:
    def artEdition1155Template() -> address: view

# Interface for ArtEdition1155
interface ArtEdition1155:
    def initialize(_art_sales_1155: address, _art_piece: address, _name: String[100], _symbol: String[10], _base_uri: String[256]): nonpayable
    def createEdition(_mint_price: uint256, _max_supply: uint256, _royalty_percent: uint256) -> uint256: nonpayable

# Interface for ArtPiece
interface ArtPiece:
    def getOwner() -> address: view
    def getArtist() -> address: view
    def getTitle() -> String[100]: view

@deploy
def __init__():
    pass

@external
def initialize(_profile_address: address, _owner: address, _profile_factory_and_registry: address):
    assert not self.initialized, "Already initialized"
    assert _profile_address != empty(address), "Profile address required"
    assert _owner != empty(address), "Owner address required"
    assert _profile_factory_and_registry != empty(address), "ProfileFactoryAndRegistry address required"
    
    self.initialized = True
    self.profileAddress = _profile_address
    self.owner = _owner
    self.artistProceedsAddress = _profile_address
    self.artistErc1155sToSellCount = 0
    self.collectorErc1155Count = 0
    
    # Get the ArtEdition1155 template from ProfileFactoryAndRegistry
    factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(_profile_factory_and_registry)
    self.artEdition1155Template = staticcall factory.artEdition1155Template()

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
    self.artistPieceToErc1155Map[_commission] = _erc1155

@external
def removeMapCommissionToMintErc1155(_commission: address):
    """
    Remove a commission to ERC1155 mapping. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    self.artistPieceToErc1155Map[_commission] = empty(address)

@view
@external
def getMapCommissionToMintErc1155(_commission: address) -> address:
    return self.artistPieceToErc1155Map[_commission]

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

@external
def createEditionFromArtPiece(
    _art_piece: address,
    _edition_name: String[100],
    _edition_symbol: String[10],
    _base_uri: String[256],
    _mint_price: uint256,
    _max_supply: uint256,
    _royalty_percent: uint256
) -> address:
    """
    Create an ERC1155 edition from an art piece. Only the owner or profile can call.
    """
    assert msg.sender == self.owner or msg.sender == self.profileAddress, "Only owner or profile can call"
    assert self.artEdition1155Template != empty(address), "ArtEdition1155 template not set"
    assert _art_piece != empty(address), "Invalid art piece address"
    
    # Check that this art piece doesn't already have an edition
    assert self.artistPieceToErc1155Map[_art_piece] == empty(address), "Art piece already has an edition"
    
    # Verify the caller owns the art piece
    art_piece: ArtPiece = ArtPiece(_art_piece)
    art_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    assert art_owner == self.owner or art_artist == self.owner, "Must own or be artist of the art piece"
    
    # Create the ArtEdition1155 contract
    edition_contract: address = create_minimal_proxy_to(self.artEdition1155Template, revert_on_failure=True)
    edition: ArtEdition1155 = ArtEdition1155(edition_contract)
    
    # Initialize the edition contract
    extcall edition.initialize(self, _art_piece, _edition_name, _edition_symbol, _base_uri)
    
    # Create the first edition with the specified parameters
    extcall edition.createEdition(_mint_price, _max_supply, _royalty_percent)
    
    # Add to artist's ERC1155s for sale
    self.artistErc1155sToSell.append(edition_contract)
    self.artistErc1155sToSellCount += 1
    
    # Map the art piece to this edition
    self.artistPieceToErc1155Map[_art_piece] = edition_contract
    
    log ERC1155Added(erc1155=edition_contract)
    return edition_contract

@view
@external
def hasEditions(_art_piece: address) -> bool:
    """
    Check if an art piece has any ERC1155 editions
    """
    return self.artistPieceToErc1155Map[_art_piece] != empty(address)
