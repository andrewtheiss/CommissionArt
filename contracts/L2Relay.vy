# @version 0.4.1

interface ArbSys:
    def sendTxToL1(destination: address, calldataForL1: Bytes[1024]) -> uint256: payable

interface L3Registrar:
    def registerNFTOwnerFromParentChain(chain_id: uint256, nft_contract: address, token_id: uint256, owner: address): nonpayable

# Precompile address for ArbSys on Arbitrum
ARBSYS: constant(address) = 0x0000000000000000000000000000000000000064

event L3RegistrarSet:
    l3_registrar: indexed(address)

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
    registrar: L3Registrar = L3Registrar(self.l3Contract)
    extcall registrar.registerNFTOwnerFromParentChain(_chain_id, _nft_contract, _token_id, _owner)
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

