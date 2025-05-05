# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# Contains the image data for a commissioned piece
# Has a list of owners that have commissioned the piece
# Has a list of artists that have commissioned the piece
# Implements ERC721 for a single token NFT

# Interface for CommissionHub
interface CommissionHub:
    def owner() -> address: view

# Interface for ERC721Receiver
interface ERC721Receiver:
    def onERC721Received(operator: address, sender: address, tokenId: uint256, data: Bytes[1024]) -> bytes4: view

# ERC721 Events
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

# ArtPiece specific events
event OwnershipTransferred:
    from_owner: indexed(address)
    to_owner: indexed(address)

event PersonTagged:
    tagger: indexed(address)
    tagged_person: indexed(address)
    is_artist: bool

event TagValidated:
    person: indexed(address)
    status: bool

event AttachedToCommissionHub:
    art_piece: indexed(address)
    commission_hub: indexed(address)
    attacher: indexed(address)

# ERC721 Standard variables
name: public(String[32])
symbol: public(String[8])
# Token ID to approved address mapping
getApproved: public(HashMap[uint256, address])
# Owner to operator approvals mapping
isApprovedForAll: public(HashMap[address, HashMap[address, bool]])
# Interface IDs
INTERFACE_ID_ERC721: constant(bytes4) = 0x80ac58cd
INTERFACE_ID_ERC165: constant(bytes4) = 0x01ffc9a7
# Single token constant (this NFT has only one token)
TOKEN_ID: constant(uint256) = 1

# ArtPiece variables
tokenURI_data: Bytes[45000]  # Changed from imageData to tokenURI_data as String
tokenURI_data_format: String[10]  # Format of the tokenURI_data   
title: String[100]  # Title of the artwork
description: String[200]  # Description with 200 byte limit
owner: address
artist: address
aiGenerated: public(bool)
initialized: public(bool)  # Flag to track if the contract has been initialized
attachedToCommissionHub: public(bool)  # Flag to track if attached to a CommissionHub
commissionHubAddress: public(address)  # Address of the CommissionHub this piece is attached to
IS_ON_CHAIN: public(constant(bool)) = True  # Constant to indicate this art piece is on-chain

# Mapping to store tags/associations with validation status
# address => bool (validated status)
taggedAddresses: public(HashMap[address, bool])

# Mapping to track which addresses have been tagged
# Used to enumerate all tagged addresses
isTagged: public(HashMap[address, bool])
taggedList: public(DynArray[address, 1000])  # List of all tagged addresses, max 1000

# Add commissionWhitelist mapping to track whitelisted commissioners
commissionWhitelist: public(HashMap[address, bool])

@deploy
def __init__():
    """
    Empty constructor for create_minimal_proxy_to
    """
    self.initialized = False
    self.name = ""
    self.symbol = ""

@external
def initialize(
    _token_uri_data: Bytes[45000],  # Changed parameter type and name
    _token_uri_data_format: String[10],  # Format of the tokenURI_data
    _title_input: String[100], 
    _description_input: String[200], 
    _owner_input: address, 
    _artist_input: address, 
    _commission_hub: address, 
    _ai_generated: bool
):
    """
    @notice Initialize the ArtPiece contract, can only be called once
    @param _token_uri_data The token URI data as raw bytes (up to 45000 bytes)
    @param _token_uri_data_format Format identifier for the token URI data (e.g., "avif", "webp", etc.)
    @param _title_input Title of the artwork
    @param _description_input Description of the artwork
    @param _owner_input Address of the owner
    @param _artist_input Address of the artist
    @param _commission_hub Address of the commission hub (if any, empty address if none)
    @param _ai_generated Flag indicating if the artwork was AI generated
    """
    assert not self.initialized, "Already initialized"
    self.tokenURI_data = _token_uri_data  # Updated field name
    self.tokenURI_data_format = _token_uri_data_format  # Updated field name
    self.title = _title_input
    self.description = _description_input
    self.owner = _owner_input
    self.artist = _artist_input
    self.aiGenerated = _ai_generated
    self.initialized = True
    
    # Set commission hub information
    self.attachedToCommissionHub = _commission_hub != empty(address)
    self.commissionHubAddress = _commission_hub

    # Set ERC721 metadata
    self.name = "ArtPiece"
    self.symbol = "ART"
    
    # Emit Transfer event for minting the single token
    log Transfer(sender=empty(address), receiver=_owner_input, tokenId=TOKEN_ID)

# ERC721 Standard Functions
@external
@view
def balanceOf(_owner: address) -> uint256:
    """
    @notice Get the number of tokens owned by an address
    @param _owner The address to query
    @return The number of tokens owned
    """
    if _owner == self.owner:
        return 1
    return 0

@external
@view
def ownerOf(_tokenId: uint256) -> address:
    """
    @notice Get the owner of a token
    @param _tokenId The token ID
    @return The owner address
    """
    assert _tokenId == TOKEN_ID, "Invalid token ID"
    return self.owner

