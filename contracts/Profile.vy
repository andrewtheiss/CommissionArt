# @version 0.4.1

# Profile Contract
# This contract represents a user's profile, with features for both regular users and artists.
# It is designed to be cloned by the ProfileHub contract for each user.

# State Variables

# Owner of the profile (user address)
deployer: public(address)  # New variable to store the deployer's address
hub: public(address)  # Address of the hub that created this profile
owner: public(address)
profileImage: public(String[45000])

# Commissions and counters
commissions: public(DynArray[address, 100000])
commissionCount: public(uint256)
unverifiedCommissions: public(DynArray[address, 10000])
unverifiedCommissionCount: public(uint256)
allowUnverifiedCommissions: public(bool)


# Art pieces collection
myArt: public(DynArray[address, 100000])
myArtCount: public(uint256)

# Collector ERC1155s
collectorErc1155s: public(DynArray[address, 100000])
collectorErc1155Count: public(uint256)

# Profile socials and counters
likedProfiles: public(DynArray[address, 10000])
likedProfileCount: public(uint256)
whitelist: public(HashMap[address, bool])
blacklist: public(HashMap[address, bool])
linkedProfiles: public(DynArray[address, 100])  
linkedProfileCount: public(uint256)


# ERC1155 addresses for supporting additional or items for sale
isArtist: public(bool)                                         # Profile is an artist
artistCommissionedWorks: public(DynArray[address, 100000])               # Commissions this artist has
artistCommissionedWorkCount: public(uint256)                             # Count of artist's commissions
artistErc1155sToSell: public(DynArray[address, 100000])      # Additional mint ERC1155s for the artist
artistErc1155sToSellCount: public(uint256)                    # Count of additional ERC1155s
artistCommissionToErc1155Map: public(HashMap[address, address])  # Map of commission addresses to mint ERC1155 addresses
artistProceedsAddress: public(address)                               # Address to receive proceeds from sales

# Profile expansion (for future features)
profileExpansion: public(address)

# Interface for ArtPiece contract
interface ArtPiece:
    def getOwner() -> address: view
    def getArtist() -> address: view
    def initialize(_token_uri_data: String[45000], _title_input: String[100], _description_input: String[200], _owner_input: address, _artist_input: address, _commission_hub: address, _ai_generated: bool): nonpayable

# Constructor
@deploy
def __init__():
    self.deployer = msg.sender  # Set deployer to msg.sender during deployment

# Initialization Function
@external
def initialize(_owner: address):
    assert self.owner == empty(address), "Already initialized"
    self.owner = _owner
    self.hub = msg.sender  # Set the hub to be the contract that called initialize
    self.deployer = msg.sender  # Also set deployer to be the same as hub for backward compatibility
    self.isArtist = False  # Default to non-artist
    self.allowUnverifiedCommissions = True  # Default to allowing commissions
    self.profileExpansion = empty(address)
    self.artistProceedsAddress = _owner  # Default proceeds to owner's address
    
    # Initialize counters
    self.commissionCount = 0
    self.unverifiedCommissionCount = 0
    self.likedProfileCount = 0
    self.linkedProfileCount = 0
    self.artistCommissionedWorkCount = 0
    self.artistErc1155sToSellCount = 0
    self.myArtCount = 0
    self.collectorErc1155Count = 0

# Helper Functions


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
def setProfileImage(_image: String[45000]):
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
    self.artistProceedsAddress = _address

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
    assert _commission not in self.commissions, "Commission already added"
    self.commissions.append(_commission)
    self.commissionCount += 1

@external
def removeCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove commission"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.commissions), bound=1000):
        if self.commissions[i] == _commission:
            index = i
            found = True
            break
    
    # If not found, revert
    assert found, "Commission not found"
    
    # Swap with the last element and pop
    if index < len(self.commissions) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.commissions[len(self.commissions) - 1]
        # Replace the item to remove with the last item
        self.commissions[index] = last_item
    
    # Pop the last item (now a duplicate if we did the swap)
    self.commissions.pop()
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
    assert _commission not in self.unverifiedCommissions, "Unverified commission already added"
    self.unverifiedCommissions.append(_commission)
    self.unverifiedCommissionCount += 1

@external
def removeUnverifiedCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove unverified commission"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.unverifiedCommissions), bound=1000):
        if self.unverifiedCommissions[i] == _commission:
            index = i
            found = True
            break
    
    # If not found, revert
    assert found, "Unverified commission not found"
    
    # Swap with the last element and pop
    if index < len(self.unverifiedCommissions) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.unverifiedCommissions[len(self.unverifiedCommissions) - 1]
        # Replace the item to remove with the last item
        self.unverifiedCommissions[index] = last_item
    
    # Pop the last item (now a duplicate if we did the swap)
    self.unverifiedCommissions.pop()
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
    assert _profile not in self.likedProfiles, "Profile already liked"
    self.likedProfiles.append(_profile)
    self.likedProfileCount += 1

