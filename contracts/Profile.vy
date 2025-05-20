# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# Profile Contract
# This contract represents a user's profile, with features for both regular users and artists.
# It is designed to be cloned by the ProfileFactoryAndRegistry contract for each user.

# State Variables
event CommissionLinked:
    profile: indexed(address)
    art_piece: indexed(address)
    is_artist: bool

event UnverifiedCommissionLinked:
    profile: indexed(address)
    art_piece: indexed(address)

event CommissionVerified:
    profile: indexed(address)
    art_piece: indexed(address)

event CommissionUnverified:
    profile: indexed(address)
    art_piece: indexed(address)

event CommissionFailedToLink:
    profile: indexed(address)
    art_piece: indexed(address)
    reason: String[100]

# Constants for standardized pagination and unified array capacities
PAGE_SIZE: constant(uint256) = 20
MAX_ITEMS: constant(uint256) = 10**8  # unified max length for all item lists (adjusted if needed to original limits)

# Owner of the profile (user address)
profileFactoryAndRegistry: public(address)  # Address of the hub that created this profile
owner: public(address)
profileImage: public(address)  # Changed from Bytes[45000] to address

# Commissions and counters
myCommissions: public(DynArray[address, MAX_ITEMS])
myCommissionExists: public(HashMap[address, bool])
myCommissionCount: public(uint256)
myUnverifiedCommissions: public(DynArray[address, MAX_ITEMS])
myUnverifiedCommissionsExists: public(HashMap[address, bool])
myUnverifiedCommissionCount: public(uint256)
allowUnverifiedCommissions: public(bool)

# Add myCommissionRole mapping to track role at time of myCommission upload
myCommissionRole: public(HashMap[address, bool])  # true = artist, false = commissioner

# Commission hubs owned by this profile
myCommissionHubs: public(DynArray[address, 10**8])
myCommissionHubCount: public(uint256)

# Art pieces collection
myArt: public(DynArray[address, MAX_ITEMS])
myArtCount: public(uint256)

# Profile socials and counters
whitelist: public(HashMap[address, bool])
blacklist: public(HashMap[address, bool])

# Profile social (for future features)
profileSocial: public(address)

# ArtSales1155 link (forever tied after set)
artSales1155: public(address)

# Artist status for this profile
isArtist: public(bool)

# Interface for ProfileFactoryAndRegistry
interface ProfileFactoryAndRegistry:
    def artCommissionHubOwners() -> address: view
    def getProfile(_owner: address) -> address: view
    def getOwner() -> address: view

# Interface for Profile (for cross-profile calls)
interface Profile:
    def updateCommissionVerificationStatus(_commission_art_piece: address): nonpayable
    def getOwner() -> address: view
    def linkArtPieceAsMyCommission(_art_piece: address) -> bool: nonpayable

# Interface for ArtPiece contract - updated with new verification methods
interface ArtPiece:
    def getOwner() -> address: view
    def getArtist() -> address: view
    def getCommissioner() -> address: view
    def getArtCommissionHubAddress() -> address: view
    def initialize(_token_uri_data: Bytes[45000], _token_uri_data_format: String[10], _title_input: String[100], _description_input: String[200], _commissioner_input: address, _artist_input: address, _commission_hub: address, _ai_generated: bool, _profile_factory_address: address): nonpayable
    def verifyAsArtist(): nonpayable
    def verifyAsCommissioner(): nonpayable
    def isFullyVerifiedCommission() -> bool: view # returns true if the art piece is a VERIFIED commissioner != artist AND fully verified)
    def isUnverifiedCommission() -> bool: view # returns true if the art piece is an cnverified commission (commissioner != artist but not fully verified)
    def isPrivateOrNonCommissionPiece() -> bool: view # returns true if the art piece is private/non-commission (commissioner == artist)
    def artistVerified() -> bool: view
    def commissionerVerified() -> bool: view

# Interface for ArtCommissionHub
interface ArtCommissionHub:
    def owner() -> address: view
    def submitCommission(_art_piece: address): nonpayable
    def setWhitelistedArtPieceContract(_art_piece_contract: address): nonpayable

# Interface for ArtSales1155 (expanded)
interface ArtSales1155:
    def getAdditionalMintErc1155s(_page: uint256, _page_size: uint256) -> DynArray[address, 100]: view

# Event for myCommission verification in profile context
event CommissionVerifiedInProfile:
    profile: indexed(address)
    art_piece: indexed(address)
    is_artist: bool

# Constructor
@deploy
def __init__():
    self.profileFactoryAndRegistry = msg.sender  # Set deployer to msg.sender during deployment

# Initialization Function
@external
def initialize(_owner: address, _profile_social: address, _is_artist: bool = False):
    assert self.owner == empty(address), "Already initialized"
    assert self.profileFactoryAndRegistry == msg.sender  # Set the hub to be the contract that called initialize
    assert _profile_social != empty(address), "Profile social address cannot be empty"

    self.owner = _owner
    self.isArtist = _is_artist 
    self.profileSocial = _profile_social
    self.allowUnverifiedCommissions = True  # Default to allowing myCommissions
    
    # Initialize counters
    self.myCommissionCount = 0
    self.myUnverifiedCommissionCount = 0
    self.myArtCount = 0
    self.myCommissionHubCount = 0

