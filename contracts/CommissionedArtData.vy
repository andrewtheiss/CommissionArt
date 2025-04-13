# @version 0.4.1
# Contains the image data for a commissioned piece
# Has a list of owners that have commissioned the piece
# Has a list of artists that have commissioned the piece

image_data: Bytes[45000]  # Adjusted to handle up to 250 KB
owner: address
artist: address

event OwnershipTransferred:
    from_owner: indexed(address)
    to_owner: indexed(address)

@deploy
def __init__(image_data_input: Bytes[45000], owner_input: address, artist_input: address):
    self.image_data = image_data_input
    self.owner = owner_input
    self.artist = artist_input

@external
@view
def get_image_data() -> Bytes[45000]:
    return self.image_data

@external
@view
def get_owner() -> address:
    return self.owner

@external
@view
def get_artist() -> address:
    return self.artist

@external
def transferOwnership(new_owner: address):
    assert msg.sender == self.owner, "Only the owner can transfer ownership"
    assert new_owner != empty(address), "Invalid new owner address"
    log OwnershipTransferred(from_owner=self.owner, to_owner=new_owner)
    self.owner = new_owner