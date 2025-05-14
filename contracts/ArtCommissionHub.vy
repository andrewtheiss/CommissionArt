# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# Contains a list of Art Pieces per a given NFT
# Allows for verification of the commissions
# Allows for creation of a new commission
# These are NFT Contracts who's children are Art Pieces and also nfts  
# The commission hub CHANGES OWNER as the L1QueryOwner updates and propegates across chains

# Interface for ArtPiece contract
interface ArtPiece:
    def isOnCommissionWhitelist(_commissioner: address) -> bool: view

owner: public(address)
chainId: public(uint256)  # Added chain ID to identify which blockchain the NFT is on
nftContract: public(address)
tokenId: public(uint256)
registry: public(address)
isInitialized: public(bool)
imageDataContracts: public(HashMap[uint256, address])
l1Contract: public(address)  # Address of the NFT contract on L1
isOwnershipRescinded: public(bool)  # Flag to track if ownership has been rescinded
is_generic: public(bool)  # Flag to indicate if this is a generic hub not tied to an NFT

# Track allowed ArtPiece contracts by code hash
approvedCodeHashes: public(HashMap[bytes32, bool])

# Track commissions
latestVerifiedArt: public(address[300])
verifiedArt: public(DynArray[address, 10**9])
unverifiedArt: public(DynArray[address, 10**9])
countVerifiedCommissions: public(uint256)
countUnverifiedCommissions: public(uint256)
nextLatestVerifiedArtIndex: public(uint256)
unverifiedCountByUser: public(HashMap[address, uint256])


event OwnershipRescinded:
    previous_owner: indexed(address)

event L1ContractSet:
    l1_contract: indexed(address)

event Initialized:
    chain_id: indexed(uint256)
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    registry: address

event GenericInitialized:
    chain_id: indexed(uint256)
    owner: indexed(address)
    registry: address
    is_generic: bool

event OwnershipUpdated:
    chain_id: indexed(uint256)
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address

event CommissionSubmitted:
    art_piece: indexed(address)
    submitter: indexed(address)
    verified: bool

event CommissionVerified:
    art_piece: indexed(address)
    verifier: indexed(address)

event CommissionerWhitelisted:
    commissioner: indexed(address)
    status: bool

event CodeHashWhitelisted:
    code_hash: indexed(bytes32)
    status: bool

@deploy
def __init__():
    self.owner = msg.sender
    self.isOwnershipRescinded = False
    self.l1Contract = empty(address)
    self.isInitialized = False
    self.chainId = 0  # Initialize with 0 to indicate not set
    self.countVerifiedCommissions = 0
    self.countUnverifiedCommissions = 0
    self.nextLatestVerifiedArtIndex = 0
    self.is_generic = False

@external
def initialize(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _registry: address):
    assert not self.isInitialized, "Already initialized"
    self.isInitialized = True
    self.chainId = _chain_id
    self.nftContract = _nft_contract
    self.tokenId = _token_id
    self.registry = _registry
    self.is_generic = False
    log Initialized(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, registry=_registry)

@external
def initializeGeneric(_chain_id: uint256, _owner: address, _registry: address, _is_generic: bool):
    """
    @notice Initialize a generic commission hub not tied to an NFT
    @dev This is used for multisigs, DAOs, or individual wallets that don't own NFTs
    @param _chain_id The chain ID where this hub is deployed
    @param _owner The address that will own this commission hub
    @param _registry The address of the OwnerRegistry contract
    @param _is_generic Flag to indicate this is a generic hub
    """
    assert not self.isInitialized, "Already initialized"
    assert _owner != empty(address), "Owner cannot be empty"
    assert _registry != empty(address), "Registry cannot be empty"
    assert _is_generic, "Must be initialized as generic"
    
    self.isInitialized = True
    self.chainId = _chain_id
    self.owner = _owner
    self.registry = _registry
    self.is_generic = True
    
    # For generic hubs, we don't set nftContract or tokenId
    self.nftContract = empty(address)
    self.tokenId = 0
    
    log GenericInitialized(chain_id=_chain_id, owner=_owner, registry=_registry, is_generic=_is_generic)