@internal
@view
def _getDeployer() -> address:
    profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
    return staticcall profile_factory.getOwner()


# Toggle allowing new myCommissions
@external
def setAllowUnverifiedCommissions(_allow: bool):
    assert msg.sender == self.owner, "Only owner can set allow new myCommissions"
    self.allowUnverifiedCommissions = _allow

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

# Set profile image
@external
def setProfileImage(_profile_image: address):
    assert msg.sender == self.owner, "Only owner can set profile image"
    # check we are owner of the art piece
    art_piece: ArtPiece = ArtPiece(_profile_image)
    effective_owner: address = staticcall art_piece.getOwner()
    assert effective_owner == self.owner or staticcall(art_piece.getArtist()) == self.owner, "Only owner can set profile image"
    self.profileImage = _profile_image

# linkArtPieceAsMyCommission
# -------------
# Links a myCommission to this profile, always to the myUnverified list until both parties verify it
# Use case:
# - If the profile is an artist, this is a piece of work they created for someone else (they are the artist).
# - If the profile is a non-artist (commissioner/curator), this is a piece of work they commissioned from an artist (they are the client).
# - The contract records the user's role at the time of upload in myCommissionRole.
#
@external
def linkArtPieceAsMyCommission(_art_piece: address) -> bool:
    """
    @notice Adds an ArtPiece to this profile, to myCommissions or myUnverified list based on verification status
    @dev Access control:
         - self.owner: The owner of the profile can add myCommissions to their own profile
         - self.profileFactoryAndRegistry: The ProfileFactoryAndRegistry contract can add myCommissions on behalf of users
         - Any other user: Can add myCommissions based on whitelist/blacklist status
    @param _art_piece The address of the myCommission art piece
    """
    # Get the art piece details to check permissions
    art_piece: ArtPiece = ArtPiece(_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    is_potential_commission: bool = commissioner != art_artist
    
    # Check who the sender is
    is_profile_owner: bool = msg.sender == self.owner
    is_profile_factory_and_registry: bool = msg.sender == self.profileFactoryAndRegistry
    is_art_creator: bool = msg.sender == art_artist or msg.sender == commissioner or staticcall Profile(commissioner).getOwner() == art_artist or staticcall Profile(art_artist).getOwner() == commissioner
    is_art_creator_profile: bool = staticcall ProfileFactoryAndRegistry(self.profileFactoryAndRegistry).getProfile(art_artist) == msg.sender or staticcall ProfileFactoryAndRegistry(self.profileFactoryAndRegistry).getProfile(commissioner) == msg.sender
    
    # Check to make sure its a valid commission and function caller has permission to add it
    # The rest of these gracefully return, however this should hard fail because noone else 
    #   should be calling this
    assert is_profile_owner or is_profile_factory_and_registry or is_art_creator or is_art_creator_profile, "No permission to add myCommission"

    if self.myCommissionExists[_art_piece]:
        log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Commission already added")
        return False

    if not is_potential_commission:
        log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Not a myCommission art piece")
        return False
    
    # If artist/commissioner are blacklisted by THIS profile, reject the myCommission
    if (self.blacklist[commissioner] or self.blacklist[art_artist]):
        log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Artist or commissioner is on blacklist")
        return False

    # Inside creating a ArtPiece from Profile, the artist or commissioner can be whiltelisted
    if (is_art_creator_profile and not (self.whitelist[commissioner] or self.whitelist[art_artist])):
        log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Artist or commissioner is not whitelisted")
        return False
    
    # Determine if this should be added to verified or myUnverified list
    # Commissions are now verified only when both parties verify them
    is_verified_by_both: bool = False
    if is_potential_commission:
        is_verified_by_both = staticcall art_piece.isFullyVerifiedCommission()
    
    # Add to verified list
    if is_verified_by_both:
        self.myCommissions.append(_art_piece)
        self.myCommissionCount += 1
        self.myCommissionRole[_art_piece] = self.isArtist
        self.myCommissionExists[_art_piece] = True
        log CommissionLinked(profile=self, art_piece=_art_piece, is_artist=self.isArtist)

    # Add to myUnverified list
    else:
        if not self.allowUnverifiedCommissions:
            log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Unverified myCommissions are disallowed by this Profile.")
            return False
        if self.myUnverifiedCommissionsExists[_art_piece]:
            log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Commission already added, but myUnverified.  Please verify.")
            return False

        # Add to myUnverified list
        self.myUnverifiedCommissions.append(_art_piece)
        self.myUnverifiedCommissionCount += 1
        self.myCommissionRole[_art_piece] = self.isArtist
        self.myUnverifiedCommissionsExists[_art_piece] = True
        log UnverifiedCommissionLinked(profile=self, art_piece=_art_piece)

    return True

#
# verifyArtLinkedToMyCommission
# -------------
# Verifies an art piece linked to myCommissions. The profile owner can verify as artist or commissioner depending on their role.
# Once both parties verify, the piece is moved from myUnverified to verified and ownership may transfer to the hub.
#
@external
def verifyArtLinkedToMyCommission(_art_piece: address):
    """
    @notice Verifies half of a myCommission piece (either as artist or as commissioner) based on the profile owner's role
    @dev Only the profile owner can call this
    @param _art_piece The address of the myCommission art piece to verify
    """
    assert msg.sender == self.owner, "Only profile owner can verify myCommission"
    assert self.myUnverifiedCommissionsExists[_art_piece], "Unverified myCommission not found"
    
    # Get the art piece details
    art_piece: ArtPiece = ArtPiece(_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()

    # Determine if the profile owner is the artist or commissioner
    is_artist: bool = self.owner == art_artist
    is_commissioner: bool = self.owner == commissioner
    assert is_artist or is_commissioner, "Profile owner not involved in this myCommission"

    # Check verification status
    artist_verified: bool = staticcall art_piece.artistVerified()
    commissioner_verified: bool = staticcall art_piece.commissionerVerified()
    
    # Verify myCommission based on profile role if not already verified
    if is_artist and not artist_verified:
        # Verify as artist
        extcall art_piece.verifyAsArtist()
    elif is_commissioner and not commissioner_verified:
        # Verify as commissioner
        extcall art_piece.verifyAsCommissioner()

    #TODO - verify artist and commissioner currently have a check that msg.sender is the person, but 
    #   it actually gets set to this Profile address instead.  i need to get the owner of the profile if 
    #   its an address
    
    # Check if now fully verified - this will move from myUnverified to verified
    is_now_verified: bool = staticcall art_piece.isFullyVerifiedCommission()
    
    # If now verified, move from myUnverified to verified list
    if is_now_verified:
        # Check if it's in the myUnverified list
        found_myUnverified: bool = False
        myUnverified_index: uint256 = 0
        
        for i: uint256 in range(0, len(self.myUnverifiedCommissions), bound=1000):
            if i >= len(self.myUnverifiedCommissions):
                break
            if self.myUnverifiedCommissions[i] == _art_piece:
                myUnverified_index = i
                found_myUnverified = True
                break
        
        if found_myUnverified:
            # Remove from myUnverified list
            if myUnverified_index < len(self.myUnverifiedCommissions) - 1:
                last_item: address = self.myUnverifiedCommissions[len(self.myUnverifiedCommissions) - 1]
                self.myUnverifiedCommissions[myUnverified_index] = last_item
            self.myUnverifiedCommissions.pop()
            self.myUnverifiedCommissionCount -= 1
        
        # Add to verified list if not already there
        if _art_piece not in self.myCommissions:
            self.myCommissions.append(_art_piece)
            self.myCommissionCount += 1
        
        # If this profile owner is the commissioner, also add to myArt if not already there
        if is_commissioner and _art_piece not in self.myArt:
            self.myArt.append(_art_piece)
            self.myArtCount += 1
        
        # Now we need to update the other party's profile as well
        # Get the profile factory registry to find the other party's profile
        if self.profileFactoryAndRegistry != empty(address):
            # Try to find the other party's profile
            other_party: address = empty(address)
            if is_artist:
                # If this profile owner is the artist, the other party is the commissioner
                other_party = commissioner
            else:
                # If this profile owner is the commissioner, the other party is the artist
                other_party = art_artist
            
            # If we have the other party's address, try to update their profile
            if other_party != empty(address):
                # Get the other party's profile from the hub
                profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
                other_profile: address = staticcall profile_factory.getProfile(other_party)
                
                # If the other party has a profile, update their myCommission status
                if other_profile != empty(address):
                    # Call the updateCommissionVerificationStatus method on the other profile
                    profile_interface: Profile = Profile(other_profile)
                    extcall profile_interface.updateCommissionVerificationStatus(_art_piece)
    
    log CommissionVerifiedInProfile(profile=self, art_piece=_art_piece, is_artist=is_artist)

#
# removeArtLinkToMyCommission
# ----------------
# Removes a myCommission from this profile's verified or myUnverified myCommissions list
# Use case:
# - If a myCommission is no longer relevant, or was added in error, it can be removed.
# - This also removes the recorded role for that myCommission.
# - If you remove a commission from your myCommissions list, it will REMOVE itself ONLY from unverified ArtCommissionHubs
#
@external
def removeArtLinkToMyCommission(_my_commission: address):
    """
    @notice Removes a myCommission from this profile's verified or myUnverified myCommissions list
    @dev Access control:
         - self.owner: The owner of the profile can remove their own myCommissions
         - self.profileFactoryAndRegistry: The ProfileFactoryAndRegistry contract can remove myCommissions on behalf of users
         - Art piece artist: Can remove myUnverified myCommissions they created
         - ArtCommissionHub owner: Can remove myCommissions from the hub
    @param _my_commission The address of the myCommission to remove
    """

    # See if this is already a verified commission or linked as verified
    assert self.myCommissionExists[_my_commission] or self.myUnverifiedCommissionsExists[_my_commission], "No commission to unlink"
    art_piece: ArtPiece = ArtPiece(_my_commission)

    # Get the art piece details to check permissions
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    
    is_art_artist: bool = msg.sender == art_artist
    is_commissioner: bool = msg.sender == commissioner
    is_profile_factory_and_registry: bool = msg.sender == self.profileFactoryAndRegistry
    
    # Check if unverified.  If so, its not in any ArtCommissionHubs
    if (self.myUnverifiedCommissionsExists[_my_commission]):
        for i: uint256 in range(0, len(self.myUnverifiedCommissions), bound=10000):
            if i >= self.myUnverifiedCommissionCount:
                break
            if self.myUnverifiedCommissions[i] == _my_commission:
                last_item: address = self.myUnverifiedCommissions[len(self.myUnverifiedCommissions) - 1]
                self.myUnverifiedCommissions[i] = last_item
                self.myUnverifiedCommissions.pop()
                self.myUnverifiedCommissionCount -= 1
                break
        self.myUnverifiedCommissionsExists[_my_commission] = False

    elif (self.myCommissionExists[_my_commission]):
        for i: uint256 in range(0, len(self.myCommissions), bound=10000):
            if i >= self.myCommissionCount:
                break
            if self.myCommissions[i] == _my_commission:
                last_item: address = self.myCommissions[len(self.myCommissions) - 1]
                self.myCommissions[i] = last_item
                self.myCommissions.pop()
                self.myCommissionCount -= 1
                break
        self.myCommissionExists[_my_commission] = False


#
# getCommissions
# ---------------
# Returns a paginated list of myCommissions (verified or myUnverified) for this profile.
# Use case:
# - Used by the frontend to display all myCommissions associated with this profile, either as artist or commissioner.
# - The frontend can also query myCommissionRole to determine the user's role at the time of upload for each myCommission.
# Example:
# - Alice wants to see all her myCommissions (as artist or as commissioner): getCommissions(page, pageSize).
#
@view
@external
def getCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.myCommissions)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.myCommissions[start + i])
    return result

