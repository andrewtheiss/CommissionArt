# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

interface IERC20Inbox:
    def createRetryableTicket(
        to: address,
        l2CallValue: uint256,
        maxSubmissionCost: uint256,
        excessFeeRefundAddress: address,
        callValueRefundAddress: address,
        gasLimit: uint256,
        maxFeePerGas: uint256,
        data: Bytes[256]
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
    # Mainnet: 0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f
    # L2 Relay Sepolia: 

@external
@payable
def queryNFTAndSendBack(
    _nft_contract: address, 
    _token_id: uint256, 
    _l2_receiver: address,                 
    _l2CallValue: uint256,
    _max_submission_cost: uint256,
    _gas_limit: uint256,
    _max_fee_per_gas: uint256
    ):
    owner: address = staticcall IERC721(_nft_contract).ownerOf(_token_id)

    assert owner != empty(address), "NFT not owned"
    
    func_selector: Bytes[4] = slice(keccak256("receiveNFTOwnerFromCrossChainMessage(uint256,address,uint256,address,uint256,uint256,uint256)"), 0, 4)
    
    data: Bytes[256] = concat(
        func_selector,
        convert(1, bytes32),  # chain_id (Ethereum mainnet)
        convert(_nft_contract, bytes32),
        convert(_token_id, bytes32),
        convert(owner, bytes32),
        convert(_max_submission_cost, bytes32),
        convert(_gas_limit, bytes32),
        convert(_max_fee_per_gas, bytes32)
    )

    assert msg.value >= _l2CallValue, "Insufficient ETH for l2CallValue"
    
    ticket_id: uint256 = extcall IERC20Inbox(INBOX).createRetryableTicket(
        _l2_receiver,
        _l2CallValue,
        _max_submission_cost,
        msg.sender,
        msg.sender,
        _gas_limit,
        _max_fee_per_gas,
        data,
        value=msg.value
    )
    
    log OwnerQueried(chain_id=1, nft_contract=_nft_contract, token_id=_token_id, owner=owner, ticket_id=ticket_id)

@external
@view
def getInboxAddress() -> address:
    return INBOX

@internal
def _get_nft_contract_owner(nft_contract: address, token_id: uint256) -> address:
    return staticcall IERC721(nft_contract).ownerOf(token_id)

@external
@view
def getNftContractOwner(nft_contract: address, token_id: uint256) -> address:
    return staticcall IERC721(nft_contract).ownerOf(token_id)


event OwnerQueried:
    chain_id: uint256
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address
    ticket_id: uint256
