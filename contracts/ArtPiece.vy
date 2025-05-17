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

# Interface for ArtCommissionHub
interface ArtCommissionHub:
    def owner() -> address: view
    def submitCommission(art_piece: address) -> bool: nonpayable

# Interface for ERC721Receiver
interface ERC721Receiver:
    def onERC721Received(operator: address, sender: address, tokenId: uint256, data: Bytes[1024]) -> bytes4: view

# Interface for Profile
interface Profile:
    def addCommission(art_piece: address): nonpayable

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

event AttachedToArtCommissionHub:
    art_piece: indexed(address)
    commission_hub: indexed(address)
    attacher: indexed(address)

event DetachedFromArtCommissionHub:
    art_piece: indexed(address)
    commission_hub: indexed(address)
    detacher: indexed(address)

event CommissionVerified:
    verifier: indexed(address)
    is_artist: bool

event CommissionfullyVerified:
    art_piece: indexed(address)
    artist: indexed(address)
    commissioner: indexed(address)

# ERC721 Standard variables
name: public(String[32])
symbol: public(String[8])
getApproved: public(HashMap[uint256, address])
isApprovedForAll: public(HashMap[address, HashMap[address, bool]])

# Interface IDs and other constants
INTERFACE_ID_ERC721: constant(bytes4) = 0x80ac58cd
INTERFACE_ID_ERC165: constant(bytes4) = 0x01ffc9a7
TOKEN_ID: constant(uint256) = 1 # Single token constant (this NFT has only one token)
IS_ON_CHAIN: public(constant(bool)) = True  # Constant to indicate this art piece is on-chain

# ArtPiece variables
tokenURI_data: Bytes[45000]  # Changed from imageData to tokenURI_data
tokenURI_data_format: String[10]  # Format of the tokenURI_data   
title: String[100]  # Title of the artwork
description: String[200]  # Description with 200 byte limit
artist: public(address)
commissioner: public(address)  # Store the commissioner's address explicitly
originalUploader: address  # Store the original uploader's address, do not need to expose
aiGenerated: public(bool)

# Contract state
initialized: public(bool)  # Flag to track if the contract has been initialized
artCommissionHubAddress: public(address)  # Address of the ArtCommissionHub this piece is attached to

artistVerified: public(bool)  # Flag to indicate if the artist has verified this piece
commissionerVerified: public(bool)  # Flag to indicate if the commissioner has verified this piece
fullyVerifiedCommission: public(bool)  # Flag to indicate if both parties have verified this piece
isPrivateOrNonCommissionPiece: public(bool)  # Flag to indicate if this is a private or non-commission piece (true if commissioner == artist)

# Tagging
isTagged: public(HashMap[address, bool])
isTagValidated: public(HashMap[address, bool])
taggedList: public(DynArray[address, 1000])  # List of all tagged addresses, max 1000
taggedListCount: public(uint256)


# Create minimal proxy to ArtPiece
@deploy
def __init__():
    self.initialized = False
    self.name = ""
    self.symbol = ""
    self.taggedListCount = 0