@view
@external
def getRecentCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.myCommissions)
    
    # Early returns for empty array or out-of-bounds page
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    
    # Calculate start index from the end and how many items to return
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    
    # Populate result array in reverse order
    for i: uint256 in range(0, items, bound=100):
        result.append(self.myCommissions[start - i])
    
    return result

## Unverified Commissions
#
# getUnverifiedCommissions
# -------------------------
# Returns a paginated list of myUnverified myCommissions for this profile.
# Use case:
# - Used by the frontend to display all myUnverified myCommissions associated with this profile.
# Example:
# - Alice wants to see all her myUnverified myCommissions: getUnverifiedCommissions(page, pageSize).
#
@view
@external
def getUnverifiedCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.myUnverifiedCommissions)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.myUnverifiedCommissions[start + i])
    return result

@view
@external
def getRecentUnverifiedCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.myUnverifiedCommissions)
    
    # Early returns for empty array or out-of-bounds page
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    
    # Calculate start index from the end and how many items to return
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    
    # Populate result array in reverse order
    for i: uint256 in range(0, items, bound=100):
        result.append(self.myUnverifiedCommissions[start - i])
    
    return result

@external
def clearUnverifiedCommissions():
    assert msg.sender == self.owner, "Only owner can clear myUnverified myCommissions"
    self.myUnverifiedCommissions = []
    self.myUnverifiedCommissionCount = 0

