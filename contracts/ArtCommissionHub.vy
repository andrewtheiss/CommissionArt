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
# The commission hub CHANGES OWNER as the L1QueryOwnership updates and propegates across chains


# Constants for maximum array sizes
MAX_UNVERIFIED_ART: constant(uint256) = 1000
MAX_VERIFIED_ART: constant(uint256) = 1000
GENERIC_ART_COMMISSION_HUB_CONTRACT: constant(address) = 0x1000000000000000000000000000000000000001

# Interface for ArtPiece contract
interface ArtPiece:
    def isFullyVerifiedCommission() -> bool: view
    def getArtist() -> address: view
    def getCommissioner() -> address: view

# Interface for ArtCommissionHubOwners
interface ArtCommissionHubOwners:
    def lookupRegisteredOwner(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256) -> address: view
    def isAllowedToUpdateForAddress(_address: address) -> bool: view
    def isApprovedArtPieceAddress(_art_piece: address) -> bool: view

# Single owner for the whole collection
# Can be updated by anyone via L1/L2 QueryOwnership relay
# Can be set to empty address when initialized before NFT is authenticated
owner: public(address)  

isInitialized: public(bool)
chainId: public(uint256)  # Added chain ID to identify which blockchain the NFT is on
nftContract: public(address) # If non-generic, the NFT contract address
nftTokenIdOrGenericHubAccount: public(uint256) # If non-generic, the token ID of the NFT
artCommissionHubOwners: public(address) # The address of the ArtCommissionHubOwners contract
expectedArtCommissionHubOwnersHash: public(bytes32) # The hash of the ArtCommissionHubOwners contract code
isBurned: public(bool)  # Flag to track if the NFT has been burned (updated to zero address owner from L2OwnershipRelay)
isGeneric: public(bool)  # Flag to track if the NFT is a generic hub

# Links to parent chain addresses
sourceChainContract: public(address)  # Address of the NFT contract on L1
sourceChainTokenId: public(uint256) # Token ID of the NFT on L1
sourceChainImageData: public(Bytes[45000]) # Address of the image data or image data contract

# Verified Art Commissions
latestVerifiedArtCommissions: public(address[100])
verifiedArtCommissions: public(DynArray[address, 10**8])
countVerifiedArtCommissions: public(uint256)
verifiedArtCommissionsCountByUser: public(HashMap[address, uint256])
verifiedArtCommissionsRegistry: public(HashMap[address, bool])

# Unverified Art Commissions
unverifiedArtCommissions: public(DynArray[address, 10**8]) 
countUnverifiedArtCommissions: public(uint256)
unverifiedArtCommissionsCountByUser: public(HashMap[address, uint256])  
UNVERIFIED_ART_COMMISSIONS_PER_USER_LIMIT: constant(uint256) = 500
unverifiedArtCommissionsRegistry: public(HashMap[address, bool])

# Access lists
whitelist: public(HashMap[address, bool])
blacklist: public(HashMap[address, bool])

# Getter index variables
nextLatestVerifiedArtCommissionsIndex: public(uint256)
nextLatestVerifiedArtIndex: public(uint256)

event Initialized:
    chain_id: indexed(uint256)
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    artCommissionHubOwners: address
    is_generic: bool
    owner: address

event OwnershipUpdated:
    chain_id: indexed(uint256)
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    previous_owner: address
    owner: address

event CommissionSubmitted:
    art_piece: indexed(address)
    submitter: indexed(address)
    verified: bool

event CommissionVerified:
    art_piece: indexed(address)
    verifier: indexed(address)

event CommissionUnverified:
    art_piece: indexed(address)
    unverifier: indexed(address)

event CommissionerWhitelisted:
    commissioner: indexed(address)
    status: bool


@deploy
def __init__():
    # Prevent direct deployment except by ArtCommissionHubOwners (enforced at initialize)
    self.owner = empty(address)
    self.isInitialized = False
    self.chainId = 1
    self.countVerifiedArtCommissions = 0
    self.countUnverifiedArtCommissions = 0
    self.isBurned = False

