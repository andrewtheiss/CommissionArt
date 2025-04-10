# @version 0.4.1

interface ArbSys:
    def sendTxToL1(destination: address, calldataForL1: Bytes[1024]) -> uint256: payable

# Precompile address for ArbSys on Arbitrum
ARBSYS: constant(address) = 0x0000000000000000000000000000000000000064

# Storage variables for contract addresses
l1_helper_contract: public(address)
l3_contract: public(address)
owner: public(address)

@deploy
def __init__(initial_l1_helper: address, initial_l3_contract: address):
    self.l1_helper_contract = initial_l1_helper
    self.l3_contract = initial_l3_contract
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
@payable
def requestNFTOwner(nft_contract: address, token_id: uint256) -> uint256:
    data: Bytes[1024] = concat(
        method_id("queryNFTAndSendBack(address,uint256,address)"),
        convert(nft_contract, bytes32),
        convert(token_id, bytes32),
        convert(self, bytes32)  # L2 contract as receiver
    )
    unique_id: uint256 = extcall ArbSys(ARBSYS).sendTxToL1(self.l1_helper_contract, data, value=msg.value)
    log RequestSent(nft_contract=nft_contract, token_id=token_id, unique_id=unique_id)
    return unique_id

@external
def receiveResultFromL1(owner: address):
    # For now, log the result; later, forward to L3
    log OwnerReceived(owner=owner)

event RequestSent:
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    unique_id: uint256

event OwnerReceived:
    owner: address