# Set ArtSales1155 address (can only be set once)
@external
def setArtSales1155(_sales: address):
    assert msg.sender == self.owner, "Only owner can set sales contract"
    assert self.artSales1155 == empty(address), "Sales contract already set"
    assert _sales != empty(address), "Invalid sales contract address"
    self.artSales1155 = _sales

#
# getProfileErc1155sForSale
# ------------------------
# This function allows the profile to retrieve a paginated list of ERC1155 contract addresses that are available for additional minting (for sale or distribution) by this profile's associated ArtSales1155 contract.
#
# How it works:
# - Checks that the artSales1155 address is set (i.e., the sales contract is linked to this profile).
# - Uses a staticcall to the ArtSales1155 contract's getAdditionalMintErc1155s method, passing the requested page and page size.
# - Returns up to 100 ERC1155 addresses from the sales contract, for the given page.
#
# Use case example:
# Suppose a frontend wants to display all ERC1155 tokens that an artist (profile) has put up for sale or additional minting. The frontend can call this method with _page=0 and _page_size=20 to get the first 20 tokens, then increment _page to paginate through the rest.
#
@view
@external
def getProfileErc1155sForSale(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    assert self.artSales1155 != empty(address), "Sales contract not set"
    return staticcall ArtSales1155(self.artSales1155).getAdditionalMintErc1155s(_page, _page_size)

# Three types of art pieces can be created:
# #1 - Personal Art Piece (non-myCommission)
# #2 - Profile Art Piece (special case for profile image) 
# #3 - Commission Art Piece
#
# #3 is the only one which takes considerable extra work as it requires linking the profile back to the ArtPiece
@external
def createArtPiece(
    _art_piece_template: address,
    _token_uri_data: Bytes[45000],
    _token_uri_data_format: String[10],
    _title: String[100],
    _description: String[200],
    _as_artist: bool,
    _other_party: address,
    _ai_generated: bool,
    _art_commission_hub: address = empty(address),  # Register with art myCommission hub
    _is_profile_art: bool = False
) -> address:
    """
    @notice Create a new art piece with optional profile art and myCommission registration
    @dev New workflow: uploader is initial owner, myCommission pieces start with uploader's side verified
    @param _art_piece_template The template contract to clone for this art piece
    @param _token_uri_data The art data
    @param _token_uri_data_format Format of the art data
    @param _title Title of the art piece
    @param _description Description of the art piece
    @param _as_artist Flag indicating if the uploader is the artist (or commissioner)
    @param _other_party Address of the other party (artist if uploader is commissioner, vice versa)
    @param _ai_generated Flag indicating if the art was AI-generated
    @param _art_commission_hub Optional hub address to register myCommission with
    @param _is_profile_art Flag indicating if this is a profile image
    @return The address of the created art piece
    """

    # Who can call this?  
    #        - Profile owner: (create profile art, personal art piece)...  direct call from user ONLY
    #        - Profile owner or ProfileFactoryAndRegistry or Deployer: (register potential commission hub)
    # Check for personal piece or commission art piece
    personal_piece: bool = _is_profile_art or (_other_party == self.owner)
    indirect_creation_call: bool = msg.sender == self._getDeployer() or msg.sender == self.profileFactoryAndRegistry
    if personal_piece:
        assert msg.sender == self.owner, "Only profile owner can create personal art piece"
    else:
        assert msg.sender == self.owner or indirect_creation_call, "Only profile owner or deployer can create commission art piece"
   
    # Variables for ArtPiece initialization
    artist: address = empty(address)
    commissioner: address = empty(address)
    art_commission_hub: address = _art_commission_hub  #overwrite to empty if personal piece...

    # If a Personal piece, it can be 1 of 2 options:
    # #1 - Profile owner creating profile art
    # #2 - Profile owner uploading to MyArt
    if personal_piece:
        art_commission_hub = empty(address)
        artist = self.owner
        commissioner = self.owner

    # if we are the artist, 
    elif _as_artist:
        commissioner = _other_party
        artist = self.owner
    else:
        artist = _other_party
        commissioner = self.owner

    # Create ArtPiece template and initialize
    # ArtPiece will link all parameters to this profile
    art_piece_address: address = create_minimal_proxy_to(_art_piece_template)
    art_piece: ArtPiece = ArtPiece(art_piece_address)
    extcall art_piece.initialize(
        _token_uri_data,
        _token_uri_data_format,
        _title,
        _description,
        commissioner,
        artist,
        art_commission_hub,
        _ai_generated,
        self.profileFactoryAndRegistry
    )
        
    # If profile art, set as profile image
    if _is_profile_art:
        self.profileImage = art_piece_address

    # Add to my art collection 
    self.myArt.append(art_piece_address)
    self.myArtCount += 1

    # If this is a commission, we need to link the profile back to the ArtPiece
    # If we are whitelisted by the other party, we can verify by both immediately and turn into 
    #        a commissioned art piece!
    if not personal_piece:

        # Record uploader as commissioner or artist (verifyAsArtist or verifyAsCommissioner)
        self.myCommissionRole[art_piece_address] = _as_artist
        if artist == self.owner:
            extcall art_piece.verifyAsArtist()
        else:
            extcall art_piece.verifyAsCommissioner()
        
        # Need to try and verify on the other Profile as we might be whitelisted
        # Since we are the Artist, the other party is the commissioner
        # If we are the Commissioner, the other party is the artist
        profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
        other_profile_address: address = staticcall profile_factory.getProfile(_other_party)
        other_profile_instance: Profile = Profile(other_profile_address)
        linked_other_profile: bool = extcall other_profile_instance.linkArtPieceAsMyCommission(art_piece_address)  
                
        # Flag as verified by this account as its the uploader
        # If the other party is set, check if they are whitelisted... if so, verify by both
        # Check if already fully verified (could happen in some edge cases)
        is_verified_by_both: bool = staticcall art_piece.isFullyVerifiedCommission()
        if is_verified_by_both:
            # Add to verified myCommissions
            self.myCommissions.append(art_piece_address)
            self.myCommissionCount += 1
        else:
            # Add to myUnverified myCommissions
            self.myUnverifiedCommissions.append(art_piece_address)
            self.myUnverifiedCommissionCount += 1
            

    # If this art is a potential commission, ArtCommissionHub is provided
    # in this case, we submitCommission to the ArtCommissionHub.. 
    # WE SHOULD NOT DO THIS AS WE JUST WANT VERIFIED PIECES TO BE SUBMITTED
    if art_commission_hub != empty(address):
        _art_commission_hub_link: ArtCommissionHub = ArtCommissionHub(art_commission_hub)
        extcall _art_commission_hub_link.submitCommission(art_piece_address)

    return art_piece_address


@external
def addArtPiece(_art_piece: address):
    """
    @notice Add an existing art piece to this profile
    @dev Only the profile owner can call this, and must be either owner or artist of the piece
    @param _art_piece Address of the art piece to add
    """
    assert msg.sender == self.owner, "Only owner can add art piece"
    
    # Get the art piece owner and artist
    art_piece: ArtPiece = ArtPiece(_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    is_myCommission: bool = staticcall art_piece.isFullyVerifiedCommission()
    
    # Verify the profile owner is either the art piece owner or artist
    assert self.owner == effective_owner or self.owner == art_artist, "Can only add art you own or created"
    
    # First, add to myArt if not already there
    if _art_piece not in self.myArt:
        self.myArt.append(_art_piece)
        self.myArtCount += 1
    
    # If this is a myCommission, determine where to add it
    if is_myCommission:
        is_verified_by_both: bool = staticcall art_piece.isFullyVerifiedCommission()
        
        if is_verified_by_both:
            # Add to verified myCommissions if not already there
            if _art_piece not in self.myCommissions:
                self.myCommissions.append(_art_piece)
                self.myCommissionCount += 1
                # Record the role (owner=commissioner, artist=artist)
                self.myCommissionRole[_art_piece] = (self.owner == art_artist)
        else:
            # Add to myUnverified myCommissions if not already there
            if _art_piece not in self.myUnverifiedCommissions:
                self.myUnverifiedCommissions.append(_art_piece)
                self.myUnverifiedCommissionCount += 1
                # Record the role (owner=commissioner, artist=artist)
                self.myCommissionRole[_art_piece] = (self.owner == art_artist)

@external
def removeArtPiece(_art_piece: address):
    assert msg.sender == self.owner, "Only owner can remove art piece"
    
    # Find the index of the item to remove
    index: uint256 = 0
    found: bool = False
    for i: uint256 in range(0, len(self.myArt), bound=1000):
        if i >= len(self.myArt):
            break
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
    
    # Also check if it's in myCommissions or myUnverified myCommissions and remove if found
    # This is optional - the user can use removeCommission for more explicit control
    
    # Check verified myCommissions
    for i: uint256 in range(0, len(self.myCommissions), bound=1000):
        if i >= len(self.myCommissions):
            break
        if self.myCommissions[i] == _art_piece:
            # Remove from verified list
            if i < len(self.myCommissions) - 1:
                last_item: address = self.myCommissions[len(self.myCommissions) - 1]
                self.myCommissions[i] = last_item
            self.myCommissions.pop()
            self.myCommissionCount -= 1
            # Clear role data (optional)
            self.myCommissionRole[_art_piece] = False
            break
    
    # Check myUnverified myCommissions
    for i: uint256 in range(0, len(self.myUnverifiedCommissions), bound=1000):
        if i >= len(self.myUnverifiedCommissions):
            break
        if self.myUnverifiedCommissions[i] == _art_piece:
            # Remove from myUnverified list
            if i < len(self.myUnverifiedCommissions) - 1:
                last_item: address = self.myUnverifiedCommissions[len(self.myUnverifiedCommissions) - 1]
                self.myUnverifiedCommissions[i] = last_item
            self.myUnverifiedCommissions.pop()
            self.myUnverifiedCommissionCount -= 1
            # Clear role data (optional)
            self.myCommissionRole[_art_piece] = False
            break

@view
@external
def getArtPieces(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.myArt)
    
    # Early returns
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    
    for i: uint256 in range(0, items, bound=100):
        result.append(self.myArt[start + i])
    
    return result
    
@view
@external
def getRecentArtPieces(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.myArt)
    
    # Early returns
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    
    for i: uint256 in range(0, items, bound=100):
        result.append(self.myArt[start - i])
    
    return result

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

@view
@external
def getArtPieceAtIndex(_index: uint256) -> address:
    return self.myArt[_index]

@external
def setIsArtist(_is_artist: bool):
    """
    Set the artist status for this profile. Only the profile owner can call this.
    Use case: Allows a user to toggle their profile between artist and non-artist.
    Example: Alice wants to become an artist: setIsArtist(True).
    """
    assert msg.sender == self.owner, "Only owner can set artist status"
    self.isArtist = _is_artist

## Commission Hubs
#
# addCommissionHub
# ----------------
# Adds a myCommission hub to this profile.
# Use case:
# - When a user becomes the owner of an ArtCommissionHub (either via NFT ownership or generic hub creation),
#   the hub is added to their profile for tracking.
# - Only the hub or owner registry can add hubs to ensure proper ownership tracking.
# Example:
# - When Alice buys an NFT, the ArtCommissionHubOwners calls addCommissionHub to link the hub to Alice's profile.
#
@external
def addCommissionHub(_hub: address):
    # Allow the hub (ProfileFactoryAndRegistry), owner registry, or original deployer to add myCommission hubs
    # Check if we have an owner registry first
    registry_address: address = empty(address)
    if self.profileFactoryAndRegistry != empty(address):
        # Try to get the owner registry from the profile-factory-and-registry
        profile_factory_and_regsitry_interface: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
        registry_address = staticcall profile_factory_and_regsitry_interface.artCommissionHubOwners()
    
    assert msg.sender == self.profileFactoryAndRegistry or msg.sender == self._getDeployer() or msg.sender == registry_address, "Only hub or registry can add myCommission hub"
    
    # Check if hub is already in the list
    hubs_len: uint256 = len(self.myCommissionHubs)
    for i: uint256 in range(10**8):  # Use a large fixed bound
        if i >= hubs_len:
            break
        if self.myCommissionHubs[i] == _hub:
            return  # Hub already exists, nothing to do
    
    # Add the hub to the list
    self.myCommissionHubs.append(_hub)
    self.myCommissionHubCount += 1

#
# removeCommissionHub
# -------------------
# Removes a myCommission hub from this profile's list.
# Use case:
# - When a user transfers ownership of an NFT, the associated hub is removed from their profile.
# - Only the hub or owner registry can remove hubs to ensure proper ownership tracking.
# Example:
# - When Alice sells her NFT to Bob, the ArtCommissionHubOwners calls removeCommissionHub to unlink the hub from Alice's profile.
#
@external
def removeCommissionHub(_hub: address):
    # Allow the hub (ProfileFactoryAndRegistry), owner registry, or original deployer to remove myCommission hubs
    # Check if we have an owner registry first
    registry_address: address = empty(address)
    if self.profileFactoryAndRegistry != empty(address):
        # Try to get the owner registry from the profile-factory-and-registry
        profile_factory_and_regsitry_interface: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
        registry_address = staticcall profile_factory_and_regsitry_interface.artCommissionHubOwners()
    
    assert msg.sender == self.profileFactoryAndRegistry or msg.sender == self._getDeployer() or msg.sender == registry_address, "Only hub or registry can remove myCommission hub"
    
    # Find the index of the hub to remove
    index: uint256 = 0
    found: bool = False
    hubs_len: uint256 = len(self.myCommissionHubs)
    for i: uint256 in range(10**8):  # Use a large fixed bound
        if i >= hubs_len:
            break
        if self.myCommissionHubs[i] == _hub:
            index = i
            found = True
            break
    
    # If hub found, remove it using swap and pop
    if found:
        # If not the last element, swap with the last element
        if index < len(self.myCommissionHubs) - 1:
            last_hub: address = self.myCommissionHubs[len(self.myCommissionHubs) - 1]
            self.myCommissionHubs[index] = last_hub
        # Remove the last element
        self.myCommissionHubs.pop()
        self.myCommissionHubCount -= 1

#
# getCommissionHubs
# ----------------
# Returns a paginated list of myCommission hubs for this profile.
# Use case:
# - Used by the frontend to display all myCommission hubs associated with this profile.
# Example:
# - Alice wants to see all her myCommission hubs: getCommissionHubs(page, pageSize).
#
@view
@external
def getCommissionHubs(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.myCommissionHubs)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(100):  # Fixed upper bound
        if i >= items:
            break
        result.append(self.myCommissionHubs[start + i])
    return result

#
# getRecentCommissionHubs
# ----------------------
# Returns a paginated list of myCommission hubs for this profile, starting from the most recent.
# Use case:
# - Used by the frontend to display the most recent myCommission hubs associated with this profile.
# Example:
# - Alice wants to see her most recent myCommission hubs: getRecentCommissionHubs(page, pageSize).
#
@view
@external
def getRecentCommissionHubs(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.myCommissionHubs)
    
    # Early returns for empty array or out-of-bounds page
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    
    # Calculate start index from the end and how many items to return
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    
    # Populate result array in reverse order
    for i: uint256 in range(100):  # Fixed upper bound
        if i >= items:
            break
        result.append(self.myCommissionHubs[start - i])
    
    return result

# Enhanced batch loading functions for efficient frontend queries

@view
@external
def getBatchArtPieces(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a batch of art pieces with improved capacity
    @dev Allows retrieving up to 50 art pieces at once for efficient frontend loading
    @param _start_idx The starting index in the art array
    @param _count The number of art pieces to retrieve
    @return Array of art piece addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no art pieces or start index is out of bounds
    if self.myArtCount == 0 or _start_idx >= self.myArtCount:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.myArtCount)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.myArt[_start_idx + i])
    
    return result

@view
@external
def getBatchCommissions(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a batch of verified myCommissions with improved capacity
    @dev Allows retrieving up to 50 myCommissions at once for efficient frontend loading
    @param _start_idx The starting index in the myCommissions array
    @param _count The number of myCommissions to retrieve
    @return Array of myCommission addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no myCommissions or start index is out of bounds
    if self.myCommissionCount == 0 or _start_idx >= self.myCommissionCount:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.myCommissionCount)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.myCommissions[_start_idx + i])
    
    return result