@external
def initializeParentCommissionHubOwnerContract(_art_commission_hub_owners: address):
    assert self.artCommissionHubOwners == empty(address), "Already set"
    assert _art_commission_hub_owners != empty(address), "Invalid address"
    size: uint256 = 0
    if len(slice(_art_commission_hub_owners.code, 0, 1)) > 0:
        size = 1
    assert size > 0, "Not a contract"
    self.expectedArtCommissionHubOwnersHash = keccak256(_art_commission_hub_owners.codehash)
    self.artCommissionHubOwners = _art_commission_hub_owners

@external
def initializeForArtCommissionHub(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256):
    assert not self.isInitialized, "Already initialized"
    assert self.artCommissionHubOwners != empty(address), "ArtCommissionHubOwners not set"
    code_hash: bytes32 = keccak256(self.artCommissionHubOwners.codehash)
    assert code_hash == self.expectedArtCommissionHubOwnersHash, "ArtCommissionHubOwners code hash mismatch"
    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    assert staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender), "Not allowed to update"

    # Set the owner of the commission hub
    if (_nft_contract == GENERIC_ART_COMMISSION_HUB_CONTRACT):
        self.isGeneric = True
    else:
        self.isGeneric = False
    self.isInitialized = True
    self.chainId = _chain_id
    self.nftContract = _nft_contract
    self.nftTokenIdOrGenericHubAccount = _nft_token_id_or_generic_hub_account
    self.owner = staticcall art_commission_hub_owners_interface.lookupRegisteredOwner(_chain_id, _nft_contract, _nft_token_id_or_generic_hub_account)
    
    log Initialized(
        chain_id=_chain_id, 
        nft_contract=_nft_contract, 
        token_id=_nft_token_id_or_generic_hub_account, 
        artCommissionHubOwners=self.artCommissionHubOwners, 
        is_generic=self.isGeneric,
        owner=self.owner
    )

@external
def syncArtCommissionHubOwner(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256, _owner: address):
    assert self.isInitialized, "Not initialized"
    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    assert staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender), "Not allowed to update"
    previous_owner: address = self.owner

    # For generic hubs, we only check chain ID
    if self.isGeneric:
        assert self.chainId == _chain_id, "Chain ID mismatch"
        self.owner = _owner
        log OwnershipUpdated(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_nft_token_id_or_generic_hub_account, previous_owner=previous_owner, owner=_owner)
        return

    # If the new owner is the empty address and the old owner isnt empty we need to burn the NFT
    elif _owner == empty(address) and self.owner != empty(address):
        self.isBurned = True
    
    # For NFT-based hubs, we check all parameters
    assert self.chainId == _chain_id, "Chain ID mismatch"
    assert self.nftContract == _nft_contract, "NFT contract mismatch"
    assert self.nftTokenIdOrGenericHubAccount == _nft_token_id_or_generic_hub_account, "Token ID mismatch"
    
    # Always update the owner, even if it's the same as before
    # This ensures the owner is set correctly in all cases
    self.owner = _owner
    
    log OwnershipUpdated(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_nft_token_id_or_generic_hub_account, previous_owner=previous_owner, owner=_owner)


