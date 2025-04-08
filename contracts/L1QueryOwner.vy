# @version 0.4.1

interface IERC721:
    def ownerOf(tokenId: uint256) -> address: view

interface IInbox:
    def createRetryableTicket(
        to: address,
        l2CallValue: uint256,
        maxSubmissionCost: uint256,
        excessFeeRefundAddress: address,
        callValueRefundAddress: address,
        gasLimit: uint256,
        maxFeePerGas: uint256,
        data: Bytes[1024]
    ) -> uint256: payable

# Inbox address on Ethereum Goerli (for Arbitrum Goerli)
INBOX: immutable(address)

# For mainnet, uncomment this line in __init__ instead of the Goerli one:
# INBOX = 0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f

@deploy
def __init__():
    INBOX = 0x6bEbC4925716945d46F0ec336d5f620C47804f00
    # For mainnet use: INBOX = 0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f

@external
@payable
def queryNFTAndSendBack(nft_contract: address, token_id: uint256, l2_receiver: address):
    """
    @notice Queries the NFT owner and sends the result to L2 via Inbox
    @param nft_contract The ERC721 NFT contract address on L1
    @param token_id The token ID to query
    @param l2_receiver The L2 contract address to receive the result
    """
    owner: address = staticcall IERC721(nft_contract).ownerOf(token_id)
    data: Bytes[1024] = concat(
        method_id("receiveResultFromL1(address)"),
        convert(owner, bytes32)
    )
    ticket_id: uint256 = extcall IInbox(INBOX).createRetryableTicket(
        l2_receiver,           # to
        0,                    # l2CallValue (no ETH sent to L2 contract)
        1000000,              # maxSubmissionCost (adjust based on testnet)
        l2_receiver,          # excessFeeRefundAddress
        l2_receiver,          # callValueRefundAddress
        100000,               # gasLimit (adjust based on L2 execution)
        1000000000,           # maxFeePerGas (1 gwei, adjust as needed)
        data,                 # calldata for L2
        value=msg.value       # ETH to cover L2 gas costs
    )
    log OwnerQueried(nft_contract=nft_contract, token_id=token_id, owner=owner, ticket_id=ticket_id)

event OwnerQueried:
    nft_contract: address
    token_id: uint256
    owner: address
    ticket_id: uint256