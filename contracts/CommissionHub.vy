# @version 0.4.1
# Contains a list of NFTs that the owner has registered
# Allows for verification of the commissions
# Allows for creation of a new commission


owner: public(address)
chainId: public(uint256)  # Added chain ID to identify which blockchain the NFT is on
nftContract: public(address)
tokenId: public(uint256)
registry: public(address)
isInitialized: public(bool)
imageDataContracts: public(HashMap[uint256, address])
l1Contract: public(address)  # Address of the NFT contract on L1
isOwnershipRescinded: public(bool)  # Flag to track if ownership has been rescinded

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

@deploy
def __init__():
    self.owner = msg.sender
    self.isOwnershipRescinded = False
    self.l1Contract = empty(address)
    self.isInitialized = False
    self.chainId = 0  # Initialize with 0 to indicate not set

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
    # assert self.imageDataContracts[_azuki_id] == empty(address), "Azuki ID already registered"
    self.imageDataContracts[_azuki_id] = _image_contract

@external
def setL1Contract(_l1_contract_address: address):
    # Check rescinded status first
    assert not self.isOwnershipRescinded, "Ownership has been rescinded"
    # Then check if sender is owner
    assert msg.sender == self.owner, "Only owner can set L1 contract"
    assert _l1_contract_address != empty(address), "Invalid L1 contract address"
    self.l1Contract = _l1_contract_address
    log L1ContractSet(_l1_contract_address)

@external
def rescindOwnership():
    # Check if ownership has already been rescinded first
    assert not self.isOwnershipRescinded, "Ownership already rescinded"
    # Then check if the sender is the owner
    assert msg.sender == self.owner, "Only owner can rescind ownership"
    
    # Log the event before changing state
    log OwnershipRescinded(self.owner)
    
    # Set ownership as rescinded
    self.isOwnershipRescinded = True
    self.owner = empty(address)  # Set owner to zero address