# Commission Submission Overview:
# 1. Art pieces undergo Profile verification process between the artist and commissioner Profiles
# 2. Once both Profiles have verified, the 2nd verifier triggers submitCommission
# 3. Before accepting, we must confirm the art piece is fully verified between artist and commissioner profiles
# 4. If the art piece is fully verified:
#    - Check if it is either:
#        a) The sender owns the ArtCommissionHub
#        b) Newly created (no owner yet as its Ownership has not been Querried, and its not burned), or
#        c) The artist or commissioner is whitelisted.
#    - If either condition is met, add the piece to the verified commissions list.
#    - Otherwise, add it to the unverified commissions list for further review (unless there is a blacklisted artist or commissioner)
# 5. This ensures only properly verified or trusted art pieces are immediately accepted as commissions, while others require additional validation.
@external
def submitCommission(_art_piece: address):
    assert not self.isBurned, "Art piece has been burned"
    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    assert staticcall art_commission_hub_owners_interface.isApprovedArtPieceAddress(_art_piece), "Not allowed to update.  Unknwon art type"
    assert staticcall ArtPiece(_art_piece).isFullyVerifiedCommission(), "Art piece is not fully between Artist and Commissioner"
    
    # assert not already submitted or blacklisted artist or commissioner
    assert not self.verifiedArtCommissionsRegistry[_art_piece], "Art piece already verified"
    assert not self.unverifiedArtCommissionsRegistry[_art_piece], "Art piece already unverified"
    assert not self.blacklist[staticcall ArtPiece(_art_piece).getArtist()], "Artist is blacklisted"
    assert not self.blacklist[staticcall ArtPiece(_art_piece).getCommissioner()], "Commissioner is blacklisted"

    sender_has_permission: bool = staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender)
    is_recent_art_hub_creation: bool = self.isBurned == False and self.owner == empty(address)
    is_whitelisted_artist: bool = self.whitelist[staticcall ArtPiece(_art_piece).getArtist()]
    is_whitelisted_commissioner: bool = self.whitelist[staticcall ArtPiece(_art_piece).getCommissioner()]

    # Add to verified list
    if sender_has_permission or is_recent_art_hub_creation or is_whitelisted_artist or is_whitelisted_commissioner:
        self.verifiedArtCommissions.append(_art_piece)
        self.countVerifiedArtCommissions += 1
        self.verifiedArtCommissionsRegistry[_art_piece] = True
        
        # Update latest verified art (circular buffer)
        self.latestVerifiedArtCommissions[self.nextLatestVerifiedArtCommissionsIndex] = _art_piece
        self.nextLatestVerifiedArtCommissionsIndex = (self.nextLatestVerifiedArtCommissionsIndex + 1) % 100
    
        log CommissionSubmitted(art_piece=_art_piece, submitter=msg.sender, verified=True)
    else:
        # For unverified commissions, ensure user doesn't have too many
        assert self.unverifiedArtCommissionsCountByUser[msg.sender] < 500, "Please verify commissions. Unverified for this account exceeds 500 items"
        
        # Add to unverified list
        self.unverifiedArtCommissionsCountByUser[msg.sender] += 1
        self.unverifiedArtCommissions.append(_art_piece)
        self.countUnverifiedArtCommissions += 1
        self.unverifiedArtCommissionsRegistry[_art_piece] = True
        
        log CommissionSubmitted(art_piece=_art_piece, submitter=msg.sender, verified=False)

@external
def verifyCommission(_art_piece: address):
    self._verifyCommission(_art_piece)

@internal
def _verifyCommission(_art_piece: address):
    
    # Bulk verify requires return immediately if already verified
    already_verified: bool = self.verifiedArtCommissionsRegistry[_art_piece]
    if already_verified:
        return
        
    # Check that its unverified, otherwise it needs to be submitted 
    assert self.unverifiedArtCommissionsRegistry[_art_piece], "Art piece is not unverified, please submit via submitCommission"
    assert not self.blacklist[staticcall ArtPiece(_art_piece).getArtist()], "Artist is blacklisted"
    assert not self.blacklist[staticcall ArtPiece(_art_piece).getCommissioner()], "Commissioner is blacklisted"

    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    sender_has_permission: bool = staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender)
    is_recent_art_hub_creation: bool = self.isBurned == False and self.owner == empty(address)
    is_whitelisted_artist: bool = self.whitelist[staticcall ArtPiece(_art_piece).getArtist()]
    is_whitelisted_commissioner: bool = self.whitelist[staticcall ArtPiece(_art_piece).getCommissioner()]
    assert sender_has_permission or is_recent_art_hub_creation or is_whitelisted_artist or is_whitelisted_commissioner, "Not allowed to verify, must be whitelisted or owner"
    
    # Find the art piece in the unverified array
    found_index: int256 = -1
    for i: uint256 in range(0, len(self.unverifiedArtCommissions), bound=MAX_UNVERIFIED_ART):
        if self.unverifiedArtCommissions[i] == _art_piece:
            found_index = convert(i, int256)
            break
    
    # If found, remove from unverified list by replacing with the last item
    if found_index >= 0:
        # Update user's unverified count
        if self.unverifiedArtCommissionsCountByUser[msg.sender] > 0:
            self.unverifiedArtCommissionsCountByUser[msg.sender] -= 1
            
        # Remove from unverified array (replace with last element and pop)
        last_index: uint256 = len(self.unverifiedArtCommissions) - 1
        if convert(found_index, uint256) != last_index:  # If not already the last element
            self.unverifiedArtCommissions[convert(found_index, uint256)] = self.unverifiedArtCommissions[last_index]
        self.unverifiedArtCommissions.pop()  # Remove last element
        self.countUnverifiedArtCommissions -= 1
    else:
        # If not found in unverified array, just decrease the unverified count for the user
        if self.unverifiedArtCommissionsCountByUser[msg.sender] > 0:
            self.unverifiedArtCommissionsCountByUser[msg.sender] -= 1
    
    # Add to verified list
    self.verifiedArtCommissions.append(_art_piece)
    self.countVerifiedArtCommissions += 1
    
    # Update latest verified art (circular buffer)
    self.latestVerifiedArtCommissions[self.nextLatestVerifiedArtCommissionsIndex] = _art_piece
    self.nextLatestVerifiedArtCommissionsIndex = (self.nextLatestVerifiedArtCommissionsIndex + 1) % 100
    
    log CommissionVerified(art_piece=_art_piece, verifier=msg.sender)


