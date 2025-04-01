#pragma version 0.4.0

owner: public(address)
imageDataContracts: public(HashMap[uint256, address])
l1_contract: public(address)  # Address of the NFT contract on L1
is_ownership_rescinded: public(bool)  # Flag to track if ownership has been rescinded

event OwnershipRescinded:
    previous_owner: indexed(address)

event L1ContractSet:
    l1_contract: indexed(address)

@deploy
def __init__():
    self.owner = msg.sender
    self.is_ownership_rescinded = False
    self.l1_contract = empty(address)

@external
def registerImageData(azukiId: uint256, imageContract: address):
    # Check rescinded status first
    assert not self.is_ownership_rescinded, "Ownership has been rescinded"
    # Then check if sender is owner
    assert msg.sender == self.owner, "Only owner can register"
    assert self.imageDataContracts[azukiId] == empty(address), "Azuki ID already registered"
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