@external
def updateRegistration(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _owner: address):
    assert self.isInitialized, "Not initialized"
    assert msg.sender == self.registry, "Only registry can update owner"
    
    # For generic hubs, we only check chain ID
    if self.is_generic:
        assert self.chainId == _chain_id, "Chain ID mismatch"
        self.owner = _owner
        log OwnershipUpdated(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, owner=_owner)
        return
    
    # For NFT-based hubs, we check all parameters
    assert self.chainId == _chain_id, "Chain ID mismatch"
    assert self.nftContract == _nft_contract, "NFT contract mismatch"
    assert self.tokenId == _token_id, "Token ID mismatch"
    self.owner = _owner
    log OwnershipUpdated(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, owner=_owner)

@external
def registerImageData(_azuki_id: uint256, _image_contract: address):
    # Check rescinded status first
    assert not self.isOwnershipRescinded, "Ownership has been rescinded"
    # Then check if sender is owner
    assert msg.sender == self.owner, "Only owner can register"
    # Allow reregistration
    self.imageDataContracts[_azuki_id] = _image_contract

@external
def setL1Contract(_l1_contract_address: address):
    # Check rescinded status first
    assert not self.isOwnershipRescinded, "Ownership has been rescinded"
    # Then check if sender is owner
    assert msg.sender == self.owner, "Only owner can set L1 contract"
    assert _l1_contract_address != empty(address), "Invalid L1 contract address"
    self.l1Contract = _l1_contract_address
    log L1ContractSet(l1_contract=_l1_contract_address)

@external
def approveArtPieceCodeHash(_art_piece: address, _approved: bool):
    """
    @notice Approves or removes approval for an art piece contract code hash
    @dev Takes an art piece contract address, computes its code hash, and adds it to the whitelist
    @param _art_piece The address of an art piece contract with the desired code
    @param _approved Whether to approve (true) or revoke approval (false)
    """
    # Check rescinded status first
    assert not self.isOwnershipRescinded, "Ownership has been rescinded"
    # Only owner can set the whitelist
    assert msg.sender == self.owner, "Only owner can set whitelist"
    assert _art_piece != empty(address), "Invalid ArtPiece contract address"
    assert self._isContract(_art_piece), "Address is not a contract"
    
    # Compute code hash
    code_hash: bytes32 = _art_piece.codehash
    
    # Set approval status
    self.approvedCodeHashes[code_hash] = _approved
    
    # Log event
    log CodeHashWhitelisted(code_hash=code_hash, status=_approved)

@external
def approveArtPieceCodeHashDirect(_code_hash: bytes32, _approved: bool):
    """
    @notice Directly approves or removes approval for an art piece code hash
    @dev Allows owner to manage the whitelist using just the hash value
    @param _code_hash The code hash to whitelist
    @param _approved Whether to approve (true) or revoke approval (false)
    """
    # Check rescinded status first
    assert not self.isOwnershipRescinded, "Ownership has been rescinded"
    # Only owner can set the whitelist
    assert msg.sender == self.owner, "Only owner can set whitelist"
    assert _code_hash != empty(bytes32), "Invalid code hash"
    
    # Set approval status
    self.approvedCodeHashes[_code_hash] = _approved
    
    # Log event
    log CodeHashWhitelisted(code_hash=_code_hash, status=_approved)

@internal
@view
def _isContract(_addr: address) -> bool:
    """
    @notice Check if an address is a contract
    @param _addr The address to check
    @return Whether the address is a contract
    """
    size: uint256 = 0
    # Check code size at address
    if _addr != empty(address):
        if len(slice(_addr.code, 0, 1)) > 0:
            size = 1
    return size > 0

@view
@external
def isApprovedArtPieceType(_art_piece: address) -> bool:
    """
    @notice Checks if an art piece contract's code hash is whitelisted
    @param _art_piece The art piece contract to check
    @return Whether the art piece's code hash is approved
    """
    if not self._isContract(_art_piece):
        return False
        
    code_hash: bytes32 = _art_piece.codehash
    return self.approvedCodeHashes[code_hash]