@external
def unverifyCommission(_art_piece: address):
    self._unverifyCommission(_art_piece)

@internal
def _unverifyCommission(_art_piece: address):

    # Bulk unverify requires return immediately if already unverified
    already_unverified: bool = self.unverifiedArtCommissionsRegistry[_art_piece]
    if already_unverified:
        return
    
    # Check that its verified, otherwise it needs to be submitted 
    assert self.verifiedArtCommissionsRegistry[_art_piece], "Art piece is not even verified...  Nothing to worry about!"
    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    assert staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender), "Not allowed to unverify"
    
    # Find the art piece in the verified array
    found_index: int256 = -1
    for i: uint256 in range(0, len(self.verifiedArtCommissions), bound=MAX_VERIFIED_ART):
        if self.verifiedArtCommissions[i] == _art_piece:
            found_index = convert(i, int256)
            break
    
    # If found, remove from verified list
    if found_index >= 0:
        # Remove from verified array (replace with last element and pop)
        last_index: uint256 = len(self.verifiedArtCommissions) - 1
        if convert(found_index, uint256) != last_index:  # If not already the last element
            self.verifiedArtCommissions[convert(found_index, uint256)] = self.verifiedArtCommissions[last_index]
        self.verifiedArtCommissions.pop()  # Remove last element
        self.countVerifiedArtCommissions -= 1
        
        # Update the submitter's unverified count
        self.unverifiedArtCommissionsCountByUser[msg.sender] += 1
        
        # Add to unverified list
        self.unverifiedArtCommissions.append(_art_piece)
        self.countUnverifiedArtCommissions += 1
        
        log CommissionUnverified(art_piece=_art_piece, unverifier=msg.sender)
    else:
        # If not found in verified array, revert
        assert False, "Art piece not found in verified list"

@view
@external
def getUnverifiedCount(_user: address) -> uint256:
    return self.unverifiedArtCommissionsCountByUser[_user]

@view
@external
def getLatestVerifiedArt(_count: uint256, _page: uint256 = 0) -> DynArray[address, 10]:
    result: DynArray[address, 10] = []
    
    # Early return if no verified art pieces
    if self.countVerifiedArtCommissions == 0:
        return result
    
    # Limit to available pieces
    available: uint256 = min(self.countVerifiedArtCommissions, 100)
    
    # Calculate start index based on page and count
    items_per_page: uint256 = min(_count, 10)
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
    if self.countVerifiedArtCommissions >= 100:
        # When buffer is full, use the next index as starting point
        buffer_start = self.nextLatestVerifiedArtCommissionsIndex
    else:
        # When buffer is partially filled, start from the beginning
        buffer_start = 0
    
    # Populate result array
    for i: uint256 in range(0, count, bound=10):
        idx: uint256 = (buffer_start + start_idx + i) % 100
        if self.latestVerifiedArtCommissions[idx] != empty(address):
            result.append(self.latestVerifiedArtCommissions[idx])
    
    return result

