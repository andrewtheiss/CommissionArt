# @version 0.4.1

# MockERC20 for testing purposes
# Simple ERC20 implementation with mint function

from ethereum.ercs import IERC20

implements: IERC20

# State variables
name: public(String[50])
symbol: public(String[10])
decimals: public(uint8)
totalSupply: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])

# Events
event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

@deploy
def __init__(_name: String[50], _symbol: String[10], _decimals: uint8):
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals
    self.totalSupply = 0

@external
def transfer(_to: address, _value: uint256) -> bool:
    assert _to != empty(address), "Cannot transfer to zero address"
    assert self.balanceOf[msg.sender] >= _value, "Insufficient balance"
    
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    
    log Transfer(sender=msg.sender, receiver=_to, value=_value)
    return True

@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    assert _to != empty(address), "Cannot transfer to zero address"
    assert self.balanceOf[_from] >= _value, "Insufficient balance"
    assert self.allowance[_from][msg.sender] >= _value, "Allowance exceeded"
    
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowance[_from][msg.sender] -= _value
    
    log Transfer(sender=_from, receiver=_to, value=_value)
    return True

@external
def approve(_spender: address, _value: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _value
    log Approval(owner=msg.sender, spender=_spender, value=_value)
    return True

@external
def mint(_to: address, _value: uint256):
    """Mint new tokens - for testing purposes only"""
    assert _to != empty(address), "Cannot mint to zero address"
    
    self.totalSupply += _value
    self.balanceOf[_to] += _value
    
    log Transfer(sender=empty(address), receiver=_to, value=_value) 