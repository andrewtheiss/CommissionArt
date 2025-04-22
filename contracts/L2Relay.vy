# @version 0.4.1

interface ArbSys:
    def sendTxToL1(destination: address, calldataForL1: Bytes[1024]) -> uint256: payable

interface L3OwnerRegistry:
    def registerNFTOwnerFromParentChain(chain_id: uint256, nft_contract: address, token_id: uint256, owner: address): nonpayable

interface L3Inbox:
    def createRetryableTicket(
        to: address,
        l2CallValue: uint256,
        maxSubmissionCost: uint256,
        excessFeeRefundAddress: address,
        callValueRefundAddress: address,
        gasLimit: uint256,
        maxFeePerGas: uint256,
        tokenTotalFeeAmount: uint256,
        data: Bytes[1024]
    ) -> uint256: payable

# Precompile address for ArbSys on Arbitrum
ARBSYS: constant(address) = 0x0000000000000000000000000000000000000064
# L3 Inbox address for L2->L3 transactions
L3_INBOX: constant(address) = 0xA203252940839c8482dD4b938b4178f842E343D7

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

event RelayToL3Initiated:
    chain_id: indexed(uint256)
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address

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

@external
@payable
def relayToL3(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _owner: address):
    """
    Relay NFT ownership from L2 to Animechain L3 using retryable tickets
    This function will be used to forward NFT ownership data to Animechain through the L3 inbox
    """
    # Make sure we have a valid L3 contract set
    assert self.l3Contract != empty(address), "L3 contract not set"
    
    # We trust the caller, but log the relay event
    log RelayToL3Initiated(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, owner=_owner)
    
    # Compute the correct selector for the L3 OwnerRegistry function
    selector: Bytes[4] = slice(keccak256("registerNFTOwnerFromParentChain(uint256,address,uint256,address)"), 0, 4)

    # Encode parameters
    chain_id_bytes: bytes32 = convert(_chain_id, bytes32)
    nft_contract_bytes: bytes32 = convert(_nft_contract, bytes32)
    token_id_bytes: bytes32 = convert(_token_id, bytes32)
    owner_bytes: bytes32 = convert(_owner, bytes32)
    
    # Build the call data for the L3 contract
    calldata: Bytes[132] = concat(selector, chain_id_bytes, nft_contract_bytes, token_id_bytes, owner_bytes)
    
    # Default values for retryable ticket
    l2CallValue: uint256 = 0  # Usually 0 unless sending ETH to L3
    maxSubmissionCost: uint256 = 10**16  # Fixed amount (0.01 ETH) for submission cost
    gasLimit: uint256 = 300000  # Default gas limit for L3 call (can be adjusted)
    maxFeePerGas: uint256 = 2000000000  # 2 gwei default (can be adjusted)
    
    # Create retryable ticket to L3
    l3_inbox: L3Inbox = L3Inbox(L3_INBOX)
    ticket_id: Bytes[32] = raw_call(
        L3_INBOX,
        concat(
            slice(keccak256("createRetryableTicket(address,uint256,uint256,address,address,uint256,uint256,uint256,bytes)"), 0, 4),
            convert(self.l3Contract, bytes32),  # to: L3 contract address
            convert(l2CallValue, bytes32),      # l2CallValue
            convert(maxSubmissionCost, bytes32), # maxSubmissionCost
            convert(msg.sender, bytes32),       # excessFeeRefundAddress
            convert(msg.sender, bytes32),       # callValueRefundAddress
            convert(gasLimit, bytes32),         # gasLimit
            convert(maxFeePerGas, bytes32),     # maxFeePerGas
            convert(0, bytes32),                # tokenTotalFeeAmount (0 for ETH)
            convert(192, bytes32),              # data offset
            convert(len(calldata), bytes32),    # data length
            calldata                            # data
        ),
        value=msg.value,
        max_outsize=32
    )
    
    log NFTRegistered(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, owner=_owner)

