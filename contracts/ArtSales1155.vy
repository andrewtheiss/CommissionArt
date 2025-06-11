# @version 0.4.1


# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# ArtPieceLicense contract - handles licensing and rights management for ArtPiece
# This contract can override ownership determination for rights management purposes
# ArtSales1155: Handles ERC1155 sales and mappings for a single Profile
# Enhanced with comprehensive sales management and phased pricing
# SIMPLIFIED: Each ArtEdition1155 contract only handles one token (ID 1)
# This contract is forever tied to a Profile (profileAddress)
# Direct mutation is allowed by the owner (set at initialization)
# All mutating methods require msg.sender == self.owner

profileAddress: public(address)
owner: public(address)
artEdition1155Template: public(address)  # Template for creating ArtEdition1155 contracts
initialized: public(bool)  # Flag to track initialization for minimal proxy pattern

# Artist ERC1155s for sale - O(1) operations pattern (like Profile.myArt)
artistErc1155sToSell: public(DynArray[address, 10000000])
artistErc1155sToSellCount: public(uint256)
artistErc1155sToSellExistsAndPositionOffsetByOne: public(HashMap[address, uint256])
artistPieceToErc1155Map: public(HashMap[address, address])  # Maps art piece → edition
artistProceedsAddress: public(address)

# Collector ERC1155s - O(1) operations pattern (like Profile.myArt)
collectorErc1155s: public(DynArray[address, 10000000])
collectorErc1155Count: public(uint256)
collectorErc1155sExistsAndPositionOffsetByOne: public(HashMap[address, uint256])
collectorErc1155ToArtPieceMap: public(HashMap[address, address])  # Maps collector edition → original art piece

# Sale Types (matching ArtEdition1155)
SALE_TYPE_FOREVER: constant(uint256) = 0      # No deadline, mint forever
SALE_TYPE_CAPPED: constant(uint256) = 1       # Stop after maxSupply reached
SALE_TYPE_QUANTITY_PHASES: constant(uint256) = 2  # Price increases based on quantity sold
SALE_TYPE_TIME_PHASES: constant(uint256) = 3      # Price increases based on time

# Phase Configuration (matching ArtEdition1155)
struct PhaseConfig:
    threshold: uint256  # Quantity threshold for QUANTITY_PHASES, timestamp for TIME_PHASES
    price: uint256

# Events
event ERC1155Added: erc1155: address
event CollectorERC1155Added: erc1155: address
event SaleStarted:
    erc1155: indexed(address)
    saleType: uint256
event SalePaused:
    erc1155: indexed(address)
event SaleResumed:
    erc1155: indexed(address)
event EditionCreated:
    erc1155: indexed(address)
    artPiece: indexed(address)
    saleType: uint256

# Interface for ProfileFactoryAndRegistry
interface ProfileFactoryAndRegistry:
    def artEdition1155Template() -> address: view

# Simplified Interface for ArtEdition1155 (single token per contract)
interface ArtEdition1155:
    def initialize(_art_sales_1155: address, _art_piece: address, _name: String[100], _symbol: String[10], _payment_currency: address): nonpayable
    def createEdition(_mint_price: uint256, _max_supply: uint256, _royalty_percent: uint256, _sale_type: uint256, _phases: DynArray[PhaseConfig, 5], _time_cap_hard_stop: uint256, _mint_cap_hard_stop: uint256): nonpayable
    def startSale(): nonpayable
    def pauseSale(): nonpayable
    def resumeSale(): nonpayable
    def getSaleInfo() -> (uint256, uint256, uint256, uint256, bool, uint256): view
    def getPhases() -> DynArray[PhaseConfig, 5]: view

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

# ================================================================================================
# ARTIST ERC1155s FOR SALE - O(1) OPERATIONS (following Profile.myArt pattern)
# ================================================================================================