@external
def approve(_approved: address, _tokenId: uint256):
    """
    @notice Approve an address to transfer a token
    @param _approved The address to approve
    @param _tokenId The token ID
    """
    assert _tokenId == TOKEN_ID, "Invalid token ID"
    current_owner: address = self.owner
    assert msg.sender == current_owner or self.isApprovedForAll[current_owner][msg.sender], "Not owner or approved operator"
    self.getApproved[_tokenId] = _approved
    log Approval(owner=current_owner, approved=_approved, tokenId=_tokenId)

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

@external
def transferFrom(_from: address, _to: address, _tokenId: uint256):
    """
    @notice Transfer a token
    @param _from The current owner
    @param _to The new owner
    @param _tokenId The token ID
    """
    assert _tokenId == TOKEN_ID, "Invalid token ID"
    assert self._isApprovedOrOwner(msg.sender, _tokenId), "Not approved or owner"
    assert _from == self.owner, "Not the owner"
    assert _to != empty(address), "Invalid receiver"
    
    # Clear approvals
    self.getApproved[_tokenId] = empty(address)
    
    # Update ownership
    old_owner: address = self.owner
    self.owner = _to
    
    log Transfer(sender=_from, receiver=_to, tokenId=_tokenId)
    log OwnershipTransferred(from_owner=old_owner, to_owner=_to)

@external
def safeTransferFrom(_from: address, _to: address, _tokenId: uint256, _data: Bytes[1024] = b""):
    """
    @notice Safely transfer a token
    @param _from The current owner
    @param _to The new owner
    @param _tokenId The token ID
    @param _data Additional data with no specified format
    """
    assert _tokenId == TOKEN_ID, "Invalid token ID"
    assert self._isApprovedOrOwner(msg.sender, _tokenId), "Not approved or owner"
    assert _from == self.owner, "Not the owner"
    assert _to != empty(address), "Invalid receiver"
    
    # Clear approvals
    self.getApproved[_tokenId] = empty(address)
    
    # Update ownership
    old_owner: address = self.owner
    self.owner = _to
    
    log Transfer(sender=_from, receiver=_to, tokenId=_tokenId)
    log OwnershipTransferred(from_owner=old_owner, to_owner=_to)
    
    if self._isContract(_to):
        returnValue: bytes4 = staticcall ERC721Receiver(_to).onERC721Received(msg.sender, _from, _tokenId, _data)
        assert returnValue == 0x150b7a02, "ERC721: transfer to non ERC721Receiver implementer"

@external
@view
def supportsInterface(_interfaceId: bytes4) -> bool:
    """
    @notice Query if contract implements an interface
    @param _interfaceId The interface identifier
    @return True if the contract implements the interface
    """
    return _interfaceId == INTERFACE_ID_ERC721 or _interfaceId == INTERFACE_ID_ERC165

@internal
@view
def _isApprovedOrOwner(_spender: address, _tokenId: uint256) -> bool:
    """
    @notice Check if spender is approved or owner of token
    @param _spender The address to check
    @param _tokenId The token ID
    @return Whether spender is approved or owner
    """
    assert _tokenId == TOKEN_ID, "Invalid token ID"
    return (
        _spender == self.owner or 
        self.getApproved[_tokenId] == _spender or 
        self.isApprovedForAll[self.owner][_spender]
    )

@internal
@view
def _isContract(_addr: address) -> bool:
    """
    @notice Check if address is a contract
    @param _addr The address to check
    @return Whether the address is a contract
    """
    # Simple check: if it's not an empty address, assume it's a contract
    # This is a simplification and in a production environment 
    # should be replaced with a proper implementation
    return _addr != empty(address)

# URI Functions
# TODO - convert to BASE64 encoded json object
# Otuput: data:application/json;base64,
@external
@view
def tokenURI(_tokenId: uint256) -> String[100000]:  # Updated return type
    """
    @notice Get the URI for a token
    @param _tokenId The token ID
    @return The token URI
    """
    assert _tokenId == TOKEN_ID, "Invalid token ID"

    temp: String[100000] = ""
    # Return the stored tokenURI data
    return temp

# Original ArtPiece Functions, with updated names
@external
@view
def getTokenURIData() -> Bytes[45000]:
    """
    @notice Get the raw token URI data stored in the contract
    @return Raw token URI data as bytes
    """
    return self.tokenURI_data

# Added for backwards compatibility
@external
@view
def getImageData() -> Bytes[45000]:
    """
    @notice Get the raw image data stored in the contract (alias for getTokenURIData for backwards compatibility)
    @return Raw token URI data as bytes
    """
    return self.tokenURI_data

@external
@view
def getTitle() -> String[100]:
    """
    @notice Get the title of the artwork
    @return The artwork title
    """
    return self.title

@external
@view
def getDescription() -> String[200]:
    """
    @notice Get the description of the artwork
    @return The artwork description
    """
    return self.description

