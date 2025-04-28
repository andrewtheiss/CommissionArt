# @version 0.4.1

# Profile Contract
# This contract represents a user's profile, with features for both regular users and artists.
# It is designed to be cloned by the ProfileHub contract for each user.

# State Variables

# Owner of the profile (user address)
deployer: public(address)  # New variable to store the deployer's address
owner: public(address)
profileImage: public(Bytes[45000])
profileImageCount: public(uint256)
profileImages: public(HashMap[uint256, Bytes[45000]])  # Store historical profile images

# Commissions and counters
commissions: public(DynArray[address, 100000])
commissionCount: public(uint256)
unverifiedCommissions: public(DynArray[address, 10000])
unverifiedCommissionCount: public(uint256)
allowUnverifiedCommissions: public(bool)

# Art pieces collection
myArt: public(DynArray[address, 100000])
myArtCount: public(uint256)

# Profile socials and counters
likedProfiles: public(DynArray[address, 10000])
likedProfileCount: public(uint256)
whitelist: public(HashMap[address, bool])
blacklist: public(HashMap[address, bool])
linkedProfiles: public(DynArray[address, 100])  
linkedProfileCount: public(uint256)

# ERC1155 addresses for supporting additional or items for sale
isArtist: public(bool)                                         # Profile is an artist
myCommissions: public(DynArray[address, 100000])               # Commissions this artist has
myCommissionCount: public(uint256)                             # Count of artist's commissions
additionalMintErc1155s: public(DynArray[address, 100000])      # Additional mint ERC1155s for the artist
additionalMintErc1155Count: public(uint256)                    # Count of additional ERC1155s
commissionToMintErc1155Map: public(HashMap[address, address])  # Map of commission addresses to mint ERC1155 addresses
proceedsAddress: public(address)                               # Address to receive proceeds from sales

# Profile expansion (for future features)
profileExpansion: public(address)

# Interface for ArtPiece contract
interface ArtPiece:
    def getOwner() -> address: view
    def getArtist() -> address: view
    def initialize(_image_data_input: Bytes[45000], _title_input: String[100], _description_input: Bytes[200], _owner_input: address, _artist_input: address, _commission_hub: address, _ai_generated: bool): nonpayable

# Constructor
@deploy
def __init__():
    self.deployer = msg.sender  # Set deployer to msg.sender during deployment

# Initialization Function
@external
def initialize(_owner: address):
    assert self.owner == empty(address), "Already initialized"
    self.owner = _owner
    self.isArtist = False  # Default to non-artist
    self.allowUnverifiedCommissions = True  # Default to allowing commissions
    self.profileExpansion = empty(address)
    self.proceedsAddress = _owner  # Default proceeds to owner's address
    
    # Initialize counters
    self.profileImageCount = 0
    self.commissionCount = 0
    self.unverifiedCommissionCount = 0
    self.likedProfileCount = 0
    self.linkedProfileCount = 0
    self.myCommissionCount = 0
    self.additionalMintErc1155Count = 0
    self.myArtCount = 0

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