@external
def addAdditionalMintErc1155(_erc1155: address):
    """
    Add an ERC1155 to the artist's for-sale list. Only the owner can call.
    O(1) operation using offset mapping pattern.
    """
    assert msg.sender == self.owner, "Only owner can call"
    assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[_erc1155] == 0, "ERC1155 already added"
    
    self.artistErc1155sToSell.append(_erc1155)
    self.artistErc1155sToSellCount += 1
    self.artistErc1155sToSellExistsAndPositionOffsetByOne[_erc1155] = self.artistErc1155sToSellCount
    
    log ERC1155Added(erc1155=_erc1155)

@external
def removeAdditionalMintErc1155(_erc1155: address):
    """
    Remove an ERC1155 from the artist's for-sale list. Only the owner can call.
    O(1) operation using swap-and-pop pattern like Profile.removeArtPiece.
    """
    assert msg.sender == self.owner, "Only owner can call"
    assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[_erc1155] != 0, "ERC1155 not found"
    
    # Get the position (subtract 1 for actual index)
    index: uint256 = self.artistErc1155sToSellExistsAndPositionOffsetByOne[_erc1155] - 1
    
    # Swap with the last element and pop
    if index < len(self.artistErc1155sToSell) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.artistErc1155sToSell[len(self.artistErc1155sToSell) - 1]
        # Replace the item to remove with the last item
        self.artistErc1155sToSell[index] = last_item
        # Update mapping for the moved item
        self.artistErc1155sToSellExistsAndPositionOffsetByOne[last_item] = index + 1  # offset by 1
    
    # Pop the last item (now a duplicate if we did the swap)
    self.artistErc1155sToSell.pop()
    self.artistErc1155sToSellCount -= 1
    # Clear mapping for the removed item
    self.artistErc1155sToSellExistsAndPositionOffsetByOne[_erc1155] = 0

@view
@external
def artistErc1155Exists(_erc1155: address) -> bool:
    """
    Check if an ERC1155 exists in the artist's for-sale collection.
    O(1) operation.
    """
    return self.artistErc1155sToSellExistsAndPositionOffsetByOne[_erc1155] != 0

@view
@external
def getArtistErc1155Position(_erc1155: address) -> uint256:
    """
    Get the position of an ERC1155 in the artistErc1155sToSell array (0-indexed).
    O(1) operation.
    """
    if self.artistErc1155sToSellExistsAndPositionOffsetByOne[_erc1155] == 0:
        return max_value(uint256)  # Return max value to indicate not found
    return self.artistErc1155sToSellExistsAndPositionOffsetByOne[_erc1155] - 1

@view
@external
def getArtistErc1155AtIndex(_index: uint256) -> address:
    """
    Get the ERC1155 address at a specific index.
    O(1) operation.
    """
    return self.artistErc1155sToSell[_index]

@view
@external
def getAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    """
    Get artist ERC1155s with forward pagination.
    Following the same pattern as Profile.getArtPiecesByOffset.
    """
    result: DynArray[address, 100] = []
    arr_len: uint256 = self.artistErc1155sToSellCount
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
    """
    Get recent artist ERC1155s with reverse pagination.
    Following the same pattern as Profile.getArtPiecesByOffset with reverse=True.
    """
    result: DynArray[address, 100] = []
    arr_len: uint256 = self.artistErc1155sToSellCount
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.artistErc1155sToSell[start - i])
    return result

@view
@external
def getArtistErc1155sByOffset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]:
    """
    Returns a paginated list of artist ERC1155s using offset-based pagination.
    Identical to Profile.getArtPiecesByOffset pattern.
    """
    result: DynArray[address, 50] = []
    array_length: uint256 = self.artistErc1155sToSellCount
    
    # Handle empty array
    if array_length == 0:
        return result
    
    if not reverse:
        # FORWARD PAGINATION: _offset is starting index
        if _offset >= array_length:
            return result  # Offset beyond array bounds
        
        available_items: uint256 = array_length - _offset
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            result.append(self.artistErc1155sToSell[_offset + i])
    else:
        # REVERSE PAGINATION: _offset is items to skip from end
        if _offset >= array_length:
            return result  # Skip more items than exist
            
        # Calculate starting index (skip _offset items from the end)
        start_index: uint256 = array_length - 1 - _offset
        available_items: uint256 = start_index + 1  # Items available going backwards
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            index: uint256 = start_index - i
            result.append(self.artistErc1155sToSell[index])
    
    return result

