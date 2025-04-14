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
cross_chain_registry_address_by_chain_id: public(HashMap[uint256, address])
l1_helper_contract: public(address)
l3_contract: public(address)
owner: public(address)
is_owner_revoked: public(bool)

@deploy
def __init__(initial_l1_helper: address, initial_l3_contract: address):
    self.l1_helper_contract = initial_l1_helper
    self.l3_contract = initial_l3_contract # Owner Registry contract
    self.owner = msg.sender
    self.is_owner_revoked = False

@external
def setL1Helper(new_l1_helper: address):
    assert msg.sender == self.owner and not self.is_owner_revoked, "Only active owner can update"
    self.l1_helper_contract = new_l1_helper

@external
def setL3Contract(new_l3_contract: address):
    assert msg.sender == self.owner and not self.is_owner_revoked, "Only active owner can update"
    self.l3_contract = new_l3_contract

@external
def receiveNFTOwnerFromCrossChainMessage(chain_id: uint256, nft_contract: address, token_id: uint256, owner: address):
    assert self.cross_chain_registry_address_by_chain_id[chain_id] == msg.sender, "Sender not whitelisted for this chain"
    registrar: L3Registrar = L3Registrar(self.l3_contract)
    extcall registrar.registerNFTOwnerFromParentChain(chain_id, nft_contract, token_id, owner)
    log NFTRegistered(chain_id=chain_id, nft_contract=nft_contract, token_id=token_id, owner=owner)

@external
def updateCrossChainSender(sender: address, chain_id: uint256):
    assert msg.sender == self.owner and not self.is_owner_revoked, "Only active owner can add whitelisted senders"
    self.cross_chain_registry_address_by_chain_id[chain_id] = sender
    log CrossChainSenderAdded(sender=sender, chain_id=chain_id)

# Make this truly decentralized by removing the owner
@external
def revokeOwner():
    assert msg.sender == self.owner and not self.is_owner_revoked, "Only active owner can revoke ownership"
    self.is_owner_revoked = True
    log OwnerRevoked(previous_owner=self.owner)