# Get a paginated slice in reverse order (newest first)
@internal
@view
def _getArraySliceReverse(_array: DynArray[address, 100000], _total_count: uint256, _page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    
    # If array is empty or invalid page, return empty result
    if _total_count == 0 or _page * _page_size >= _total_count:
        return result
    
    # Calculate the start index from the end (newest items first)
    start: uint256 = _total_count - (_page * _page_size) - 1
    # Calculate how many items to return
    items_to_return: uint256 = min(_page_size, start + 1)
    
    # Cap at result array maximum size
    items_to_return = min(items_to_return, 100)
    
    # Add items in reverse order (newest first)
    for i: uint256 in range(0, items_to_return, bound=100):
        idx: uint256 = start - i
        if idx < len(_array):  # Safety check
            result.append(_array[idx])
    
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
    
    # Store current image in history
    if len(self.profileImage) > 0:
        self.profileImages[self.profileImageCount] = self.profileImage
        self.profileImageCount += 1
    
    # Update current profile image
    self.profileImage = _image

# Get historical profile image
@view
@external
def getProfileImageByIndex(_index: uint256) -> Bytes[45000]:
    assert _index < self.profileImageCount, "Invalid profile image index"
    return self.profileImages[_index]

# Get recent profile images (newest first)
@view
@external
def getRecentProfileImages(_count: uint256) -> DynArray[Bytes[45000], 10]:
    result: DynArray[Bytes[45000], 10] = []
    
    # Cap count to maximum result size and available images
    count: uint256 = min(_count, 10)
    count = min(count, self.profileImageCount + 1)  # +1 for current image
    
    # Add current image first if it exists
    if len(self.profileImage) > 0:
        result.append(self.profileImage)
        count -= 1
    
    # Add historical images in reverse order
    for i: uint256 in range(0, count, bound=10):
        idx: uint256 = self.profileImageCount - 1 - i
        result.append(self.profileImages[idx])
    
    return result

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
@external
def addToBlacklist(_address: address):
    assert msg.sender == self.owner, "Only owner can add to blacklist"
    self.blacklist[_address] = True

@external
def removeFromBlacklist(_address: address):
    assert msg.sender == self.owner, "Only owner can remove from blacklist"
    self.blacklist[_address] = False


## Commissions
@external
def addCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can add commission"
    self._addToArray(self.commissions, _commission)
    self.commissionCount += 1

@external
def removeCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove commission"
    self._removeFromArray(self.commissions, _commission)
    self.commissionCount -= 1

@view
@external
def getCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.commissions, _page, _page_size)

@view
@external
def getRecentCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySliceReverse(self.commissions, self.commissionCount, _page, _page_size)

## Unverified Commissions
@external
def addUnverifiedCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can add unverified commission"
    self._addToArray(self.unverifiedCommissions, _commission)
    self.unverifiedCommissionCount += 1

@external
def removeUnverifiedCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove unverified commission"
    self._removeFromArray(self.unverifiedCommissions, _commission)
    self.unverifiedCommissionCount -= 1

@view
@external
def getUnverifiedCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.unverifiedCommissions, _page, _page_size)

@view
@external
def getRecentUnverifiedCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySliceReverse(self.unverifiedCommissions, self.unverifiedCommissionCount, _page, _page_size)

## Liked Profiles
@external
def addLikedProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can add liked profile"
    self._addToArray(self.likedProfiles, _profile)
    self.likedProfileCount += 1

@external
def removeLikedProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can remove liked profile"
    self._removeFromArray(self.likedProfiles, _profile)
    self.likedProfileCount -= 1

@view
@external
def getLikedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.likedProfiles, _page, _page_size)

@view
@external
def getRecentLikedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySliceReverse(self.likedProfiles, self.likedProfileCount, _page, _page_size)

## Other Profiles
@external
def linkProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can add other profile"
    self._addToArray(self.linkedProfiles, _profile)
    self.linkedProfileCount += 1

@external
def removeLinkedProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can remove linked profile"
    self._removeFromArray(self.linkedProfiles, _profile)
    self.linkedProfileCount -= 1

@view
@external
def getLinkedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.linkedProfiles, _page, _page_size)

