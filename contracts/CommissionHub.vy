# @version 0.4.1
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

# Track allowed ArtPiece contracts
whitelistedArtPieceContract: public(address)

# Track commissions
latestVerifiedArt: public(address[300])
verifiedArt: public(DynArray[address, 100000])
unverifiedArt: public(DynArray[address, 100000])
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

event ArtPieceContractWhitelisted:
    art_piece_contract: indexed(address)

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
    self.whitelistedArtPieceContract = empty(address)

@external
def initialize(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _registry: address):
    assert not self.isInitialized, "Already initialized"
    self.isInitialized = True
    self.chainId = _chain_id
    self.nftContract = _nft_contract
    self.tokenId = _token_id
    self.registry = _registry
    log Initialized(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, registry=_registry)

@external
def updateRegistration(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _owner: address):
    assert self.isInitialized, "Not initialized"
    assert msg.sender == self.registry, "Only registry can update owner"
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
def setWhitelistedArtPieceContract(_art_piece_contract: address):
    """
    Sets the whitelisted ArtPiece contract that can be used for submissions
    """
    # Check rescinded status first
    assert not self.isOwnershipRescinded, "Ownership has been rescinded"
    # Only owner can set the whitelisted contract
    assert msg.sender == self.owner, "Only owner can set whitelisted contract"
    assert _art_piece_contract != empty(address), "Invalid ArtPiece contract address"
    
    # Set the whitelisted contract
    self.whitelistedArtPieceContract = _art_piece_contract
    log ArtPieceContractWhitelisted(art_piece_contract=_art_piece_contract)

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

@external
def submitCommission(_art_piece: address):
    # Need to assert that the art piece is actually an art piece
    assert self._isContract(_art_piece), "Art piece is not a contract"
    
    # Check whitelisted contract (always enforced)
    assert self.whitelistedArtPieceContract != empty(address), "No ArtPiece contract whitelisted"
    assert _art_piece == self.whitelistedArtPieceContract, "Art piece is not from approved contract"

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
    
    # Check whitelisted contract (always enforced)
    assert self.whitelistedArtPieceContract != empty(address), "No ArtPiece contract whitelisted"
    assert _art_piece == self.whitelistedArtPieceContract, "Art piece is not from approved contract"
    
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
def getUnverifiedArtPieces(_start_idx: uint256, _count: uint256) -> DynArray[address, 1]:
    result: DynArray[address, 1] = []
    
    # Early return if no unverified art or start index is out of bounds
    if self.countUnverifiedCommissions == 0 or _start_idx >= self.countUnverifiedCommissions:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.countUnverifiedCommissions)
    max_items: uint256 = min(end_idx - _start_idx, 1)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=1):
        result.append(self.unverifiedArt[_start_idx + i])
    
    return result