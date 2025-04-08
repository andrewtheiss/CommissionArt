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
def supportsInterface(interfaceId: bytes4) -> bool:
    return interfaceId == INTERFACE_ID_ERC721 or interfaceId == INTERFACE_ID_ERC165

@external
def mint(to: address, tokenId: uint256):
    """
    @notice Mint a new token
    @param to The receiver of the token
    @param tokenId The token ID to mint
    """
    assert msg.sender == self.owner, "Only owner can mint"
    assert to != empty(address), "Invalid receiver"
    assert self.ownerOf[tokenId] == empty(address), "Token already exists"

    self.balanceOf[to] += 1
    self.ownerOf[tokenId] = to

    log Transfer(sender=empty(address), receiver=to, tokenId=tokenId)

@external
def transferFrom(from_address: address, to: address, tokenId: uint256):
    """
    @notice Transfer a token
    @param from_address The current owner
    @param to The new owner
    @param tokenId The token ID
    """
    assert self._isApprovedOrOwner(msg.sender, tokenId), "Not approved or owner"
    assert from_address == self.ownerOf[tokenId], "Not the owner"
    assert to != empty(address), "Invalid receiver"

    # Clear approvals
    self.getApproved[tokenId] = empty(address)

    # Update balances
    self.balanceOf[from_address] -= 1
    self.balanceOf[to] += 1
    
    # Update ownership
    self.ownerOf[tokenId] = to

    log Transfer(sender=from_address, receiver=to, tokenId=tokenId)

@external
def safeTransferFrom(from_address: address, to: address, tokenId: uint256, data: Bytes[1024] = b""):
    """
    @notice Safely transfer a token
    @param from_address The current owner
    @param to The new owner
    @param tokenId The token ID
    @param data Additional data with no specified format
    """
    # Instead of calling self.transferFrom, implement the logic directly
    assert self._isApprovedOrOwner(msg.sender, tokenId), "Not approved or owner"
    assert from_address == self.ownerOf[tokenId], "Not the owner"
    assert to != empty(address), "Invalid receiver"

    # Clear approvals
    self.getApproved[tokenId] = empty(address)

    # Update balances
    self.balanceOf[from_address] -= 1
    self.balanceOf[to] += 1
    
    # Update ownership
    self.ownerOf[tokenId] = to

    log Transfer(sender=from_address, receiver=to, tokenId=tokenId)
    
    if self._isContract(to):
        returnValue: bytes4 = staticcall ERC721Receiver(to).onERC721Received(msg.sender, from_address, tokenId, data)
        assert returnValue == 0x150b7a02, "ERC721: transfer to non ERC721Receiver implementer"

@external
def approve(approved: address, tokenId: uint256):
    """
    @notice Approve an address to transfer a token
    @param approved The address to approve
    @param tokenId The token ID
    """
    owner: address = self.ownerOf[tokenId]
    assert owner != empty(address), "Token does not exist"
    assert msg.sender == owner or self.isApprovedForAll[owner][msg.sender], "Not owner or approved operator"
    assert approved != owner, "Approval to current owner"
    
    self.getApproved[tokenId] = approved
    log Approval(owner=owner, approved=approved, tokenId=tokenId)

@external
def setApprovalForAll(operator: address, approved: bool):
    """
    @notice Set approval for an operator to manage all of sender's tokens
    @param operator The operator address
    @param approved Whether the operator is approved
    """
    assert operator != msg.sender, "Approve to caller"
    self.isApprovedForAll[msg.sender][operator] = approved
    log ApprovalForAll(owner=msg.sender, operator=operator, approved=approved)

@internal
@view
def _isApprovedOrOwner(spender: address, tokenId: uint256) -> bool:
    """
    @notice Check if spender is approved or owner of token
    @param spender The address to check
    @param tokenId The token ID
    @return Whether spender is approved or owner
    """
    owner: address = self.ownerOf[tokenId]
    return (
        spender == owner or 
        self.getApproved[tokenId] == spender or 
        self.isApprovedForAll[owner][spender]
    )

@internal
@view
def _isContract(addr: address) -> bool:
    """
    @notice Check if address is a contract
    @param addr The address to check
    @return Whether the address is a contract
    """
    size: uint256 = 0
    # Check code size at address
    if addr != empty(address):
        if len(slice(addr.code, 0, 1)) > 0:
            size = 1
    return size > 0 