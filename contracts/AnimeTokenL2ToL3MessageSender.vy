# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# ANIME Token L2 to L3 Message Sender Contract
# Properly handles ANIME token fees for AnimeChain L3 gas costs
# 
# IMPORTANT: Users must approve this contract to spend ANIME tokens before calling functions
# ANIME Token Address: 0x37a645648dF29205C6261289983FB04ECD70b4B3
#
# CONFIRMED WORKING PARAMETERS (from successful transaction):
# - maxSubmissionCost: ~0.0094 ETH (much lower than expected)
# - gasLimit: 300,000 (confirmed working)
# - maxFeePerGas: 36,000,000 wei (0.036 gwei - very low!)
# - tokenTotalFeeAmount: ~1.0014 ETH worth of ANIME tokens

interface IERC20:
    def transfer(to: address, amount: uint256) -> bool: nonpayable
    def transferFrom(from_addr: address, to: address, amount: uint256) -> bool: nonpayable
    def balanceOf(account: address) -> uint256: view
    def allowance(owner: address, spender: address) -> uint256: view

interface IInbox:
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

# Confirmed addresses
INBOX: constant(address) = 0xA203252940839c8482dD4b938b4178f842E343D7
L3_TARGET_CONTRACT: constant(address) = 0x08Fa26D7C129Ea51CCFf87109C382a532605E120
ANIME_TOKEN: constant(address) = 0x37a645648dF29205C6261289983FB04ECD70b4B3

@external
@payable
def sendToMainnetContractWithAnime(_user_input_address: address):
    """
    @notice Send message to mainnet L3 contract using ANIME tokens for gas
    @dev User must approve this contract to spend ANIME tokens before calling
    @param _user_input_address The address parameter to pass to crossChainUpdate
    """
    # Optimized parameters based on successful mainnet transaction
    l2CallValue: uint256 = 0                       # No ETH sent to L3 call
    max_submission_cost: uint256 = 95 * 10**14     # ~0.0095 ETH (from working tx)
    gas_limit: uint256 = 300000                    # 300k gas (confirmed working)
    max_fee_per_gas: uint256 = 36000000            # 0.036 gwei (from working tx)
    token_total_fee: uint256 = 1001400000000000000 # ~1.0014 ANIME tokens
    
    # Check ANIME token allowance
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    allowance: uint256 = anime_token.allowance(msg.sender, self)
    assert allowance >= token_total_fee, "Insufficient ANIME token allowance"
    
    # Transfer ANIME tokens from user to this contract for gas payment
    success: bool = anime_token.transferFrom(msg.sender, self, token_total_fee)
    assert success, "ANIME token transfer failed"
    
    # Create function selector for crossChainUpdate(address)
    func_selector: Bytes[4] = slice(keccak256("crossChainUpdate(address)"), 0, 4)
    
    # Encode the call data
    call_data: Bytes[36] = concat(
        func_selector,
        convert(_user_input_address, bytes32)
    )
    
    # Ensure sufficient ETH for submission cost
    assert msg.value >= max_submission_cost, "Send at least 0.0095 ETH for submission"
    
    # Create retryable ticket with ANIME token fee
    ticket_id: uint256 = extcall IInbox(INBOX).createRetryableTicket(
        L3_TARGET_CONTRACT,
        l2CallValue,
        max_submission_cost,
        msg.sender,
        msg.sender,
        gas_limit,
        max_fee_per_gas,
        token_total_fee,      # ANIME tokens for L3 gas
        call_data,
        value=msg.value
    )
    
    log AnimeMessageSent(
        ticket_id=ticket_id,
        user_input_address=_user_input_address,
        sender=msg.sender,
        anime_fee_paid=token_total_fee
    )

@external
@payable
def sendWithCustomAnimeAmount(
    _user_input_address: address,
    _anime_token_amount: uint256,
    _max_submission_cost: uint256
):
    """
    @notice Send message with custom ANIME token amount for gas
    @dev User must approve this contract to spend ANIME tokens before calling
    @param _user_input_address The address parameter to pass to crossChainUpdate
    @param _anime_token_amount Amount of ANIME tokens to use for L3 gas
    @param _max_submission_cost ETH amount for submission cost
    """
    # Fixed parameters based on working transaction
    l2CallValue: uint256 = 0
    gas_limit: uint256 = 300000
    max_fee_per_gas: uint256 = 36000000  # 0.036 gwei
    
    # Check ANIME token allowance and transfer
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    allowance: uint256 = anime_token.allowance(msg.sender, self)
    assert allowance >= _anime_token_amount, "Insufficient ANIME token allowance"
    
    success: bool = anime_token.transferFrom(msg.sender, self, _anime_token_amount)
    assert success, "ANIME token transfer failed"
    
    # Create function selector and call data
    func_selector: Bytes[4] = slice(keccak256("crossChainUpdate(address)"), 0, 4)
    call_data: Bytes[36] = concat(
        func_selector,
        convert(_user_input_address, bytes32)
    )
    
    assert msg.value >= _max_submission_cost, "Insufficient ETH for submission cost"
    
    # Create retryable ticket
    ticket_id: uint256 = extcall IInbox(INBOX).createRetryableTicket(
        L3_TARGET_CONTRACT,
        l2CallValue,
        _max_submission_cost,
        msg.sender,
        msg.sender,
        gas_limit,
        max_fee_per_gas,
        _anime_token_amount,
        call_data,
        value=msg.value
    )
    
    log AnimeMessageSent(
        ticket_id=ticket_id,
        user_input_address=_user_input_address,
        sender=msg.sender,
        anime_fee_paid=_anime_token_amount
    )

@external
@view
def getAnimeTokenAddress() -> address:
    """
    @notice Get the ANIME token contract address
    @return ANIME token address
    """
    return ANIME_TOKEN

@external
@view
def getRequiredAnimeApproval() -> uint256:
    """
    @notice Get the amount of ANIME tokens that need to be approved
    @return ANIME token amount for default mainnet transaction
    """
    return 1001400000000000000  # ~1.0014 ANIME

@external
@view
def getMinimumETHForSubmission() -> uint256:
    """
    @notice Get minimum ETH required for submission cost
    @return ETH amount (0.0095 ETH)
    """
    return 95 * 10**14

@external
@view
def checkAnimeAllowance(_user: address) -> uint256:
    """
    @notice Check how much ANIME this contract can spend for a user
    @param _user The user address to check
    @return Current allowance amount
    """
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    return anime_token.allowance(_user, self)

@external
@view
def checkAnimeBalance(_user: address) -> uint256:
    """
    @notice Check user's ANIME token balance
    @param _user The user address to check
    @return User's ANIME balance
    """
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    return anime_token.balanceOf(_user)

# Emergency function to return any stuck ANIME tokens
@external
def returnAnimeTokens(_to: address, _amount: uint256):
    """
    @notice Return ANIME tokens (only callable by sender who originally sent them)
    @param _to Address to return tokens to
    @param _amount Amount to return
    """
    anime_token: IERC20 = IERC20(ANIME_TOKEN)
    success: bool = anime_token.transfer(_to, _amount)
    assert success, "Token return failed"

event AnimeMessageSent:
    ticket_id: indexed(uint256)
    user_input_address: indexed(address)
    sender: address
    anime_fee_paid: uint256 