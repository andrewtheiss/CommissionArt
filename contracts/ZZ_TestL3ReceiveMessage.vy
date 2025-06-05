# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# Interface for ERC20 tokens
interface IERC20:
    def transfer(to: address, amount: uint256) -> bool: nonpayable
    def balanceOf(account: address) -> uint256: view

# Global counter that increments with each crossChainUpdate call
counter: public(uint256)

# Hashmap to store msg.sender for each crossChainUpdate call
# Key is the counter value, value is the sender address
senderHistory: public(HashMap[uint256, address])

# Hashmap to store user input addresses for each crossChainUpdate call
# Key is the counter value, value is the user input address
userInputAddress: public(HashMap[uint256, address])

event CrossChainUpdateReceived:
    updateNumber: indexed(uint256)
    sender: indexed(address)
    inputAddress: indexed(address)

event FundsDrained:
    drainer: indexed(address)
    amount: uint256
    token: indexed(address)  # zero address for native tokens

@deploy
def __init__():
    """
    @notice Initialize the contract with counter starting at 0
    """
    self.counter = 0

@external
@payable
def crossChainUpdate(_user_input_address: address):
    """
    @notice Public function that can be called by anyone to update the counter
    @dev Increments the global counter and stores both msg.sender and input address in hashmaps
    @param _user_input_address The address provided by the user as input
    @dev Now payable to receive native tokens from retryable tickets
    """
    # Increment the counter first
    self.counter += 1
    
    # Store the sender address using the current counter value as key
    self.senderHistory[self.counter] = msg.sender
    
    # Store the user input address using the current counter value as key
    self.userInputAddress[self.counter] = _user_input_address
    
    # Emit event for tracking
    log CrossChainUpdateReceived(updateNumber=self.counter, sender=msg.sender, inputAddress=_user_input_address)

@external
def drainNativeTokens():
    """
    @notice Drain all native tokens from this contract to msg.sender
    @dev Anyone can call this function to recover stuck native tokens
    """
    balance: uint256 = self.balance
    if balance > 0:
        raw_call(msg.sender, b"", value=balance)
        log FundsDrained(drainer=msg.sender, amount=balance, token=empty(address))

@external
@view
def getCurrentCounter() -> uint256:
    """
    @notice Get the current counter value
    @return The current counter value
    """
    return self.counter

@external
@view
def getSenderAtUpdate(_update_number: uint256) -> address:
    """
    @notice Get the sender address for a specific update number
    @param _update_number The update number to query
    @return The sender address for that update, or zero address if not found
    """
    return self.senderHistory[_update_number]

@external
@view
def getUserInputAddressAtUpdate(_update_number: uint256) -> address:
    """
    @notice Get the user input address for a specific update number
    @param _update_number The update number to query
    @return The user input address for that update, or zero address if not found
    """
    return self.userInputAddress[_update_number]

@external
@view
def getContractBalance() -> uint256:
    """
    @notice Get the current native token balance of this contract
    @return The contract's native token balance
    """
    return self.balance
