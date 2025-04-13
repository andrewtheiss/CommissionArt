# @version 0.4.1
# Contains a list of NFTs that the owner has registered
# Allows for verification of the commissions
# Allows for creation of a new commission


owner: public(address)
nft_contract: public(address)
token_id: public(uint256)
registry: public(address)
is_initialized: public(bool)
imageDataContracts: public(HashMap[uint256, address])
l1_contract: public(address)  # Address of the NFT contract on L1
is_ownership_rescinded: public(bool)  # Flag to track if ownership has been rescinded

event OwnershipRescinded:
    previous_owner: indexed(address)

event L1ContractSet:
    l1_contract: indexed(address)

event Initialized:
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    registry: indexed(address)

event OwnershipUpdated:
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address

@deploy
def __init__():
    self.owner = msg.sender
    self.is_ownership_rescinded = False
    self.l1_contract = empty(address)
    self.is_initialized = False

@external
def initialize(nft_contract: address, token_id: uint256, registry: address):
    assert not self.is_initialized, "Already initialized"
    self.is_initialized = True
    self.nft_contract = nft_contract
    self.token_id = token_id
    self.registry = registry
    log Initialized(nft_contract=nft_contract, token_id=token_id, registry=registry)

@external
def updateRegistration(nft_contract: address, token_id: uint256, owner: address):
    assert self.is_initialized, "Not initialized"
    assert msg.sender == self.registry, "Only registry can update owner"
    assert self.nft_contract == nft_contract, "NFT contract mismatch"
    assert self.token_id == token_id, "Token ID mismatch"
    self.owner = owner
    log OwnershipUpdated(nft_contract=nft_contract, token_id=token_id, owner=owner)

@external
def registerImageData(azukiId: uint256, imageContract: address):
    # Check rescinded status first
    assert not self.is_ownership_rescinded, "Ownership has been rescinded"
    # Then check if sender is owner
    assert msg.sender == self.owner, "Only owner can register"
    # Allow reregistration
    # assert self.imageDataContracts[azukiId] == empty(address), "Azuki ID already registered"
    self.imageDataContracts[azukiId] = imageContract

@external
def setL1Contract(l1_contract_address: address):
    # Check rescinded status first
    assert not self.is_ownership_rescinded, "Ownership has been rescinded"
    # Then check if sender is owner
    assert msg.sender == self.owner, "Only owner can set L1 contract"
    assert l1_contract_address != empty(address), "Invalid L1 contract address"
    self.l1_contract = l1_contract_address
    log L1ContractSet(l1_contract_address)

@external
def rescindOwnership():
    # Check if ownership has already been rescinded first
    assert not self.is_ownership_rescinded, "Ownership already rescinded"
    # Then check if the sender is the owner
    assert msg.sender == self.owner, "Only owner can rescind ownership"
    
    # Log the event before changing state
    log OwnershipRescinded(self.owner)
    
    # Set ownership as rescinded
    self.is_ownership_rescinded = True
    self.owner = empty(address)  # Set owner to zero address