@external
def removeLikedProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can remove liked profile"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.likedProfiles), bound=1000):
        if self.likedProfiles[i] == _profile:
            index = i
            found = True
            break
    
    # If not found, revert
    assert found, "Profile not found"
    
    # Swap with the last element and pop
    if index < len(self.likedProfiles) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.likedProfiles[len(self.likedProfiles) - 1]
        # Replace the item to remove with the last item
        self.likedProfiles[index] = last_item
    
    # Pop the last item (now a duplicate if we did the swap)
    self.likedProfiles.pop()
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
    assert _profile not in self.linkedProfiles, "Profile already linked"
    self.linkedProfiles.append(_profile)
    self.linkedProfileCount += 1

@external
def removeLinkedProfile(_profile: address):
    assert msg.sender == self.owner, "Only owner can remove linked profile"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.linkedProfiles), bound=1000):
        if self.linkedProfiles[i] == _profile:
            index = i
            found = True
            break
    
    # If not found, revert
    assert found, "Linked profile not found"
    
    # Swap with the last element and pop
    if index < len(self.linkedProfiles) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.linkedProfiles[len(self.linkedProfiles) - 1]
        # Replace the item to remove with the last item
        self.linkedProfiles[index] = last_item
    
    # Pop the last item (now a duplicate if we did the swap)
    self.linkedProfiles.pop()
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
    assert _commission not in self.artistCommissionedWorks, "Commission already added"
    self.artistCommissionedWorks.append(_commission)
    self.artistCommissionedWorkCount += 1

@external
def removeMyCommission(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove my commission"
    assert self.isArtist, "Only artists can remove my commissions"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.artistCommissionedWorks), bound=1000):
        if self.artistCommissionedWorks[i] == _commission:
            index = i
            found = True
            break
    
    # If not found, revert
    assert found, "My commission not found"
    
    # Swap with the last element and pop
    if index < len(self.artistCommissionedWorks) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.artistCommissionedWorks[len(self.artistCommissionedWorks) - 1]
        # Replace the item to remove with the last item
        self.artistCommissionedWorks[index] = last_item
    
    # Pop the last item (now a duplicate if we did the swap)
    self.artistCommissionedWorks.pop()
    self.artistCommissionedWorkCount -= 1

@view
@external
def getArtistCommissionedWorks(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have my commissions"
    return self._getArraySlice(self.artistCommissionedWorks, _page, _page_size)

@view
@external
def getRecentArtistCommissionedWorks(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have my commissions"
    return self._getArraySliceReverse(self.artistCommissionedWorks, self.artistCommissionedWorkCount, _page, _page_size)

## Additional Mint ERC1155s (Artist-Only)
@external
def addAdditionalMintErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can add additional mint ERC1155"
    assert self.isArtist, "Only artists can add additional mint ERC1155s"
    assert _erc1155 not in self.artistErc1155sToSell, "ERC1155 already added"
    self.artistErc1155sToSell.append(_erc1155)
    self.artistErc1155sToSellCount += 1

@external
def removeAdditionalMintErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can remove additional mint ERC1155"
    assert self.isArtist, "Only artists can remove additional mint ERC1155s"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.artistErc1155sToSell), bound=1000):
        if self.artistErc1155sToSell[i] == _erc1155:
            index = i
            found = True
            break
    
    # If not found, revert
    assert found, "Additional mint ERC1155 not found"
    
    # Swap with the last element and pop
    if index < len(self.artistErc1155sToSell) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.artistErc1155sToSell[len(self.artistErc1155sToSell) - 1]
        # Replace the item to remove with the last item
        self.artistErc1155sToSell[index] = last_item
    
    # Pop the last item (now a duplicate if we did the swap)
    self.artistErc1155sToSell.pop()
    self.artistErc1155sToSellCount -= 1

@view
@external
def getAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have additional mint ERC1155s"
    return self._getArraySlice(self.artistErc1155sToSell, _page, _page_size)

@view
@external
def getRecentAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.isArtist, "Only artists have additional mint ERC1155s"
    return self._getArraySliceReverse(self.artistErc1155sToSell, self.artistErc1155sToSellCount, _page, _page_size)

## Map Commission to Mint ERC1155 (Artist-Only)
@external
def mapCommissionToMintErc1155(_commission: address, _erc1155: address):
    assert msg.sender == self.owner, "Only owner can map commission to mint ERC1155"
    assert self.isArtist, "Only artists can map commission to mint ERC1155"
    self.artistCommissionToErc1155Map[_commission] = _erc1155

