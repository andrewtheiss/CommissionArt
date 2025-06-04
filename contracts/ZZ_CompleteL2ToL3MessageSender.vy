# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# Simple L2 to L3 Message Sender Contract
# Sends messages from L2 (Arbitrum) to L3 (AnimeChain) - Both on Mainnet
# 
# CONFIRMED MAINNET ADDRESSES:
# L3 Inbox: 0xA203252940839c8482dD4b938b4178f842E343D7
# L3 Target Deployed Test Contract: 0x08Fa26D7C129Ea51CCFf87109C382a532605E120
# ANIME Token (L2): 0x37a645648dF29205C6261289983FB04ECD70b4B3
# Currently deployed on L2 At 0xa46E204B8cD37959c0e4C3082c8830eFa160dc14

interface IERC20:
    def approve(spender: address, amount: uint256) -> bool: nonpayable


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

# Confirmed working L3 Inbox address from mainnet transactions
INBOX: constant(address) = 0xA203252940839c8482dD4b938b4178f842E343D7

# ANIME token address on Arbitrum L2
ANIME_TOKEN: constant(address) = 0x37a645648dF29205C6261289983FB04ECD70b4B3

@deploy
def __init__():
    """
    @notice Initialize the L2 to L3 message sender contract
    """
    pass

@external
def approveMaxAnimeForMessaging():
    """
    @notice Approve this contract to spend maximum ANIME tokens for L2 to L3 messaging
    @dev Sets allowance to maximum uint256 value for convenience
    """
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    max_amount: uint256 = max_value(uint256)
    success: bool = extcall anime_token.approve(self, max_amount)
    assert success, "ANIME token approval failed"
    
    log AnimeApprovedForMessaging(
        user=msg.sender,
        amount=max_amount
    )

@external
@payable
def sendMessageToL3(
    _l3_receiver: address,              # The L3 contract address to receive the message
    _user_input_address: address,       # The address parameter to pass to the L3 contract
    _l3_call_value: uint256,           # ETH value to send with the L3 call (usually 0)
    _max_submission_cost: uint256,      # Maximum cost for submitting the retryable ticket (e.g., 0.01 ETH = 10**16)
    _gas_limit: uint256,               # Gas limit for L3 execution (e.g., 300000)
    _max_fee_per_gas: uint256          # Maximum fee per gas for L3 execution (e.g., 2000000000 = 2 gwei)
    ):
    """
    @notice Send L2 to L3 message with full parameter control
    @dev Creates retryable ticket to send crossChainUpdate message to L3
    @param _l3_receiver The L3 contract address to receive the message (use 0x08Fa26D7C129Ea51CCFf87109C382a532605E120 for mainnet)
    @param _user_input_address The address to pass as parameter to crossChainUpdate function on L3
    @param _l3_call_value The ETH value to send with the L3 call (typically 0)
    @param _max_submission_cost Maximum cost for submitting the retryable ticket to L3
    @param _gas_limit Gas limit for the L3 execution
    @param _max_fee_per_gas Maximum fee per gas for L3 execution
    """
    
    # Create function selector for crossChainUpdate(address)
    func_selector: Bytes[4] = slice(keccak256("crossChainUpdate(address)"), 0, 4)
    
    # Encode the user input address as the parameter
    data: Bytes[36] = concat(
        func_selector,
        convert(_user_input_address, bytes32)
    )

    assert msg.value >= _l3_call_value, "Insufficient ETH for l3CallValue"
    
    # Create retryable ticket to L3
    ticket_id: uint256 = extcall IERC20Inbox(INBOX).createRetryableTicket(
        _l3_receiver,           # L3 contract address to receive the call
        _l3_call_value,         # ETH to send with L3 call (usually 0)
        _max_submission_cost,   # Cost to submit ticket (e.g., 0.01 ETH = 10**16)
        msg.sender,             # Excess fee refund address (caller)
        msg.sender,             # Call value refund address (caller)
        _gas_limit,             # Gas limit for L3 execution (e.g., 300000)
        _max_fee_per_gas,       # Max fee per gas (e.g., 2000000000 = 2 gwei)
        data,                   # Encoded function call data
        value=msg.value         # Total ETH sent (covers submission + gas costs)
    )
    
    log L2ToL3MessageSent(
        l3_receiver=_l3_receiver, 
        user_input_address=_user_input_address, 
        sender=msg.sender, 
        ticket_id=ticket_id
    )

# ========== EVENTS ==========

event AnimeApprovedForMessaging:
    user: indexed(address)
    amount: uint256

event L2ToL3MessageSent:
    l3_receiver: indexed(address)
    user_input_address: indexed(address)
    sender: address
    ticket_id: uint256 