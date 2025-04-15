# @version 0.4.1
# Contains the image data for a commissioned piece
# Has a list of owners that have commissioned the piece
# Has a list of artists that have commissioned the piece

imageData: Bytes[45000]  # Adjusted to handle up to 250 KB
title: String[100]  # Title of the artwork
description: Bytes[200]  # Description with 200 byte limit
owner: address
artist: address

# Mapping to store tags/associations with validation status
# address => bool (validated status)
taggedAddresses: public(HashMap[address, bool])

# Mapping to track which addresses have been tagged
# Used to enumerate all tagged addresses
isTagged: public(HashMap[address, bool])
taggedList: public(DynArray[address, 100])  # List of all tagged addresses, max 100

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

@deploy
def __init__(_image_data_input: Bytes[45000], _title_input: String[100], _description_input: Bytes[200], _owner_input: address, _artist_input: address, _commission_hub: address):
    self.imageData = _image_data_input
    self.title = _title_input
    self.description = _description_input
    self.owner = _owner_input
    self.artist = _artist_input

@external
@view
def getImageData() -> Bytes[45000]:
    return self.imageData

@external
@view
def getTitle() -> String[100]:
    return self.title

@external
@view
def getDescription() -> Bytes[200]:
    return self.description

@external
@view
def getOwner() -> address:
    return self.owner

@external
@view
def getArtist() -> address:
    return self.artist

@external
def transferOwnership(_new_owner: address):
    assert msg.sender == self.owner, "Only the owner can transfer ownership"
    assert _new_owner != empty(address), "Invalid new owner address"
    log OwnershipTransferred(from_owner=self.owner, to_owner=_new_owner)
    self.owner = _new_owner

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
def getAllTaggedAddresses() -> DynArray[address, 100]:
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
    log PersonTagged(msg.sender, _person, is_artist_tag)

@external
def validateTag():
    """
    Validate that you accept being tagged in this artwork
    Can only be called by the tagged person
    """
    assert self.isTagged[msg.sender], "You are not tagged in this artwork"
    self.taggedAddresses[msg.sender] = True
    log TagValidated(msg.sender, True)

@external
def invalidateTag():
    """
    Invalidate your tag if you don't want to be associated with this artwork
    Can only be called by the tagged person
    """
    assert self.isTagged[msg.sender], "You are not tagged in this artwork"
    self.taggedAddresses[msg.sender] = False
    log TagValidated(msg.sender, False)

@external
@view
def isPersonTagged(_person: address) -> bool:
    """
    Check if a person is tagged in this artwork
    """
    return self.isTagged[_person]