@external
def submitCommission(_art_piece: address):
    # Need to assert that the art piece is actually an art piece
    assert self._isContract(_art_piece), "Art piece is not a contract"
    
    # Check if code hash is whitelisted
    code_hash: bytes32 = _art_piece.codehash
    assert self.approvedCodeHashes[code_hash], "Art piece code not approved"

    is_whitelisted: bool = staticcall ArtPiece(_art_piece).isOnCommissionWhitelist(msg.sender)
    
    if is_whitelisted:
        # Add to verified list
        self.verifiedArt.append(_art_piece)
        self.countVerifiedCommissions += 1
        
        # Update latest verified art (circular buffer)
        self.latestVerifiedArt[self.nextLatestVerifiedArtIndex] = _art_piece
        self.nextLatestVerifiedArtIndex = (self.nextLatestVerifiedArtIndex + 1) % 300
        
        log CommissionSubmitted(art_piece=_art_piece, submitter=msg.sender, verified=True)
    else:
        # For unverified commissions, ensure user doesn't have too many
        assert self.unverifiedCountByUser[msg.sender] < 500, "Please verify commissions. Unverified for this account exceeds 500 items"
        
        # Add to unverified list
        self.unverifiedArt.append(_art_piece)
        self.countUnverifiedCommissions += 1
        self.unverifiedCountByUser[msg.sender] += 1
        
        log CommissionSubmitted(art_piece=_art_piece, submitter=msg.sender, verified=False)

@external
def verifyCommission(_art_piece: address, _submitter: address):
    # Only owner or authorized users can verify
    assert msg.sender == self.owner, "Not authorized to verify"
    
    # Check if code hash is whitelisted
    code_hash: bytes32 = _art_piece.codehash
    assert self.approvedCodeHashes[code_hash], "Art piece code not approved"
    
    # Update user's unverified count
    if self.unverifiedCountByUser[_submitter] > 0:
        self.unverifiedCountByUser[_submitter] -= 1
    
    # Add to verified list
    self.verifiedArt.append(_art_piece)
    self.countVerifiedCommissions += 1
    
    # Update latest verified art (circular buffer)
    self.latestVerifiedArt[self.nextLatestVerifiedArtIndex] = _art_piece
    self.nextLatestVerifiedArtIndex = (self.nextLatestVerifiedArtIndex + 1) % 300
    
    log CommissionVerified(art_piece=_art_piece, verifier=msg.sender)

@view
@external
def getUnverifiedCount(_user: address) -> uint256:
    return self.unverifiedCountByUser[_user]

@view
@external
def getLatestVerifiedArt(_count: uint256, _page: uint256 = 0) -> DynArray[address, 3]:
    result: DynArray[address, 3] = []
    
    # Early return if no verified art pieces
    if self.countVerifiedCommissions == 0:
        return result
    
    # Limit to available pieces
    available: uint256 = min(self.countVerifiedCommissions, 300)
    
    # Calculate start index based on page and count
    items_per_page: uint256 = min(_count, 3)
    start_idx: uint256 = _page * items_per_page
    
    # Early return if start index is out of bounds
    if start_idx >= available:
        return result
    
    # Calculate how many items to return, capped by available items
    count: uint256 = min(items_per_page, available - start_idx)
    if count == 0:
        return result
    
    # Calculate buffer start differently based on fill level
    buffer_start: uint256 = 0
    if self.countVerifiedCommissions >= 300:
        # When buffer is full, use the next index as starting point
        buffer_start = self.nextLatestVerifiedArtIndex
    else:
        # When buffer is partially filled, start from the beginning
        buffer_start = 0
    
    # Populate result array
    for i: uint256 in range(0, count, bound=3):
        idx: uint256 = (buffer_start + start_idx + i) % 300
        if self.latestVerifiedArt[idx] != empty(address):
            result.append(self.latestVerifiedArt[idx])
    
    return result

@view
@external
def getVerifiedArtPieces(_start_idx: uint256, _count: uint256) -> DynArray[address, 1000]:
    result: DynArray[address, 1000] = []
    
    # Early return if no verified art or start index is out of bounds
    if self.countVerifiedCommissions == 0 or _start_idx >= self.countVerifiedCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countVerifiedCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 1000)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=1000):
        result.append(self.verifiedArt[_start_idx + i])
    
    return result