@view
@external
def getRecentLinkedProfiles(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySliceReverse(self.linkedProfiles, self.linkedProfileCount, _page, _page_size)

## My Commissions (Artist-Only)
@external
def addMyCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can add my commission"
    assert self.isArtist, "Only artists can add my commissions"
    self._addToArray(self.myCommissions, _commission)
    self.myCommissionCount += 1

@external
def removeMyCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove my commission"
    assert self.isArtist, "Only artists can remove my commissions"
    self._removeFromArray(self.myCommissions, _commission)
    self.myCommissionCount -= 1

@view
@external
def getMyCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have my commissions"
    return self._getArraySlice(self.myCommissions, _page, _page_size)

@view
@external
def getRecentMyCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have my commissions"
    return self._getArraySliceReverse(self.myCommissions, self.myCommissionCount, _page, _page_size)

## Additional Mint ERC1155s (Artist-Only)
@external
def addAdditionalMintErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can add additional mint ERC1155"
    assert self.isArtist, "Only artists can add additional mint ERC1155s"
    self._addToArray(self.additionalMintErc1155s, _erc1155)
    self.additionalMintErc1155Count += 1

@external
def removeAdditionalMintErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can remove additional mint ERC1155"
    assert self.isArtist, "Only artists can remove additional mint ERC1155s"
    self._removeFromArray(self.additionalMintErc1155s, _erc1155)
    self.additionalMintErc1155Count -= 1

@view
@external
def getAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have additional mint ERC1155s"
    return self._getArraySlice(self.additionalMintErc1155s, _page, _page_size)

@view
@external
def getRecentAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have additional mint ERC1155s"
    return self._getArraySliceReverse(self.additionalMintErc1155s, self.additionalMintErc1155Count, _page, _page_size)

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

## Art Pieces

@external
def createArtPiece(_art_piece_template: address, _image_data: Bytes[45000], _title: String[100], _description: Bytes[200], _is_artist: bool, _other_party: address, _commission_hub: address, _ai_generated: bool) -> address:
    """
    Create a new art piece through this profile
    _art_piece_template: Address of the ArtPiece template contract to clone
    _is_artist: True if caller is the artist, False if caller is the commissioner
    _other_party: Address of the other party (artist if caller is commissioner, commissioner if caller is artist)
    """
    assert msg.sender == self.owner, "Only profile owner can create art"
    assert _art_piece_template != empty(address), "ArtPiece template address required"
    
    # Determine owner and artist based on caller's role
    owner_input: address = empty(address)
    artist_input: address = empty(address)
    
    if _is_artist:
        # Caller is the artist
        artist_input = self.owner  # The profile owner is the artist
        owner_input = _other_party if _other_party != empty(address) else self.owner  # If no commissioner specified, owner is also artist
    else:
        # Caller is the commissioner/owner
        owner_input = self.owner  # The profile owner is the commissioner
        artist_input = _other_party if _other_party != empty(address) else self.owner  # If no artist specified, commissioner is also artist
    
    # Create minimal proxy to the ArtPiece template
    art_piece_address: address = create_minimal_proxy_to(_art_piece_template)
    
    # Initialize the art piece proxy
    art_piece: ArtPiece = ArtPiece(art_piece_address)
    extcall art_piece.initialize(
        _image_data,
        _title,
        _description,
        owner_input,
        artist_input,
        _commission_hub,
        _ai_generated
    )
    
    # Add to my art collection
    self._addToArray(self.myArt, art_piece_address)
    self.myArtCount += 1
    
    return art_piece_address

@external
def addArtPiece(_art_piece: address):
    assert msg.sender == self.owner, "Only owner can add art piece"
    
    # Get the art piece owner and artist
    art_piece: ArtPiece = ArtPiece(_art_piece)
    art_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    
    # Verify the profile owner is either the art piece owner or artist
    assert self.owner == art_owner or self.owner == art_artist, "Can only add art you own or created"
    
    self._addToArray(self.myArt, _art_piece)
    self.myArtCount += 1

@external
def removeArtPiece(_art_piece: address):
    assert msg.sender == self.owner, "Only owner can remove art piece"
    self._removeFromArray(self.myArt, _art_piece)
    self.myArtCount -= 1

@view
@external
def getArtPieces(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.myArt, _page, _page_size)

@view
@external
def getRecentArtPieces(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySliceReverse(self.myArt, self.myArtCount, _page, _page_size)

@view
@external
def getLatestArtPieces() -> DynArray[address, 5]:
    result: DynArray[address, 5] = []
    
    # If no art pieces exist, return empty array
    if self.myArtCount == 0:
        return result
    
    # Get minimum of 5 or available art pieces
    items_to_return: uint256 = min(5, self.myArtCount)
    
    # Start from the last (most recent) item and work backwards
    # Using safe indexing to prevent underflow
    for i: uint256 in range(0, items_to_return, bound=5):
        if i < self.myArtCount:  # Safety check
            idx: uint256 = self.myArtCount - 1 - i
            result.append(self.myArt[idx])
    
    return result