@view
@external
def getBatchUnverifiedCommissions(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a batch of myUnverified myCommissions with improved capacity
    @dev Allows retrieving up to 50 myUnverified myCommissions at once for efficient frontend loading
    @param _start_idx The starting index in the myUnverified myCommissions array
    @param _count The number of myUnverified myCommissions to retrieve
    @return Array of myUnverified myCommission addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no myUnverified myCommissions or start index is out of bounds
    if self.myUnverifiedCommissionCount == 0 or _start_idx >= self.myUnverifiedCommissionCount:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.myUnverifiedCommissionCount)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.myUnverifiedCommissions[_start_idx + i])
    
    return result

@view
@external
def getBatchCommissionHubs(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a batch of myCommission hubs with improved capacity
    @dev Allows retrieving up to 50 myCommission hubs at once for efficient frontend loading
    @param _start_idx The starting index in the myCommission hubs array
    @param _count The number of myCommission hubs to retrieve
    @return Array of myCommission hub addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no myCommission hubs or start index is out of bounds
    if self.myCommissionHubCount == 0 or _start_idx >= self.myCommissionHubCount:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.myCommissionHubCount)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.myCommissionHubs[_start_idx + i])
    
    return result

@view
@external
def getArtPiecesByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of art pieces using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the art pieces array
    @param _count The number of art pieces to return (capped at 50)
    @return A list of art piece addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no art pieces or offset is out of bounds
    if self.myArtCount == 0 or _offset >= self.myArtCount:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.myArtCount - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.myArt[_offset + i])
    
    return result