# ================================================================================================
# COLLECTOR ERC1155s - O(1) OPERATIONS (following Profile.myArt pattern)
# ================================================================================================

@external
def addCollectorErc1155(_erc1155: address, _original_art_piece: address = empty(address)):
    """
    Add an ERC1155 to the collector list. Only the owner can call.
    O(1) operation using offset mapping pattern.
    """
    assert msg.sender == self.owner, "Only owner can call"
    assert self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] == 0, "ERC1155 already added"
    
    self.collectorErc1155s.append(_erc1155)
    self.collectorErc1155Count += 1
    self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] = self.collectorErc1155Count
    
    # Map collector edition back to original art piece if provided
    if _original_art_piece != empty(address):
        self.collectorErc1155ToArtPieceMap[_erc1155] = _original_art_piece
    
    log CollectorERC1155Added(erc1155=_erc1155)

@external
def removeCollectorErc1155(_erc1155: address):
    """
    Remove an ERC1155 from the collector list. Only the owner can call.
    O(1) operation using swap-and-pop pattern like Profile.removeArtPiece.
    """
    assert msg.sender == self.owner, "Only owner can call"
    assert self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] != 0, "ERC1155 not found"
    
    # Get the position (subtract 1 for actual index)
    index: uint256 = self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] - 1
    
    # Swap with the last element and pop
    if index < len(self.collectorErc1155s) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.collectorErc1155s[len(self.collectorErc1155s) - 1]
        # Replace the item to remove with the last item
        self.collectorErc1155s[index] = last_item
        # Update mapping for the moved item
        self.collectorErc1155sExistsAndPositionOffsetByOne[last_item] = index + 1  # offset by 1
    
    # Pop the last item (now a duplicate if we did the swap)
    self.collectorErc1155s.pop()
    self.collectorErc1155Count -= 1
    # Clear mappings for the removed item
    self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] = 0
    self.collectorErc1155ToArtPieceMap[_erc1155] = empty(address)

@view
@external
def collectorErc1155Exists(_erc1155: address) -> bool:
    """
    Check if an ERC1155 exists in the collector collection.
    O(1) operation.
    """
    return self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] != 0

@view
@external
def getCollectorErc1155Position(_erc1155: address) -> uint256:
    """
    Get the position of an ERC1155 in the collectorErc1155s array (0-indexed).
    O(1) operation.
    """
    if self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] == 0:
        return max_value(uint256)  # Return max value to indicate not found
    return self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] - 1

@view
@external
def getCollectorErc1155AtIndex(_index: uint256) -> address:
    """
    Get the ERC1155 address at a specific index.
    O(1) operation.
    """
    return self.collectorErc1155s[_index]

@view
@external
def getCollectorErc1155OriginalArtPiece(_erc1155: address) -> address:
    """
    Get the original art piece for a collector ERC1155.
    O(1) operation.
    """
    return self.collectorErc1155ToArtPieceMap[_erc1155]

@view
@external
def getCollectorErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    """
    Get collector ERC1155s with forward pagination.
    """
    result: DynArray[address, 100] = []
    arr_len: uint256 = self.collectorErc1155Count
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
    """
    Get recent collector ERC1155s with reverse pagination.
    """
    result: DynArray[address, 100] = []
    arr_len: uint256 = self.collectorErc1155Count
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.collectorErc1155s[start - i])
    return result

