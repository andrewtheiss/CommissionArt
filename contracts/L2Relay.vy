# @version 0.4.1

interface ArbSys:
    def sendTxToL1(destination: address, calldataForL1: Bytes[1024]) -> uint256: payable

interface L3Registrar:
    def registerNFTOwnerFromParentChain(nft_contract: address, token_id: uint256, owner: address): nonpayable

# Precompile address for ArbSys on Arbitrum
ARBSYS: constant(address) = 0x0000000000000000000000000000000000000064

event L3RegistrarSet:
    l3_registrar: indexed(address)

event NFTRegistered:
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: indexed(address)
    
event RequestSent:
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    unique_id: uint256

event OwnerReceived:
    owner: address
    
# Storage variables for contract addresses
l1_helper_contract: public(address)
l3_contract: public(address)
owner: public(address)

@deploy
def __init__(initial_l1_helper: address, initial_l3_contract: address):
    self.l1_helper_contract = initial_l1_helper
    self.l3_contract = initial_l3_contract # Owner Registry contract
    self.owner = msg.sender

@external
def setL1Helper(new_l1_helper: address):
    assert msg.sender == self.owner, "Only owner can update"
    self.l1_helper_contract = new_l1_helper

@external
def setL3Contract(new_l3_contract: address):
    assert msg.sender == self.owner, "Only owner can update"
    self.l3_contract = new_l3_contract

@external
def receiveNFTOwnerFromL1(nft_contract: address, token_id: uint256, owner: address):
    assert msg.sender == self.l1_helper_contract, "Only L1 helper contract can call this"
    registrar: L3Registrar = L3Registrar(self.l3_contract)
    extcall registrar.registerNFTOwnerFromParentChain(nft_contract, token_id, owner)
    log NFTRegistered(nft_contract=nft_contract, token_id=token_id, owner=owner)

# This gets stuck in the inbox and requires a manual execution on L1 to get the result
# Might as well just call the L1 contract directly
@external
@payable
def requestNFTOwnerFromL1(nft_contract: address, token_id: uint256) -> uint256:
    data: Bytes[1024] = concat(
        method_id("queryNFTAndSendBack(address,uint256,address)"),
        convert(nft_contract, bytes32),
        convert(token_id, bytes32),
        convert(self, bytes32)  # L2 contract as receiver
    )
    unique_id: uint256 = extcall ArbSys(ARBSYS).sendTxToL1(self.l1_helper_contract, data, value=msg.value)
    log RequestSent(nft_contract=nft_contract, token_id=token_id, unique_id=unique_id)
    return unique_id