@view
@external
def getUnverifiedArtPieces(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    result: DynArray[address, 50] = []
    
    # Early return if no unverified art or start index is out of bounds
    if self.countUnverifiedCommissions == 0 or _start_idx >= self.countUnverifiedCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countUnverifiedCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.unverifiedArt[_start_idx + i])
    
    return result

# Enhanced batch loading functions for efficient frontend queries

@view
@external
def getBatchVerifiedArtPieces(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a batch of verified art pieces with improved capacity
    @dev Allows retrieving up to 50 art pieces at once for efficient frontend loading
    @param _start_idx The starting index in the verified art array
    @param _count The number of art pieces to retrieve
    @return Array of art piece addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no verified art or start index is out of bounds
    if self.countVerifiedCommissions == 0 or _start_idx >= self.countVerifiedCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countVerifiedCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.verifiedArt[_start_idx + i])
    
    return result

@view
@external
def getBatchUnverifiedArtPieces(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a batch of unverified art pieces with improved capacity
    @dev Allows retrieving up to 50 art pieces at once for efficient frontend loading
    @param _start_idx The starting index in the unverified art array
    @param _count The number of art pieces to retrieve
    @return Array of art piece addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no unverified art or start index is out of bounds
    if self.countUnverifiedCommissions == 0 or _start_idx >= self.countUnverifiedCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countUnverifiedCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.unverifiedArt[_start_idx + i])
    
    return result

@view
@external
def getRecentVerifiedArtPieces(_count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns the most recent verified art pieces
    @dev Returns art pieces from the end of the array (most recently added)
    @param _count The number of recent art pieces to retrieve
    @return Array of recent art piece addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no verified art
    if self.countVerifiedCommissions == 0:
        return result
    
    # Calculate how many items to return, capped by array size and max return size
    count: uint256 = min(min(_count, self.countVerifiedCommissions), 50)
    
    # Start from the end of the array (most recent)
    start_idx: uint256 = self.countVerifiedCommissions - count
    
    # Populate result array
    for i: uint256 in range(0, count, bound=50):
        result.append(self.verifiedArt[start_idx + i])
    
    return result

@view
@external
def getRecentUnverifiedArtPieces(_count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns the most recent unverified art pieces
    @dev Returns art pieces from the end of the array (most recently added)
    @param _count The number of recent art pieces to retrieve
    @return Array of recent art piece addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no unverified art
    if self.countUnverifiedCommissions == 0:
        return result
    
    # Calculate how many items to return, capped by array size and max return size
    count: uint256 = min(min(_count, self.countUnverifiedCommissions), 50)
    
    # Start from the end of the array (most recent)
    start_idx: uint256 = self.countUnverifiedCommissions - count
    
    # Populate result array
    for i: uint256 in range(0, count, bound=50):
        result.append(self.unverifiedArt[start_idx + i])
    
    return result

@view
@external
def getVerifiedArtPiecesByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of verified art pieces using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the verified art array
    @param _count The number of art pieces to return (capped at 50)
    @return A list of verified art piece addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no verified art or offset is out of bounds
    if self.countVerifiedCommissions == 0 or _offset >= self.countVerifiedCommissions:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.countVerifiedCommissions - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.verifiedArt[_offset + i])
    
    return result

@view
@external
def getUnverifiedArtPiecesByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of unverified art pieces using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the unverified art array
    @param _count The number of art pieces to return (capped at 50)
    @return A list of unverified art piece addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no unverified art or offset is out of bounds
    if self.countUnverifiedCommissions == 0 or _offset >= self.countUnverifiedCommissions:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.countUnverifiedCommissions - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.unverifiedArt[_offset + i])
    
    return result

@view
@external
def getArtPieceByIndex(_verified: bool, _index: uint256) -> address:
    """
    @notice Returns an art piece at a specific index
    @dev Allows direct access to art pieces by index
    @param _verified Whether to access verified or unverified art
    @param _index The index of the art piece to retrieve
    @return The address of the art piece at the specified index
    """
    if _verified:
        assert _index < self.countVerifiedCommissions, "Index out of bounds"
        return self.verifiedArt[_index]
    else:
        assert _index < self.countUnverifiedCommissions, "Index out of bounds"
        return self.unverifiedArt[_index]