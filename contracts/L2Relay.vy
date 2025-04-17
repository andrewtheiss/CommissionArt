# @version 0.4.1

interface ArbSys:
    def sendTxToL1(destination: address, calldataForL1: Bytes[1024]) -> uint256: payable

# Precompile address for ArbSys on Arbitrum
ARBSYS: constant(address) = 0x0000000000000000000000000000000000000064

event NFTRegistered:
    chain_id: indexed(uint256)
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address
    
event RequestSent:
    chain_id: indexed(uint256)
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    unique_id: uint256

event OwnerReceived:
    owner: address

event CrossChainSenderAdded:
    sender: indexed(address)
    chain_id: indexed(uint256)

event OwnerRevoked:
    previous_owner: indexed(address)

# Whitelist of cross-chain message senders and the chain_id they are allowed to send from
crossChainRegistryAddressByChainId: public(HashMap[uint256, address])
l3Contract: public(address)
owner: public(address)
isOwnerRevoked: public(bool)

@deploy
def __init__():
    self.l3Contract = 0x0000000000000000000000000000000000000000 # Owner Registry contract
    self.owner = msg.sender
    self.isOwnerRevoked = False

@external
def setL3Contract(_new_l3_contract: address):
    assert msg.sender == self.owner and not self.isOwnerRevoked, "Only active owner can update"
    self.l3Contract = _new_l3_contract

@external
def receiveNFTOwnerFromCrossChainMessage(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _owner: address):
    assert self.crossChainRegistryAddressByChainId[_chain_id] == msg.sender, "Sender not whitelisted for this chain"
  
    # Compute the correct selector
    selector: Bytes[4] = slice(keccak256("registerNFTOwnerFromParentChain(uint256,address,uint256,address)"), 0, 4)

    # Encode parameters
    chain_id_bytes: bytes32 = convert(_chain_id, bytes32)
    nft_contract_bytes: bytes32 = convert(_nft_contract, bytes32)
    token_id_bytes: bytes32 = convert(_token_id, bytes32)
    owner_bytes: bytes32 = convert(_owner, bytes32)
    
    # Build the call data
    data: Bytes[132] = concat(selector, chain_id_bytes, nft_contract_bytes, token_id_bytes, owner_bytes)
    
    # Make the raw call
    raw_call(self.l3Contract, data, max_outsize=0)
    log NFTRegistered(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, owner=_owner)

@external
def updateCrossChainQueryOwnerContract(_aliased_cross_chain_sender: address, _chain_id: uint256):
    assert msg.sender == self.owner and not self.isOwnerRevoked, "Only active owner can add whitelisted senders"
    self.crossChainRegistryAddressByChainId[_chain_id] = _aliased_cross_chain_sender
    log CrossChainSenderAdded(sender=_aliased_cross_chain_sender, chain_id=_chain_id)

# Make this truly decentralized by removing the owner
@external
def revokeOwner():
    assert msg.sender == self.owner and not self.isOwnerRevoked, "Only active owner can revoke ownership"
    self.isOwnerRevoked = True
    log OwnerRevoked(previous_owner=self.owner)