# Initialize has a bunch of specific behaviors
# #1. We need different commissioners and artist for every piece in order to be a proper commission
# If you just want to upload art, you either don't set an artist / commissioner or set them the same
# Any time in the future you can tag the artist or commissioner, this is to make workflows easier
@external
def initialize(
    _token_uri_data: Bytes[45000],
    _token_uri_data_format: String[10],  # Format of the tokenURI_data i.e. webp, avif, etc.
    _title_input: String[100], 
    _description_input: String[200], 
    _commissioner_input: address,
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
    @param _commissioner_input Address of the commissioner/owner
    @param _artist_input Address of the artist
    @param _commission_hub Address of the commission hub (if any, empty address if none)
    @param _ai_generated Flag indicating if the artwork was AI generated
    """
    assert not self.initialized, "Already initialized"
    self.initialized = True
    self.tokenURI_data = _token_uri_data
    self.tokenURI_data_format = _token_uri_data_format
    self.title = _title_input
    self.description = _description_input
    self.artist = _artist_input
    self.commissioner = _commissioner_input
    self.aiGenerated = _ai_generated
    self.artCommissionHubAddress = _commission_hub
    self.originalUploader = msg.sender

    # Determine if this is a private or non-commission piece based on commissioner and artist being the same
    if _commissioner_input == _artist_input and _commissioner_input != empty(address) and _artist_input != empty(address):
        self.artistVerified = True
        self.commissionerVerified = True
        self.fullyVerifiedCommission = True
        self.isPrivateOrNonCommissionPiece = True
         
    # The uploader implicitly verifies their side
    if not self.isPrivateOrNonCommissionPiece:
        if _commissioner_input == self.originalUploader:
            self.commissionerVerified = True
        elif _artist_input == self.originalUploader:
            self.artistVerified = True

    # Set ERC721 metadata
    self.name = "ArtPiece"
    self.symbol = "ART"
    
    # Emit Transfer event for minting the single token
    log Transfer(sender=empty(address), receiver=_commissioner_input, tokenId=TOKEN_ID)

# ERC721 Standard Functions
@external
@view
def balanceOf(_owner: address) -> uint256:
    """
    @notice Get the number of tokens owned by an address
    @param _owner The address to query
    @return The number of tokens owned
    """
    current_owner: address = self._getEffectiveOwner()
    if _owner == current_owner:
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
    assert _tokenId == TOKEN_ID, "This NFT collection only has a single id: 1"
    return self._getEffectiveOwner()

@external
def approve(_approved: address, _tokenId: uint256):
    """
    @notice Approve an address to transfer a token - always reverts as we don't allow delegated transfers
    @param _approved The address to approve
    @param _tokenId The token ID
    """
    # This contract doesn't allow approvals - transfers are only managed through the Commission Hub
    assert False, "Approvals are disabled - transfers only through hub ownership"

@external
def setApprovalForAll(_operator: address, _approved: bool):
    """
    @notice Set approval for an operator to manage all of sender's tokens - always reverts as we don't allow delegated transfers
    @param _operator The operator address
    @param _approved Whether the operator is approved
    """
    # This contract doesn't allow approvals - transfers are only managed through the Commission Hub
    assert False, "Approvals are disabled - transfers only through hub ownership"

@external
def transferFrom(_from: address, _to: address, _tokenId: uint256):
    """
    @notice Transfer a token from one address to another - always reverts if Art Piece is attached to a hub
    @dev Only the direct owner can transfer if the piece has never been attached to a hub
    @param _from The address to transfer from
    @param _to The address to transfer to
    @param _tokenId The token ID
    """
    assert False, "Transfers disabled for hub-attached art pieces"

@external
def safeTransferFrom(_from: address, _to: address, _tokenId: uint256, _data: Bytes[1024]=b""):
    """
    @notice Safely transfer a token from one address to another - always reverts if Art Piece is attached to a hub
    @dev Only the direct owner can transfer if the piece has never been attached to a hub
    @param _from The address to transfer from
    @param _to The address to transfer to
    @param _tokenId The token ID
    @param _data Optional data to send along with the transfer
    """
    assert False, "Transfers disabled for hub-attached art pieces"

@external
@view
def supportsInterface(_interfaceId: bytes4) -> bool:
    """
    @notice Query if contract implements an interface
    @param _interfaceId The interface identifier
    @return True if the contract implements the interface
    """
    return _interfaceId == INTERFACE_ID_ERC721 or _interfaceId == INTERFACE_ID_ERC165

@external
@view
def tokenURI(_tokenId: uint256) -> String[1000]:  # Updated return type
    """
    @notice Get the URI for a token
    @param _tokenId The token ID
    @return The token URI
    """
    assert _tokenId == TOKEN_ID, "This NFT collection only has a single id: 1"
    temp: String[1000] = ""
    return temp

@external
@view
def getTokenURIData() -> Bytes[45000]:
    """
    @notice Get the raw token URI data stored in the contract
    @return Raw token URI data as bytes
    """
    return self.tokenURI_data

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

@internal
@view
def _getEffectiveOwner() -> address:
    """
    @notice Internal function to determine the effective owner based on verification and hub status
    @return The effective owner address
    """
    # If attached to a hub and fully verified, return the hub owner (which is set only by ArtCommissionHubOwners)
    if self.artCommissionHubAddress != empty(address) and self.fullyVerifiedCommission:
        hub_owner: address = staticcall ArtCommissionHub(self.artCommissionHubAddress).owner()
        if hub_owner != empty(address):
            return hub_owner     
    # Before verification, return the original uploader
    return self.originalUploader

@external
@view
def getOwner() -> address:
    """
    @notice Get the effective owner of the artwork
    @dev Returns originalUploader before verification, or hub owner if attached to a hub
    @return The effective owner address
    """
    return self._getEffectiveOwner()

@external
@view
def getCommissioner() -> address:
    """
    @notice Get the commissioner of the artwork
    @return The commissioner address
    """
    return self.commissioner

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
def getArtCommissionHubAddress() -> address:
    """
    Return the address of the commission hub this piece is attached to
    """
    return self.artCommissionHubAddress

@external
def addArtCommissionHubDetails(_art_commission_hub_address: address, _commissioner: address, _artist: address):
    """
    @notice Add the details of the commission hub to the art piece
    @param _art_commission_hub_address The address of the commission hub
    @param _commissioner The address of the commissioner
    @param _artist The address of the artist
    """
    assert self.initialized, "Contract not initialized"
    assert msg.sender == self.originalUploader, "Only the original uploader can add art commission hub details"

    if _art_commission_hub_address != empty(address) and self.artCommissionHubAddress == empty(address):
        self.artCommissionHubAddress = _art_commission_hub_address
        log AttachedToArtCommissionHub(art_piece=self, commission_hub=_art_commission_hub_address, attacher=msg.sender)

    if _commissioner != empty(address) and self.commissioner == empty(address):
        self.commissioner = _commissioner
        if (_commissioner == _artist):
            self.artistVerified = True
            self.commissionerVerified = True
            self.fullyVerifiedCommission = True
            self.isPrivateOrNonCommissionPiece = True
    if _artist != empty(address) and self.artist == empty(address):
        self.artist = _artist
        if (_artist == _commissioner):
            self.artistVerified = True
            self.commissionerVerified = True
            self.fullyVerifiedCommission = True
            self.isPrivateOrNonCommissionPiece = True

# We need to have a connected artCommissionHub before verification
@external
def verifyAsArtist():
    """
    @notice Allows the artist to verify this art piece
    @dev Can only be called by the artist of the piece
    """
    assert self.initialized, "Contract not initialized"
    assert not self.isPrivateOrNonCommissionPiece, "Not a commission piece"
    assert msg.sender == self.artist, "Only the artist can verify as artist"
    assert not self.artistVerified, "Already verified by artist"
    assert not self.fullyVerifiedCommission, "Already fully verified"
    assert self.artCommissionHubAddress != empty(address), "ArtPiece must be attached to a ArtCommissionHub to be fully verified"
    
    self.artistVerified = True
    log CommissionVerified(verifier=msg.sender, is_artist=True)
    
    # Check if both parties have verified
    if self.commissionerVerified:
        self._completeVerification()

# We need to have a connected artCommissionHub before verification
@external
def verifyAsCommissioner():
    """
    @notice Allows the commissioner to verify this art piece
    @dev Can only be called by the commissioner of the piece
    """
    assert self.initialized, "Contract not initialized"
    assert not self.isPrivateOrNonCommissionPiece, "Not a commission piece"
    assert msg.sender == self.commissioner, "Only the commissioner can verify as commissioner"
    assert not self.commissionerVerified, "Already verified by commissioner"
    assert not self.fullyVerifiedCommission, "Already fully verified"
    assert self.artCommissionHubAddress != empty(address), "ArtPiece must be attached to a ArtCommissionHub to be fully verified"
    
    self.commissionerVerified = True
    log CommissionVerified(verifier=msg.sender, is_artist=False)
    
    # Check if both parties have verified
    if self.artistVerified:
        self._completeVerification()

# After completeVerification:
# If attached to a hub, ownership will now be determined by the hub owner
# No need to update any internal state since _getEffectiveOwner() will handle this
@internal
def _completeVerification():
    """
    Internal helper to complete the verification process
    - Sets fullyVerifiedCommission flag
    - Updates ownership if attached to a hub
    - Emits events
    """
    self.fullyVerifiedCommission = True
    
    # Attach to the Profile of both the artist and commissioner as a commission
    profile_interface: Profile = Profile(self.artist)
    extcall profile_interface.addCommission(self)
    profile_interface = Profile(self.commissioner)
    extcall profile_interface.addCommission(self)

    # After call submitCommission on the commission hub
    commission_hub_interface: ArtCommissionHub = ArtCommissionHub(self.artCommissionHubAddress)
    submitedComission: bool = extcall commission_hub_interface.submitCommission(self)
    
    # Emit verification complete event
    log CommissionfullyVerified(art_piece=self, artist=self.artist, commissioner=self.commissioner)

@external
def transferOwnership(_new_owner: address):
    """
    @notice Transfer ownership directly - always reverts if Art Piece is attached to a hub
    @dev Only the direct owner can transfer if the piece has never been attached to a hub
    """
    assert False, "Transfers disabled for hub-attached art pieces"

# Phase 2 - Tagging TODO - After commissions works with UI
@external
@view
def isTaggedValidated(_person: address) -> bool:
    """
    Check if a person is tagged and their validation status
    Returns false if not tagged, or tagged but not validated
    """
    if not self.isTagged[_person]:
        return False
    return self.isTagValidated[_person]

@external
@view
def getAllTaggedAddresses() -> DynArray[address, 1000]:
    """
    Returns all tagged addresses
    """
    return self.taggedList

# Phase 2 - Tagging TODO - After commissions works with UI
@internal
def _addTag(_person: address):
    """
    Internal helper to add a tag
    """
    if not self.isTagged[_person]:
        self.isTagged[_person] = True
        self.isTagValidated[_person] = False  # Initially unvalidated
        self.taggedList.append(_person)
        self.taggedListCount += 1

# Phase 2 - Tagging TODO - After commissions works with UI
@external
def tagPerson(_person: address, _profile_factory_and_regsitry: address):
    """
    Tag a person as associated with this artwork
    Only owner or artist can tag people
    """
    current_owner: address = self._getEffectiveOwner()
    assert msg.sender == current_owner or msg.sender == self.artist, "Only owner or artist can tag people"
    assert _person != empty(address), "Cannot tag zero address"
    assert len(self.taggedList) < 100, "Maximum number of tags reached"
    
    self._addTag(_person)

    # # Get the profile of the person based on their address
    # profile_factory_and_registry: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(_profile_factory_and_regsitry)
    # profile_social: address = profile_factory_and_registry.getProfileSocial(_person)
    # profile_social_interface: ProfileSocial = ProfileSocial(profile_social)
    # staticcall profile_social_interface.addTag(self)
    
    # Emit event based on who is doing the tagging
    is_artist_tag: bool = msg.sender == self.artist
    log PersonTagged(tagger=msg.sender, tagged_person=_person, is_artist=is_artist_tag)

# Phase 2 - Tagging TODO - After commissions works with UI
@external
def validateTag() -> bool:
    """
    Validate that you accept being tagged in this artwork
    Can only be called by the tagged person
    """
    if self.isTagged[msg.sender] == False:
        return False
        
    self.isTagValidated[msg.sender] = True
    log TagValidated(person=msg.sender, status=True)
    return True

# Phase 2 - Tagging TODO - After commissions works with UI
@external
def invalidateTag():
    """
    Invalidate your tag if you don't want to be associated with this artwork
    Can only be called by the tagged person
    """
    assert self.isTagged[msg.sender], "You are not tagged in this artwork"
    self.isTagValidated[msg.sender] = False
    log TagValidated(person=msg.sender, status=False)

# Phase 2 - Tagging TODO - After commissions works with UI
@external
@view
def isPersonTagged(_person: address) -> bool:
    """
    Check if a person is tagged in this artwork
    """
    return self.isTagged[_person]

@external
@view
def getAIGenerated() -> bool:
    """
    Return whether the artwork was AI generated
    """
    return self.aiGenerated

@external
def attachToArtCommissionHub(_commission_hub: address):
    self._attachToArtCommissionHub(_commission_hub)


@internal
def _attachToArtCommissionHub(_commission_hub: address):
    """
    Attach this ArtPiece to a ArtCommissionHub
    Can only be called if not currently attached to a hub
    """
    assert self.artCommissionHubAddress == empty(address), "Already attached to a ArtCommissionHub"
    assert _commission_hub != empty(address), "Invalid ArtCommissionHub address"
    assert not self.fullyVerifiedCommission, "ArtPiece must be fully verified to be attached to a ArtCommissionHub"
    assert msg.sender == self.artist or msg.sender == self.commissioner, "Only artist or commissioner can attach to a ArtCommissionHub"

    # Artist or commissioner need to be the hub owner
    hub_owner: address = staticcall ArtCommissionHub(_commission_hub).owner()
    assert hub_owner == self.artist or hub_owner == self.commissioner, "Only artist, commissioner, or hub owner can attach to a ArtCommissionHub"

    self.artCommissionHubAddress = _commission_hub
    log AttachedToArtCommissionHub(art_piece=self, commission_hub=_commission_hub, attacher=msg.sender)

@external
def detachFromArtCommissionHub():
    """
    @notice Detach this ArtPiece from its ArtCommissionHub
    @dev Only the hub owner can detach, but the permanent relationship remains
    @dev This only affects current attachment status, not ownership determination
    """
    assert self.artCommissionHubAddress != empty(address), "Not attached to a ArtCommissionHub"
    assert msg.sender == self._getEffectiveOwner(), "Only the hub owner can detach from ArtCommissionHub"
    assert not self.fullyVerifiedCommission, "ArtPiece must be fully verified to be attached to a ArtCommissionHub"

    previous_hub: address = self.artCommissionHubAddress
    self.artCommissionHubAddress = empty(address)
    
    log DetachedFromArtCommissionHub(art_piece=self, commission_hub=previous_hub, detacher=msg.sender)

@external
@view
def checkOwner() -> address:
    """
    @notice External wrapper to check the owner of this ArtPiece.
    @return The effective owner address
    """
    return self._getEffectiveOwner()

@external
@view
def isUnverifiedCommission() -> bool:
    """
    @notice Check if this art piece is an unverified commission (commissioner != artist but not fully verified)
    @dev This is for backward compatibility with tests that check if a piece is a commission
    @return Whether the art piece is an unverified commission
    """
    # It's an unverified commission if:
    # 1. It's not a private/non-commission piece (commissioner != artist)
    # 2. It's not fully verified yet
    return not self.isPrivateOrNonCommissionPiece and not self.fullyVerifiedCommission

@external
@view
def isFullyVerifiedCommission() -> bool:
    """
    @notice Check if this art piece is fully verified (commission or non-commission)
    @dev Returns true if fullyVerifiedCommission is true, regardless of commission type
    @return Whether the art piece is fully verified
    """
    return self.fullyVerifiedCommission