@view
@external
def getCommissionsByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of verified myCommissions using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the myCommissions array
    @param _count The number of myCommissions to return (capped at 50)
    @return A list of myCommission addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no myCommissions or offset is out of bounds
    if self.myCommissionCount == 0 or _offset >= self.myCommissionCount:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.myCommissionCount - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.myCommissions[_offset + i])
    
    return result

@view
@external
def getUnverifiedCommissionsByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of myUnverified myCommissions using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the myUnverified myCommissions array
    @param _count The number of myUnverified myCommissions to return (capped at 50)
    @return A list of myUnverified myCommission addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no myUnverified myCommissions or offset is out of bounds
    if self.myUnverifiedCommissionCount == 0 or _offset >= self.myUnverifiedCommissionCount:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.myUnverifiedCommissionCount - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.myUnverifiedCommissions[_offset + i])
    
    return result

@view
@external
def getCommissionHubsByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of myCommission hubs using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the myCommission hubs array
    @param _count The number of myCommission hubs to return (capped at 50)
    @return A list of myCommission hub addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no myCommission hubs or offset is out of bounds
    if self.myCommissionHubCount == 0 or _offset >= self.myCommissionHubCount:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.myCommissionHubCount - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.myCommissionHubs[_offset + i])
    
    return result