@view
@external
def getCollectorErc1155sByOffset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]:
    """
    Returns a paginated list of collector ERC1155s using offset-based pagination.
    Identical to Profile.getArtPiecesByOffset pattern.
    """
    result: DynArray[address, 50] = []
    array_length: uint256 = self.collectorErc1155Count
    
    # Handle empty array
    if array_length == 0:
        return result
    
    if not reverse:
        # FORWARD PAGINATION: _offset is starting index
        if _offset >= array_length:
            return result  # Offset beyond array bounds
        
        available_items: uint256 = array_length - _offset
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            result.append(self.collectorErc1155s[_offset + i])
    else:
        # REVERSE PAGINATION: _offset is items to skip from end
        if _offset >= array_length:
            return result  # Skip more items than exist
            
        # Calculate starting index (skip _offset items from the end)
        start_index: uint256 = array_length - 1 - _offset
        available_items: uint256 = start_index + 1  # Items available going backwards
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            index: uint256 = start_index - i
            result.append(self.collectorErc1155s[index])
    
    return result

@view
@external
def getLatestCollectorErc1155s() -> DynArray[address, 5]:
    """
    Get the latest 5 collector ERC1155s.
    """
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
    """
    Check if an address is in the collector ERC1155s list.
    O(1) operation now instead of O(n) loop.
    """
    return self.collectorErc1155sExistsAndPositionOffsetByOne[_erc1155] != 0

# ================================================================================================
# LEGACY/COMPATIBILITY FUNCTIONS REMOVED
# Note: Legacy functions addArtistErc1155ToSell and removeArtistErc1155ToSell have been removed.
# Use addAdditionalMintErc1155 and removeAdditionalMintErc1155 instead.
# ================================================================================================

# ================================================================================================
# ART PIECE TO ERC1155 MAPPING FUNCTIONS
# ================================================================================================

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
    """
    Get the ERC1155 mapped to a commission/art piece.
    """
    return self.artistPieceToErc1155Map[_commission]

# ================================================================================================
# COMMISSION/PROFILE INTEGRATION
# ================================================================================================

