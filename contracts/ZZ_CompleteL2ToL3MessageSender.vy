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
    def balanceOf(owner: address) -> uint256: view
    def transfer(to: address, amount: uint256) -> bool: nonpayable
    def allowance(owner: address, spender: address) -> uint256: view


# Confirmed working L3 Inbox address from mainnet transactions
# Need to approve this Inbox to spend ANIME tokens for L2 to L3 messaging
INBOX: constant(address) = 0xA203252940839c8482dD4b938b4178f842E343D7

# ANIME token address on Arbitrum L2
ANIME_TOKEN: constant(address) = 0x37a645648dF29205C6261289983FB04ECD70b4B3

# State variables for access control
owner: public(address)
whitelisted: public(HashMap[address, bool])

@deploy
def __init__():
    self.owner = msg.sender
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    max_amount: uint256 = max_value(uint256)
    success: bool = extcall anime_token.approve(INBOX, max_amount)
    self.whitelisted[msg.sender] = True

@internal
def _allowedAccess():
    """
    @notice Internal method to check if caller has whitelisted access
    @dev Reverts if msg.sender is not whitelisted
    """
    assert self.whitelisted[msg.sender], "Access denied: caller not whitelisted"

@external
@view
def getAnimeBalance() -> uint256:
    """
    @notice Get the ANIME token balance of this contract
    @return The amount of ANIME tokens held by this contract
    """
    assert msg.sender == self.owner
    
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    return staticcall anime_token.balanceOf(self)

# ========== EVENTS ==========


@external
def sendRetryableTicketToCrossChainUpdateMethod(
    _l3_deliver_to: address, 
    _gas_limit: uint256, 
    _max_fee_per_gas: uint256, 
    _token_total_fee_amount: uint256,
    _cross_chain_update_input: address):
    """
    @notice Send a retryable ticket with hardcoded parameters using direct raw call
    @dev Calls createRetryableTicket directly on the INBOX contract with specific parameters
    """
    self._allowedAccess()
    
    # Hardcoded parameters
    to: address = _l3_deliver_to # 0x96eF33e25FdDA3808F35CC5fa62286120FF285a9
    l2_call_value: uint256 = 0
    max_submission_cost: uint256 = 20000000000000  # 0.00002 ETH
    excess_fee_refund_address: address = 0x2D68643fC11D8952324ca051fFa5c7DB5F9219D8 # hard code deployer for now
    call_value_refund_address: address = 0x2D68643fC11D8952324ca051fFa5c7DB5F9219D8 # hard code deployer for now
    gas_limit: uint256 = _gas_limit # 180000
    max_fee_per_gas: uint256 = _max_fee_per_gas # 500000000000  # 500 gwei
    token_total_fee_amount: uint256 = _token_total_fee_amount# 100000000000000000  # 0.1 tokens
    
    # Hardcoded data: 0x73252838000000000000000000000000aca5be80ce2db9cf01530d95bc80c1f1db7071fa
    func_selector: bytes4 = 0x73252838  # crossChainUpdate(address)
    
    # Create 12 bytes of zeros for LEFT padding (this is the key!)
    zeros: bytes32 = empty(bytes32)  # All zeros
    padding: Bytes[12] = slice(zeros, 0, 12)


    # CORRECT - slice directly from the bytes32
    addr_bytes: Bytes[20] = slice(
        convert(_cross_chain_update_input, bytes32),
        0,
        20
    )

    
    
    # Construct properly encoded calldata: selector + padding + address
    l3_calldata: Bytes[36] = concat(
        func_selector,      # 4 bytes: 73252838
        padding,            # 12 bytes: 000000000000000000000000
        addr_bytes          # 20 bytes: aca5be80ce2db9cf01530d95bc80c1f1db7071fa
    )


    method_sig: bytes4 = 0x549e8426
    # Encode all parameters
    encoded_call: Bytes[1024] = concat(  # was 420 exactly
        method_sig,
        convert(to, bytes32),  # to
        convert(0, bytes32),  # l2CallValue
        convert(max_submission_cost, bytes32),  # maxSubmissionCost
        convert(excess_fee_refund_address, bytes32),  # excessFeeRefundAddress
        convert(call_value_refund_address, bytes32),  # callValueRefundAddress
        convert(gas_limit, bytes32),  # gasLimit
        convert(max_fee_per_gas, bytes32),  # maxFeePerGas
        convert(token_total_fee_amount, bytes32),  # tokenTotalFeeAmount
        convert(288, bytes32),  # offset pointer that tells the decoder where the dynamic data begins
        convert(36, bytes32),  # length of that dynamic byte array
        l3_calldata
    )

    # Make the call
    response: Bytes[32] = raw_call(
        INBOX,
        encoded_call,
        max_outsize=32,
        value=0,
        revert_on_failure=True
    )
    
    ticket_id: uint256 = convert(response, uint256)
    

@external
@view
def checkAllowance() -> uint256:
    """Check current ANIME allowance to INBOX"""
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    return staticcall anime_token.allowance(self, INBOX)

@external
def withdrawAllAnime():
    """
    @notice Withdraw all ANIME tokens from this contract to the owner
    @dev Only the owner can call this function to recover accumulated ANIME tokens
    """
    assert msg.sender == self.owner, "Only owner can withdraw ANIME tokens"
    
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    current_balance: uint256 = staticcall anime_token.balanceOf(self)
    
    assert current_balance > 0, "No ANIME tokens to withdraw"
    
    # Transfer all ANIME tokens to the owner
    success: bool = extcall anime_token.transfer(self.owner, current_balance)
    assert success, "ANIME token transfer failed"
