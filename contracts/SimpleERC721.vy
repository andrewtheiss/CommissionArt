# @version 0.4.1

"""
@title Simple ERC721 Contract for Testing
@notice A basic implementation of ERC721 for testing purposes
"""

# Contract interfaces
interface ERC721Receiver:
    def onERC721Received(operator: address, sender: address, tokenId: uint256, data: Bytes[1024]) -> bytes4: view

# Events
event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    tokenId: indexed(uint256)

event Approval:
    owner: indexed(address)
    approved: indexed(address)
    tokenId: indexed(uint256)

event ApprovalForAll:
    owner: indexed(address)
    operator: indexed(address)
    approved: bool

# State variables
name: public(String[32])
symbol: public(String[8])
owner: public(address)

# Token ID to owner address mapping
ownerOf: public(HashMap[uint256, address])

# Owner address to token count mapping
balanceOf: public(HashMap[address, uint256])

# Token ID to approved address mapping
getApproved: public(HashMap[uint256, address])

# Owner to operator approvals mapping
isApprovedForAll: public(HashMap[address, HashMap[address, bool]])

# ERC721 interface ID
INTERFACE_ID_ERC721: constant(bytes4) = 0x80ac58cd

# ERC165 interface ID
INTERFACE_ID_ERC165: constant(bytes4) = 0x01ffc9a7

@deploy
def __init__(_name: String[32], _symbol: String[8]):
    self.name = _name
    self.symbol = _symbol
    self.owner = msg.sender

@external
def supportsInterface(_interface_id: bytes4) -> bool:
    return _interface_id == INTERFACE_ID_ERC721 or _interface_id == INTERFACE_ID_ERC165

@external
def mint(_to: address, _token_id: uint256):
    """
    @notice Mint a new token
    @param _to The receiver of the token
    @param _token_id The token ID to mint
    """
    assert msg.sender == self.owner, "Only owner can mint"
    assert _to != empty(address), "Invalid receiver"
    assert self.ownerOf[_token_id] == empty(address), "Token already exists"

    self.balanceOf[_to] += 1
    self.ownerOf[_token_id] = _to

    log Transfer(sender=empty(address), receiver=_to, tokenId=_token_id)

@external
def transferFrom(_from_address: address, _to: address, _token_id: uint256):
    """
    @notice Transfer a token
    @param _from_address The current owner
    @param _to The new owner
    @param _token_id The token ID
    """
    assert self._isApprovedOrOwner(msg.sender, _token_id), "Not approved or owner"
    assert _from_address == self.ownerOf[_token_id], "Not the owner"
    assert _to != empty(address), "Invalid receiver"

    # Clear approvals
    self.getApproved[_token_id] = empty(address)

    # Update balances
    self.balanceOf[_from_address] -= 1
    self.balanceOf[_to] += 1
    
    # Update ownership
    self.ownerOf[_token_id] = _to

    log Transfer(sender=_from_address, receiver=_to, tokenId=_token_id)

@external
def safeTransferFrom(_from_address: address, _to: address, _token_id: uint256, _data: Bytes[1024] = b""):
    """
    @notice Safely transfer a token
    @param _from_address The current owner
    @param _to The new owner
    @param _token_id The token ID
    @param _data Additional data with no specified format
    """
    # Instead of calling self.transferFrom, implement the logic directly
    assert self._isApprovedOrOwner(msg.sender, _token_id), "Not approved or owner"
    assert _from_address == self.ownerOf[_token_id], "Not the owner"
    assert _to != empty(address), "Invalid receiver"

    # Clear approvals
    self.getApproved[_token_id] = empty(address)

    # Update balances
    self.balanceOf[_from_address] -= 1
    self.balanceOf[_to] += 1
    
    # Update ownership
    self.ownerOf[_token_id] = _to

    log Transfer(sender=_from_address, receiver=_to, tokenId=_token_id)
    
    if self._isContract(_to):
        returnValue: bytes4 = staticcall ERC721Receiver(_to).onERC721Received(msg.sender, _from_address, _token_id, _data)
        assert returnValue == 0x150b7a02, "ERC721: transfer to non ERC721Receiver implementer"

@external
def approve(_approved: address, _token_id: uint256):
    """
    @notice Approve an address to transfer a token
    @param _approved The address to approve
    @param _token_id The token ID
    """
    owner: address = self.ownerOf[_token_id]
    assert owner != empty(address), "Token does not exist"
    assert msg.sender == owner or self.isApprovedForAll[owner][msg.sender], "Not owner or approved operator"
    assert _approved != owner, "Approval to current owner"
    
    self.getApproved[_token_id] = _approved
    log Approval(owner=owner, approved=_approved, tokenId=_token_id)

@external
def setApprovalForAll(_operator: address, _approved: bool):
    """
    @notice Set approval for an operator to manage all of sender's tokens
    @param _operator The operator address
    @param _approved Whether the operator is approved
    """
    assert _operator != msg.sender, "Approve to caller"
    self.isApprovedForAll[msg.sender][_operator] = _approved
    log ApprovalForAll(owner=msg.sender, operator=_operator, approved=_approved)

@internal
@view
def _isApprovedOrOwner(_spender: address, _tokenId: uint256) -> bool:
    """
    @notice Check if spender is approved or owner of token
    @param _spender The address to check
    @param _tokenId The token ID
    @return Whether spender is approved or owner
    """
    owner: address = self.ownerOf[_tokenId]
    return (
        _spender == owner or 
        self.getApproved[_tokenId] == _spender or 
        self.isApprovedForAll[owner][_spender]
    )

@internal
@view
def _isContract(_addr: address) -> bool:
    """
    @notice Check if address is a contract
    @param _addr The address to check
    @return Whether the address is a contract
    """
    size: uint256 = 0
    # Check code size at address
    if _addr != empty(address):
        if len(slice(_addr.code, 0, 1)) > 0:
            size = 1
    return size > 0 