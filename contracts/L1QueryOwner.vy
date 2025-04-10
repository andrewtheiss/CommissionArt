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

# Inbox address on Ethereum (Arbitrum bridge)
INBOX: immutable(address)

@deploy
def __init__(inbox_address: address):
    """
    @notice Initialize the contract with the Inbox address
    @param inbox_address The Arbitrum Inbox contract address
    """
    INBOX = inbox_address
    # Example values:
    # Sepolia: 0x6c97864CE4bEf387dE0b3310A44230f7E3F1be0D
    # Mainnet: 0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6

@external
@payable
def queryNFTAndSendBack(nft_contract: address, token_id: uint256, l2_receiver: address,
                        max_submission_cost: uint256 = 1000000, gas_limit: uint256 = 100000,
                        max_fee_per_gas: uint256 = 1000000000):
    """
    @notice Queries the NFT owner and sends the result to L2 via Inbox
    @param nft_contract The ERC721 NFT contract address on L1
    @param token_id The token ID to query
    @param l2_receiver The L2 contract address to receive the result
    @param max_submission_cost The maximum cost of submitting the retryable ticket (in wei)
    @param gas_limit The gas limit for executing the message on L2
    @param max_fee_per_gas The maximum fee per gas for L2 execution (in wei)
    """
    owner: address = staticcall IERC721(nft_contract).ownerOf(token_id)
    
    # Create calldata with method selector and parameter
    data: Bytes[1024] = concat(
        method_id("receiveResultFromL1(address)"),
        convert(owner, bytes32)
    )
    
    # Calculate minimum required ETH
    min_required_eth: uint256 = max_submission_cost + (gas_limit * max_fee_per_gas)
    
    # Ensure enough ETH is provided
    assert msg.value >= min_required_eth, "Insufficient ETH for gas costs"
    
    # Create the retryable ticket
    ticket_id: uint256 = extcall IInbox(INBOX).createRetryableTicket(
        l2_receiver,           # to address (L2 contract)
        0,                     # l2CallValue (no ETH value for call)
        max_submission_cost,   # maxSubmissionCost
        msg.sender,            # excessFeeRefundAddress
        msg.sender,            # callValueRefundAddress
        gas_limit,             # gasLimit
        max_fee_per_gas,       # maxFeePerGas
        data,                  # calldata with nft owner
        value=msg.value        # total ETH for transaction
    )
    
    # Log the event
    log OwnerQueried(nft_contract=nft_contract, token_id=token_id, owner=owner, ticket_id=ticket_id)

event OwnerQueried:
    nft_contract: address
    token_id: uint256
    owner: address
    ticket_id: uint256