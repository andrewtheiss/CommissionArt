# @version 0.4.1

# Profile Contract
# This contract represents a user's profile, with features for both regular users and artists.
# It is designed to be cloned by the ProfileHub contract for each user.

# State Variables

# Owner of the profile (user address)
owner: public(address)
profileImage: public(Bytes[45000])
commissions: public(DynArray[address, 100000])
unverifiedCommissions: public(DynArray[address, 10000])
allowUnverifiedCommissions: public(bool)

# Profile socials
likedProfiles: public(DynArray[address, 10000])
whitelist: public(HashMap[address, bool])
blacklist: public(HashMap[address, bool])
linkedProfiles: public(DynArray[address, 100])  

# ERC1155 addresses for supporting additional or items for sale
isArtist: public(bool)                                         # Profile is an artist
myCommissions: public(DynArray[address, 100000])               # Commissions this artist has
additionalMintErc1155s: public(DynArray[address, 100000])      # Additional mint ERC1155s for the artist
commissionToMintErc1155Map: public(HashMap[address, address])  # Map of commission addresses to mint ERC1155 addresses
proceedsAddress: public(address)                               # Address to receive proceeds from sales

# Profile expansion (for future features)
profileExpansion: public(address)

# Initialization Function
# Called by ProfileHub after cloning to set the owner
@external
def initialize(_owner: address):
    assert self.owner == empty(address), "Already initialized"
    self.owner = _owner
    self.isArtist = False  # Default to non-artist
    self.allowUnverifiedCommissions = True  # Default to allowing commissions
    self.profileExpansion = empty(address)
    self.proceedsAddress = _owner  # Default proceeds to owner's address

# Helper Functions

# Add an item to a dynamic array
@internal
def _addToArray(_array: DynArray[address, 100000], _item: address):
    assert _item not in _array, "Item already exists"
    _array.append(_item)

# Remove an item from a dynamic array by swapping with the last element
@internal
def _removeFromArray(_array: DynArray[address, 100000], _item: address):
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(_array), bound=1000):
        if _array[i] == _item:
            index = i
            found = True
            break
    assert found, "Item not found"
    lastItem: address = _array[len(_array) - 1]
    _array[index] = lastItem
    _array.pop()

# Get a paginated slice of a dynamic array
@internal
@view
def _getArraySlice(_array: DynArray[address, 100000], _page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    start: uint256 = _page * _page_size
    end: uint256 = start + _page_size
    if start >= len(_array):
        return result
    if end > len(_array):
        end = len(_array)
    for i: uint256 in range(start, end, bound=100):
        result.append(_array[i])
    return result

# Setter Functions

# Set artist status
@external
def setIsArtist(_is_artist: bool):
    assert msg.sender == self.owner, "Only owner can set artist status"
    self.isArtist = _is_artist

# Set profile image
@external
def setProfileImage(_image: Bytes[45000]):
    assert msg.sender == self.owner, "Only owner can set profile image"
    self.profileImage = _image

# Toggle allowing new commissions
@external
def setAllowUnverifiedCommissions(_allow: bool):
    assert msg.sender == self.owner, "Only owner can set allow new commissions"
    self.allowUnverifiedCommissions = _allow

# Set profile expansion address
@external
def setProfileExpansion(_address: address):
    assert msg.sender == self.owner, "Only owner can set profile expansion"
    self.profileExpansion = _address

# Set proceeds address (artist-only)
@external
def setProceedsAddress(_address: address):
    assert msg.sender == self.owner, "Only owner can set proceeds address"
    assert self.isArtist, "Only artists can set proceeds address"
    self.proceedsAddress = _address

# Add address to whitelist
@external
def addToWhitelist(_address: address):
    assert msg.sender == self.owner, "Only owner can add to whitelist"
    self.whitelist[_address] = True

# Remove address from whitelist
@external
def removeFromWhitelist(_address: address):
    assert msg.sender == self.owner, "Only owner can remove from whitelist"
    self.whitelist[_address] = False

# Blacklist Management
def addToBlacklist(_address: address):
    assert msg.sender == self.owner, "Only owner can add to blacklist"
    self.blacklist[_address] = True

def removeFromBlacklist(_address: address):
    assert msg.sender == self.owner, "Only owner can remove from blacklist"
    self.blacklist[_address] = False


## Commissions
@external
def addCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can add commission"
    self._addToArray(self.commissions, _commission)

@external
def removeCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove commission"
    self._removeFromArray(self.commissions, _commission)

@view
@external
def getCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.commissions, _page, _page_size)

## Unverified Commissions
@external
def addUnverifiedCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can add unverified commission"
    self._addToArray(self.unverifiedCommissions, _commission)

@external
def removeUnverifiedCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove unverified commission"
    self._removeFromArray(self.unverifiedCommissions, _commission)

@view
@external
def getUnverifiedCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.unverifiedCommissions, _page, _page_size)

## Liked Profiles
@external
def addLikedProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can add liked profile"
    self._addToArray(self.likedProfiles, _profile)

@external
def removeLikedProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can remove liked profile"
    self._removeFromArray(self.likedProfiles, _profile)

@view
@external
def getLikedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.likedProfiles, _page, _page_size)

## Other Profiles
@external
def linkProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can add other profile"
    self._addToArray(self.linkedProfiles, _profile)

@external
def removeLinkedProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can remove linked profile"
    self._removeFromArray(self.linkedProfiles, _profile)

@view
@external
def getLinkedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.linkedProfiles, _page, _page_size)

## My Commissions (Artist-Only)
@external
def addMyCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can add my commission"
    assert self.isArtist, "Only artists can add my commissions"
    self._addToArray(self.myCommissions, _commission)

@external
def removeMyCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove my commission"
    assert self.isArtist, "Only artists can remove my commissions"
    self._removeFromArray(self.myCommissions, _commission)

@view
@external
def getMyCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have my commissions"
    return self._getArraySlice(self.myCommissions, _page, _page_size)

## Additional Mint ERC1155s (Artist-Only)
@external
def addAdditionalMintErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can add additional mint ERC1155"
    assert self.isArtist, "Only artists can add additional mint ERC1155s"
    self._addToArray(self.additionalMintErc1155s, _erc1155)

@external
def removeAdditionalMintErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can remove additional mint ERC1155"
    assert self.isArtist, "Only artists can remove additional mint ERC1155s"
    self._removeFromArray(self.additionalMintErc1155s, _erc1155)

@view
@external
def getAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have additional mint ERC1155s"
    return self._getArraySlice(self.additionalMintErc1155s, _page, _page_size)

## Map Commission to Mint ERC1155 (Artist-Only)
@external
def mapCommissionToMintErc1155(_commission: address, _erc1155: address):
    assert msg.sender == self.owner, "Only owner can map commission to mint ERC1155"
    assert self.isArtist, "Only artists can map commission to mint ERC1155"
    self.commissionToMintErc1155Map[_commission] = _erc1155

@external
def removeMapCommissionToMintErc1155(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove map commission to mint ERC1155"
    assert self.isArtist, "Only artists can remove map commission to mint ERC1155"
    self.commissionToMintErc1155Map[_commission] = empty(address)

@view
@external
def getMapCommissionToMintErc1155(_commission: address) -> address:
    assert self.isArtist, "Only artists have map commission to mint ERC1155"
    return self.commissionToMintErc1155Map[_commission]