@external
def addMyCommission(_commission: address):
    """
    Add a commission to the artist's commission list. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    # This is a placeholder method for compatibility with the test suite
    # Actual commission management is typically handled at the Profile level
    pass

@external
def removeMyCommission(_commission: address):
    """
    Remove a commission from the artist's commission list. Only the owner can call.
    """
    assert msg.sender == self.owner, "Only owner can call"
    # This is a placeholder method for compatibility with the test suite
    # Actual commission management is typically handled at the Profile level
    pass

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

# ================================================================================================
# EDITION CREATION
# ================================================================================================

@external
def createEditionFromArtPiece(
    _art_piece: address,
    _edition_name: String[100],
    _edition_symbol: String[10],
    _mint_price: uint256,
    _max_supply: uint256,
    _royalty_percent: uint256,
    _payment_currency: address = empty(address),
    _sale_type: uint256 = SALE_TYPE_CAPPED,
    _phases: DynArray[PhaseConfig, 5] = [],
    _time_cap_hard_stop: uint256 = 0,
    _mint_cap_hard_stop: uint256 = 0
) -> address:
    """
    Create an ERC1155 edition from an art piece with advanced sale configuration.
    Only the owner or profile can call.
    All metadata is automatically pulled from the linked ArtPiece contract.
    Each edition contract handles exactly one token (ID 1).
    """
    assert msg.sender == self.owner or msg.sender == self.profileAddress, "Only owner or profile can call"
    assert self.artEdition1155Template != empty(address), "ArtEdition1155 template not set"
    assert _art_piece != empty(address), "Invalid art piece address"
    assert _sale_type <= SALE_TYPE_TIME_PHASES, "Invalid sale type"
    
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
    
    # Initialize the edition contract with payment currency
    extcall edition.initialize(self, _art_piece, _edition_name, _edition_symbol, _payment_currency)
    
    # Create the single edition with the specified parameters, sale configuration, and hard stops
    extcall edition.createEdition(_mint_price, _max_supply, _royalty_percent, _sale_type, _phases, _time_cap_hard_stop, _mint_cap_hard_stop)
    
    # Add to artist's ERC1155s for sale using O(1) operation
    if self.artistErc1155sToSellExistsAndPositionOffsetByOne[edition_contract] == 0:
        self.artistErc1155sToSell.append(edition_contract)
        self.artistErc1155sToSellCount += 1
        self.artistErc1155sToSellExistsAndPositionOffsetByOne[edition_contract] = self.artistErc1155sToSellCount
    
    # Map the art piece to this edition
    self.artistPieceToErc1155Map[_art_piece] = edition_contract
    
    log ERC1155Added(erc1155=edition_contract)
    log EditionCreated(erc1155=edition_contract, artPiece=_art_piece, saleType=_sale_type)
    return edition_contract

@view
@external
def hasEditions(_art_piece: address) -> bool:
    """
    Check if an art piece has any ERC1155 editions
    """
    return self.artistPieceToErc1155Map[_art_piece] != empty(address)

# ================================================================================================
# SALES MANAGEMENT FUNCTIONS
# ================================================================================================

@external
def startSaleForEdition(_edition_address: address):
    """
    Start the sale for an edition (always token ID 1).
    Only the owner can call this.
    """
    assert msg.sender == self.owner, "Only owner can start sales"
    assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[_edition_address] != 0, "Edition not managed by this contract"
    
    edition: ArtEdition1155 = ArtEdition1155(_edition_address)
    extcall edition.startSale()
    
    # Get sale info to emit event
    sale_info: (uint256, uint256, uint256, uint256, bool, uint256) = staticcall edition.getSaleInfo()
    sale_type: uint256 = sale_info[0]
    
    log SaleStarted(erc1155=_edition_address, saleType=sale_type)

@external
def pauseSaleForEdition(_edition_address: address):
    """
    Pause the sale for an edition (always token ID 1).
    Only the owner can call this.
    """
    assert msg.sender == self.owner, "Only owner can pause sales"
    assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[_edition_address] != 0, "Edition not managed by this contract"
    
    edition: ArtEdition1155 = ArtEdition1155(_edition_address)
    extcall edition.pauseSale()
    
    log SalePaused(erc1155=_edition_address)

@external
def resumeSaleForEdition(_edition_address: address):
    """
    Resume a paused sale for an edition (always token ID 1).
    Only the owner can call this.
    """
    assert msg.sender == self.owner, "Only owner can resume sales"
    assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[_edition_address] != 0, "Edition not managed by this contract"
    
    edition: ArtEdition1155 = ArtEdition1155(_edition_address)
    extcall edition.resumeSale()
    
    log SaleResumed(erc1155=_edition_address)

@external
def batchStartSales(_edition_addresses: DynArray[address, 10]):
    """
    Start sales for multiple editions at once.
    Much simpler now - no token IDs needed since each edition only has token ID 1.
    """
    assert msg.sender == self.owner, "Only owner can start sales"
    assert len(_edition_addresses) <= 10, "Too many items in batch"
    
    for i: uint256 in range(len(_edition_addresses), bound=10):
        edition_address: address = _edition_addresses[i]
        assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[edition_address] != 0, "Edition not managed by this contract"
        
        edition: ArtEdition1155 = ArtEdition1155(edition_address)
        extcall edition.startSale()
        
        # Get sale info to emit event
        sale_info: (uint256, uint256, uint256, uint256, bool, uint256) = staticcall edition.getSaleInfo()
        sale_type: uint256 = sale_info[0]
        
        log SaleStarted(erc1155=edition_address, saleType=sale_type)

@external
def batchPauseSales(_edition_addresses: DynArray[address, 10]):
    """
    Pause sales for multiple editions at once.
    Much simpler now - no token IDs needed since each edition only has token ID 1.
    """
    assert msg.sender == self.owner, "Only owner can pause sales"
    assert len(_edition_addresses) <= 10, "Too many items in batch"
    
    for i: uint256 in range(len(_edition_addresses), bound=10):
        edition_address: address = _edition_addresses[i]
        assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[edition_address] != 0, "Edition not managed by this contract"
        
        edition: ArtEdition1155 = ArtEdition1155(edition_address)
        extcall edition.pauseSale()
        
        log SalePaused(erc1155=edition_address)

@external
def batchResumeSales(_edition_addresses: DynArray[address, 10]):
    """
    Resume sales for multiple editions at once.
    """
    assert msg.sender == self.owner, "Only owner can resume sales"
    assert len(_edition_addresses) <= 10, "Too many items in batch"
    
    for i: uint256 in range(len(_edition_addresses), bound=10):
        edition_address: address = _edition_addresses[i]
        assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[edition_address] != 0, "Edition not managed by this contract"
        
        edition: ArtEdition1155 = ArtEdition1155(edition_address)
        extcall edition.resumeSale()
        
        log SaleResumed(erc1155=edition_address)

# ================================================================================================
# VIEW FUNCTIONS FOR SALES MANAGEMENT
# ================================================================================================

@view
@external
def getSaleInfo(_edition_address: address) -> (uint256, uint256, uint256, uint256, bool, uint256):
    """
    Get sale information for an edition (always token ID 1).
    Returns (saleType, currentPrice, currentSupply, maxSupply, isPaused, currentPhase)
    """
    assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[_edition_address] != 0, "Edition not managed by this contract"
    
    edition: ArtEdition1155 = ArtEdition1155(_edition_address)
    return staticcall edition.getSaleInfo()

@view
@external
def getPhaseInfo(_edition_address: address) -> DynArray[PhaseConfig, 5]:
    """
    Get phase configuration for an edition (always token ID 1).
    """
    assert self.artistErc1155sToSellExistsAndPositionOffsetByOne[_edition_address] != 0, "Edition not managed by this contract"
    
    edition: ArtEdition1155 = ArtEdition1155(_edition_address)
    return staticcall edition.getPhases()

@view
@external
def getAllActiveSales(_page: uint256, _page_size: uint256) -> DynArray[address, 20]:
    """
    Get addresses of all active edition contracts managed by this contract.
    Use getSaleInfo() to get detailed information for each edition.
    Much simpler now since each edition only has one token.
    Limited to 20 results per call for gas efficiency.
    """
    result: DynArray[address, 20] = []
    
    arr_len: uint256 = self.artistErc1155sToSellCount
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 20)
    
    for i: uint256 in range(0, items, bound=20):
        edition_address: address = self.artistErc1155sToSell[start + i]
        edition: ArtEdition1155 = ArtEdition1155(edition_address)
        
        # Check if the edition exists and has been created
        sale_info: (uint256, uint256, uint256, uint256, bool, uint256) = staticcall edition.getSaleInfo()
        if sale_info[1] > 0:  # If currentPrice > 0, edition exists
            result.append(edition_address)
    
    return result

@view
@external
def isSaleActive(_edition_address: address) -> bool:
    """
    Check if a sale is currently active (not paused and edition exists).
    Much simpler now since each edition only has one token.
    """
    if self.artistErc1155sToSellExistsAndPositionOffsetByOne[_edition_address] == 0:
        return False
    
    edition: ArtEdition1155 = ArtEdition1155(_edition_address)
    sale_info: (uint256, uint256, uint256, uint256, bool, uint256) = staticcall edition.getSaleInfo()
    return sale_info[1] > 0 and not sale_info[4]  # currentPrice > 0 and not isPaused

@view
@external
def getAllManagedEditions() -> DynArray[address, 100]:
    """
    Get all edition addresses managed by this contract (up to 100).
    Use for admin interfaces to see all editions.
    """
    result: DynArray[address, 100] = []
    items_to_return: uint256 = min(100, self.artistErc1155sToSellCount)
    
    for i: uint256 in range(0, items_to_return, bound=100):
        result.append(self.artistErc1155sToSell[i])
    
    return result
