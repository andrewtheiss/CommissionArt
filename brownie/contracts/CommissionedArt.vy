#pragma version 0.4.0

image_data: Bytes[10000000]  # Adjustable max size for the image data
owner: address
artist: address

event OwnershipTransferred:
    from_owner: indexed(address)
    to_owner: indexed(address)

@deploy
def __init__(image_data_input: Bytes[10000000], owner_input: address, artist_input: address):
    self.image_data = image_data_input
    self.owner = owner_input
    self.artist = artist_input

@view
def get_image_data() -> Bytes[10000000]:
    return self.image_data

@view
def get_owner() -> address:
    return self.owner

@view
def get_artist() -> address:
    return self.artist

@external
def transferOwnership(new_owner: address):
    assert msg.sender == self.owner, "Only the owner can transfer ownership"
    log OwnershipTransferred(self.owner, new_owner)
    self.owner = new_owner