@view
@external
def getVerifiedArtPieces(_start_idx: uint256, _count: uint256) -> DynArray[address, 1000]:
    result: DynArray[address, 1000] = []
    
    # Early return if no verified art or start index is out of bounds
    if self.countVerifiedArtCommissions == 0 or _start_idx >= self.countVerifiedArtCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countVerifiedArtCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 1000)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=1000):
        result.append(self.verifiedArtCommissions[_start_idx + i])
    
    return result

@view
@external
def getUnverifiedArtPieces(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    result: DynArray[address, 50] = []
    
    # Early return if no unverified art or start index is out of bounds
    if self.countUnverifiedArtCommissions == 0 or _start_idx >= self.countUnverifiedArtCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countUnverifiedArtCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.unverifiedArtCommissions[_start_idx + i])
    
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
    if self.countVerifiedArtCommissions == 0 or _start_idx >= self.countVerifiedArtCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countVerifiedArtCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.verifiedArtCommissions[_start_idx + i])
    
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
    if self.countUnverifiedArtCommissions == 0 or _start_idx >= self.countUnverifiedArtCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countUnverifiedArtCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.unverifiedArtCommissions[_start_idx + i])
    
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
    if self.countVerifiedArtCommissions == 0:
        return result
    
    # Calculate how many items to return, capped by array size and max return size
    count: uint256 = min(min(_count, self.countVerifiedArtCommissions), 50)
    
    # Start from the end of the array (most recent)
    start_idx: uint256 = self.countVerifiedArtCommissions - count
    
    # Populate result array
    for i: uint256 in range(0, count, bound=50):
        result.append(self.verifiedArtCommissions[start_idx + i])
    
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
    if self.countUnverifiedArtCommissions == 0:
        return result
    
    # Calculate how many items to return, capped by array size and max return size
    count: uint256 = min(min(_count, self.countUnverifiedArtCommissions), 50)
    
    # Start from the end of the array (most recent)
    start_idx: uint256 = self.countUnverifiedArtCommissions - count
    
    # Populate result array
    for i: uint256 in range(0, count, bound=50):
        result.append(self.unverifiedArtCommissions[start_idx + i])
    
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
    if self.countVerifiedArtCommissions == 0 or _offset >= self.countVerifiedArtCommissions:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.countVerifiedArtCommissions - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.verifiedArtCommissions[_offset + i])
    
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
    if self.countUnverifiedArtCommissions == 0 or _offset >= self.countUnverifiedArtCommissions:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.countUnverifiedArtCommissions - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.unverifiedArtCommissions[_offset + i])
    
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
        assert _index < self.countVerifiedArtCommissions, "Index out of bounds"
        return self.verifiedArtCommissions[_index]
    else:
        assert _index < self.countUnverifiedArtCommissions, "Index out of bounds"
        return self.unverifiedArtCommissions[_index]

@external
def bulkVerifyCommissions(_commission_addresses: DynArray[address, 1000]):
    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    assert staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender), "Not allowed to update"
    for i: uint256 in range(0, len(_commission_addresses), bound=1000):
        self._verifyCommission(_commission_addresses[i])
        
@external
def bulkUnverifyCommissions(_commission_addresses: DynArray[address, 1000]):
    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    assert staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender), "Not allowed to update"
    for i: uint256 in range(0, len(_commission_addresses), bound=1000):
        self._unverifyCommission(_commission_addresses[i])

@external
def updateWhitelistOrBlacklist(_address_to_list: address, _is_whitelist: bool, _list_status: bool):
    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    assert staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender), "Not allowed to update"
    if _is_whitelist:
        self.whitelist[_address_to_list] = _list_status
        if self.blacklist[_address_to_list]:
            self.blacklist[_address_to_list] = False
    else:
        self.blacklist[_address_to_list] = _list_status
        if self.whitelist[_address_to_list]:
            self.whitelist[_address_to_list] = False
 
@external
def clearAllUnverifiedArtCommissions():
    art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    assert staticcall art_commission_hub_owners_interface.isAllowedToUpdateForAddress(msg.sender), "Not allowed to update"
    for i: uint256 in range(0, self.countUnverifiedArtCommissions, bound=10000):
        if len(self.unverifiedArtCommissions) == 0:
            break
        art_piece: address = self.unverifiedArtCommissions.pop()
        self.unverifiedArtCommissionsRegistry[art_piece] = False
    self.countUnverifiedArtCommissions = 0