@external
def removeMapCommissionToMintErc1155(_commission: address):
    assert msg.sender == self.owner, "Only owner can remove map commission to mint ERC1155"
    assert self.isArtist, "Only artists can remove map commission to mint ERC1155"
    self.artistCommissionToErc1155Map[_commission] = empty(address)

@view
@external
def getMapCommissionToMintErc1155(_commission: address) -> address:
    assert self.isArtist, "Only artists have map commission to mint ERC1155"
    return self.artistCommissionToErc1155Map[_commission]

## Art Pieces

@external
def createArtPiece(_art_piece_template: address, _token_uri_data: String[45000], _title: String[100], _description: String[200], _is_artist: bool, _other_party: address, _commission_hub: address, _ai_generated: bool) -> address:
    """
    Create a new art piece through this profile
    _art_piece_template: Address of the ArtPiece template contract to clone
    _is_artist: True if caller is the artist, False if caller is the commissioner
    _other_party: Address of the other party (artist if caller is commissioner, commissioner if caller is artist)
    """
    # Check if the caller is either:
    # 1. The profile owner (direct user call)
    # 2. The hub that created this profile (ProfileHub)
    # 3. The deployer of this profile contract (system admin)
    assert msg.sender == self.owner or msg.sender == self.hub or msg.sender == self.deployer, "Only profile owner, hub, or deployer can create art"
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
        _token_uri_data,
        _title,
        _description,
        owner_input,
        artist_input,
        _commission_hub,
        _ai_generated
    )
    
    # Add to my art collection
    self.myArt.append(art_piece_address)
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
    
    assert _art_piece not in self.myArt, "Art piece already added"
    self.myArt.append(_art_piece)
    self.myArtCount += 1

@external
def removeArtPiece(_art_piece: address):
    assert msg.sender == self.owner, "Only owner can remove art piece"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.myArt), bound=1000):
        if self.myArt[i] == _art_piece:
            index = i
            found = True
            break
    
    # If not found, revert
    assert found, "Art piece not found"
    
    # Swap with the last element and pop
    if index < len(self.myArt) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.myArt[len(self.myArt) - 1]
        # Replace the item to remove with the last item
        self.myArt[index] = last_item
    
    # Pop the last item (now a duplicate if we did the swap)
    self.myArt.pop()
    self.myArtCount -= 1

@view
@external
def getArtPieces(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.myArt, _page, _page_size)

@view
@external
def getArtPieceAtIndex(_index: uint256) -> address:
    return self.myArt[_index]
    
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

## Collector ERC1155s
@external
def addCollectorErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can add collector ERC1155"
    assert _erc1155 not in self.collectorErc1155s, "ERC1155 already added"
    self.collectorErc1155s.append(_erc1155)
    self.collectorErc1155Count += 1

@external
def removeCollectorErc1155(_erc1155: address):
    assert msg.sender == self.owner, "Only owner can remove collector ERC1155"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.collectorErc1155s), bound=1000):
        if self.collectorErc1155s[i] == _erc1155:
            index = i
            found = True
            break
    
    # If not found, revert
    assert found, "Collector ERC1155 not found"
    
    # Swap with the last element and pop
    if index < len(self.collectorErc1155s) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.collectorErc1155s[len(self.collectorErc1155s) - 1]
        # Replace the item to remove with the last item
        self.collectorErc1155s[index] = last_item
    
    # Pop the last item (now a duplicate if we did the swap)
    self.collectorErc1155s.pop()
    self.collectorErc1155Count -= 1

@view
@external
def getCollectorErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySlice(self.collectorErc1155s, _page, _page_size)

@view
@external
def getRecentCollectorErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    return self._getArraySliceReverse(self.collectorErc1155s, self.collectorErc1155Count, _page, _page_size)

@view
@external
def getLatestCollectorErc1155s() -> DynArray[address, 5]:
    result: DynArray[address, 5] = []
    
    # If no ERC1155 tokens exist, return empty array
    if self.collectorErc1155Count == 0:
        return result
    
    # Get minimum of 5 or available ERC1155 tokens
    items_to_return: uint256 = min(5, self.collectorErc1155Count)
    
    # Start from the last (most recent) item and work backwards
    # Using safe indexing to prevent underflow
    for i: uint256 in range(0, items_to_return, bound=5):
        if i < self.collectorErc1155Count:  # Safety check
            idx: uint256 = self.collectorErc1155Count - 1 - i
            result.append(self.collectorErc1155s[idx])
    
    return result

@view
@external
def isCollectorErc1155(_erc1155: address) -> bool:
    for i: uint256 in range(0, len(self.collectorErc1155s), bound=1000):
        if self.collectorErc1155s[i] == _erc1155:
            return True
    return False
