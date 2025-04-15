# @version 0.4.1

interface IERC20Inbox:
    def createRetryableTicket(
        to: address,
        l2CallValue: uint256,
        maxSubmissionCost: uint256,
        excessFeeRefundAddress: address,
        callValueRefundAddress: address,
        gasLimit: uint256,
        maxFeePerGas: uint256,
        data: Bytes[140]
    ) -> uint256: payable

interface IERC721:
    def ownerOf(tokenId: uint256) -> address: view

# Inbox address on Ethereum (Arbitrum bridge)
INBOX: immutable(address)

@deploy
def __init__(_inbox_address: address):
    """
    @notice Initialize the contract with the Inbox address
    @param _inbox_address The Arbitrum Inbox contract address
    """
    INBOX = _inbox_address
    # Example values:
    # Sepolia Delayed Inbox: 0xaAe29B0366299461418F5324a79Afc425BE5ae21 
    # Mainnet: 0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6
    # L2 Relay Sepolia: 

@external
@payable
def queryNFTAndSendBack(_nft_contract: address, _token_id: uint256, _l2_receiver: address,
                        _max_submission_cost: uint256 = 4500000000000,
                        _gas_limit: uint256 = 1000000,
                        _max_fee_per_gas: uint256 = 100000000):
    """
    @notice Queries the NFT owner and sends the result to L2 via Inbox
    @param _nft_contract The ERC721 NFT contract address on L1
    @param _token_id The token ID to query
    @param _l2_receiver The L2 contract address to receive the result
    @param _max_submission_cost The maximum cost of submitting the retryable ticket (in wei)
    @param _gas_limit The gas limit for executing the message on L2
    @param _max_fee_per_gas The maximum fee per gas for L2 execution (in wei)
    """
    owner: address = staticcall IERC721(_nft_contract).ownerOf(_token_id)
    
    func_selector: Bytes[4] = slice(keccak256("receiveNFTOwnerFromL1(uint256,address,uint256,address)"), 0, 4)
    
    # Construct data with chain_id=1 (Ethereum), _nft_contract, _token_id, and owner as parameters
    data: Bytes[140] = concat(
        func_selector,
        convert(1, bytes32),  # Default to Ethereum mainnet (chain ID 1)
        convert(_nft_contract, bytes32),
        convert(_token_id, bytes32),
        convert(owner, bytes32)
    )

    # Calculate minimum required ETH
    min_required_eth: uint256 = _max_submission_cost + (_gas_limit * _max_fee_per_gas)
    
    # Ensure enough ETH is provided
    assert msg.value >= min_required_eth, "Insufficient ETH for gas costs"
    
    # Create the retryable ticket
    ticket_id: uint256 = extcall IERC20Inbox(INBOX).createRetryableTicket(
        _l2_receiver,
        0,
        _max_submission_cost,
        msg.sender,
        msg.sender,
        _gas_limit,
        _max_fee_per_gas,
        data,
        value=msg.value
    )
    
    # Log the event
    log OwnerQueried(chain_id=1, nft_contract=_nft_contract, token_id=_token_id, owner=owner, ticket_id=ticket_id)

event OwnerQueried:
    chain_id: uint256
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address
    ticket_id: uint256