@external
def updateCommissionVerificationStatus(_commission_art_piece: address):
    """
    @notice Updates the verification status of a myCommission in this profile
    @dev Access control:
         - self.owner: The owner of the profile can update verification status
         - The commissioner or artist of the art piece can update status
         - The hub owner can update status
    @param _commission_art_piece The address of the myCommission art piece
    """
    # Get the art piece details
    art_piece: ArtPiece = ArtPiece(_commission_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    is_myCommission: bool = staticcall art_piece.isFullyVerifiedCommission()
    myCommission_hub: address = staticcall art_piece.getArtCommissionHubAddress()
    
    # Check if sender is the owner of this profile
    is_profile_owner: bool = msg.sender == self.owner
    
    # Check if sender is the artist or commissioner of the art piece
    is_art_creator: bool = msg.sender == art_artist or msg.sender == commissioner
    
    # Check if sender is the hub owner
    is_hub_owner: bool = False
    if myCommission_hub != empty(address):
        myCommission_hub_interface: ArtCommissionHub = ArtCommissionHub(myCommission_hub)
        hub_owner: address = staticcall myCommission_hub_interface.owner()
        is_hub_owner = (hub_owner == msg.sender)
    
    # Verify the sender has permission to update verification status
    assert is_profile_owner or is_art_creator or is_hub_owner, "No permission to update verification status"
    
    # Ensure the profile owner is one of the parties involved
    is_artist: bool = self.owner == art_artist
    is_commissioner: bool = self.owner == commissioner
    assert is_artist or is_commissioner, "Profile owner not involved in this myCommission"
    
    # Check if the myCommission is verified
    is_verified_by_both: bool = staticcall art_piece.isFullyVerifiedCommission()
    
    # If verified, move from myUnverified to verified list
    if is_verified_by_both:
        # Check if it's in the myUnverified list
        found_myUnverified: bool = False
        myUnverified_index: uint256 = 0
        
        for i: uint256 in range(0, len(self.myUnverifiedCommissions), bound=1000):
            if i >= len(self.myUnverifiedCommissions):
                break
            if self.myUnverifiedCommissions[i] == _commission_art_piece:
                myUnverified_index = i
                found_myUnverified = True
                break
        
        if found_myUnverified:
            # Remove from myUnverified list
            if myUnverified_index < len(self.myUnverifiedCommissions) - 1:
                last_item: address = self.myUnverifiedCommissions[len(self.myUnverifiedCommissions) - 1]
                self.myUnverifiedCommissions[myUnverified_index] = last_item
            self.myUnverifiedCommissions.pop()
            self.myUnverifiedCommissionCount -= 1
            
            # Add to verified list if not already there
            if _commission_art_piece not in self.myCommissions:
                self.myCommissions.append(_commission_art_piece)
                self.myCommissionCount += 1
        
        # If this profile owner is the commissioner, also add to myArt if not already there
        if is_commissioner and _commission_art_piece not in self.myArt:
            self.myArt.append(_commission_art_piece)
            self.myArtCount += 1

# NOTE: For any myCommission art piece attached to a hub and fully verified, the true owner is always the hub's owner (as set by ArtCommissionHubOwners). The Profile contract should never override this; always query the hub for the current owner if needed.

@external
def getOwner() -> address:
    return self.owner