@external
@view
def getOwner() -> address:
    """
    @notice Get the owner of the artwork
    @return The owner address
    """
    return self.owner

@external
@view
def getArtist() -> address:
    """
    @notice Get the artist of the artwork
    @return The artist address
    """
    return self.artist

@external
@view
def getCommissionHubAddress() -> address:
    """
    Return the address of the commission hub this piece is attached to
    """
    return self.commissionHubAddress

@external
def transferOwnership(_new_owner: address):
    """
    @notice Transfer ownership using the ERC721 mechanism
    """
    assert msg.sender == self.owner, "Only the owner can transfer ownership"
    assert _new_owner != empty(address), "Invalid new owner address"
    
    # Implement transfer logic directly instead of calling self.transferFrom
    old_owner: address = self.owner
    
    # Clear approvals for token ID 1
    self.getApproved[TOKEN_ID] = empty(address)
    
    # Update ownership
    self.owner = _new_owner
    
    # Emit events
    log Transfer(sender=old_owner, receiver=_new_owner, tokenId=TOKEN_ID)
    log OwnershipTransferred(from_owner=old_owner, to_owner=_new_owner)

@external
@view
def isTaggedValidated(_person: address) -> bool:
    """
    Check if a person is tagged and their validation status
    Returns false if not tagged, or tagged but not validated
    """
    if not self.isTagged[_person]:
        return False
    return self.taggedAddresses[_person]

@external
@view
def getAllTaggedAddresses() -> DynArray[address, 1000]:
    """
    Returns all tagged addresses
    """
    return self.taggedList

@internal
def _addTag(_person: address):
    """
    Internal helper to add a tag
    """
    if not self.isTagged[_person]:
        self.isTagged[_person] = True
        self.taggedAddresses[_person] = False  # Initially unvalidated
        self.taggedList.append(_person)

@external
def tagPerson(_person: address):
    """
    Tag a person as associated with this artwork
    Only owner or artist can tag people
    """
    assert msg.sender == self.owner or msg.sender == self.artist, "Only owner or artist can tag people"
    assert _person != empty(address), "Cannot tag zero address"
    assert len(self.taggedList) < 100, "Maximum number of tags reached"
    
    self._addTag(_person)
    
    # Emit event based on who is doing the tagging
    is_artist_tag: bool = msg.sender == self.artist
    log PersonTagged(tagger=msg.sender, tagged_person=_person, is_artist=is_artist_tag)

@external
def validateTag():
    """
    Validate that you accept being tagged in this artwork
    Can only be called by the tagged person
    """
    assert self.isTagged[msg.sender], "You are not tagged in this artwork"
    self.taggedAddresses[msg.sender] = True
    log TagValidated(person=msg.sender, status=True)

@external
def invalidateTag():
    """
    Invalidate your tag if you don't want to be associated with this artwork
    Can only be called by the tagged person
    """
    assert self.isTagged[msg.sender], "You are not tagged in this artwork"
    self.taggedAddresses[msg.sender] = False
    log TagValidated(person=msg.sender, status=False)

@external
@view
def isPersonTagged(_person: address) -> bool:
    """
    Check if a person is tagged in this artwork
    """
    return self.isTagged[_person]

@external
def setCommissionWhitelist(_commissioner: address, _status: bool):
    """
    Allow the owner to set a commissioner's whitelist status
    """
    assert msg.sender == self.owner or msg.sender == self.artist, "Only owner or artist can set commission whitelist"
    self.commissionWhitelist[_commissioner] = _status
    
@view
@external
def isOnCommissionWhitelist(_commissioner: address) -> bool:
    """
    Check if an address is whitelisted for commissioning
    """
    return self.commissionWhitelist[_commissioner]

@external
@view
def getAIGenerated() -> bool:
    """
    Return whether the artwork was AI generated
    """
    return self.aiGenerated

@external
def attachToCommissionHub(_commission_hub: address):
    """
    Attach this ArtPiece to a CommissionHub
    Can only be called once per ArtPiece
    """
    assert msg.sender == self.owner or msg.sender == self.artist, "Only owner or artist can attach to a CommissionHub"
    assert not self.attachedToCommissionHub, "Already attached to a CommissionHub"
    assert _commission_hub != empty(address), "Invalid CommissionHub address"

    self.attachedToCommissionHub = True
    self.commissionHubAddress = _commission_hub
    
    log AttachedToCommissionHub(art_piece=self, commission_hub=_commission_hub, attacher=msg.sender)

@external
@view
def checkOwner() -> address:
    """
    Check the owner of this ArtPiece.
    If attached to a CommissionHub, returns the owner from the CommissionHub.
    Otherwise returns the stored owner.
    """
    if self.attachedToCommissionHub and self.commissionHubAddress != empty(address):
        return staticcall CommissionHub(self.commissionHubAddress).owner()
    return self.owner

