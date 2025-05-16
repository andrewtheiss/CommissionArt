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

# Constants for standardized pagination and unified array capacities
PAGE_SIZE: constant(uint256) = 20
MAX_ITEMS: constant(uint256) = 10**8  # unified max length for all item lists (adjusted if needed to original limits)


# Owner of the profile (user address)
deployer: public(address)  # New variable to store the deployer's address
hub: public(address)  # Address of the hub that created this profile
owner: public(address)
profileImage: public(address)  # Changed from Bytes[45000] to address

# Commissions and counters
commissions: public(DynArray[address, MAX_ITEMS])
commissionCount: public(uint256)
unverifiedCommissions: public(DynArray[address, MAX_ITEMS])
unverifiedCommissionCount: public(uint256)
allowUnverifiedCommissions: public(bool)

# Add commissionRole mapping to track role at time of commission upload
commissionRole: public(HashMap[address, bool])  # true = artist, false = commissioner

# Commission hubs owned by this profile
commissionHubs: public(DynArray[address, 10**8])
commissionHubCount: public(uint256)

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
    def getProfileByOwner(_owner: address) -> address: view

# Interface for Profile (for cross-profile calls)
interface Profile:
    def updateCommissionVerificationStatus(_commission_art_piece: address): nonpayable

# Interface for ArtPiece contract - updated with new verification methods
interface ArtPiece:
    def getOwner() -> address: view
    def getArtist() -> address: view
    def getCommissioner() -> address: view
    def getArtCommissionHubAddress() -> address: view
    def initialize(_token_uri_data: Bytes[45000], _token_uri_data_format: String[10], _title_input: String[100], _description_input: String[200], _commissioner_input: address, _artist_input: address, _commission_hub: address, _ai_generated: bool): nonpayable
    def verifyAsArtist(): nonpayable
    def verifyAsCommissioner(): nonpayable
    def isFullyVerifiedCommission() -> bool: view # returns true if the art piece is a VERIFIED commission (commissioner != artist AND fully verified)
    def isUnverifiedCommission() -> bool: view # returns true if the art piece is an unverified commission (commissioner != artist but not fully verified)
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

# Event for commission verification in profile context
event CommissionVerifiedInProfile:
    profile: indexed(address)
    art_piece: indexed(address)
    is_artist: bool

# Constructor
@deploy
def __init__():
    self.deployer = msg.sender  # Set deployer to msg.sender during deployment

# Initialization Function
@external
def initialize(_owner: address, _profile_social: address):
    assert self.owner == empty(address), "Already initialized"
    self.owner = _owner
    self.hub = msg.sender  # Set the hub to be the contract that called initialize
    self.deployer = msg.sender  # Also set deployer to be the same as hub for backward compatibility
    self.allowUnverifiedCommissions = True  # Default to allowing commissions
    
    # Set the profileSocial link permanently
    assert _profile_social != empty(address), "Profile social address cannot be empty"
    self.profileSocial = _profile_social
    
    self.isArtist = False  # Default to non-artist
    
    # Initialize counters
    self.commissionCount = 0
    self.unverifiedCommissionCount = 0
    self.myArtCount = 0
    self.commissionHubCount = 0

# Toggle allowing new commissions
@external
def setAllowUnverifiedCommissions(_allow: bool):
    assert msg.sender == self.owner, "Only owner can set allow new commissions"
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
    
    # TODO: Consider adding logic to remove already existing commissions from blacklisted addresses
    # This would be complex and gas-intensive, so for now, we just prevent new additions

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

## Commissions - Updated to implement new verification workflow
#
# addCommission
# -------------
# Adds a commission to this profile, always to the unverified list until both parties verify it
# Use case:
# - If the profile is an artist, this is a piece of work they created for someone else (they are the artist).
# - If the profile is a non-artist (commissioner/curator), this is a piece of work they commissioned from an artist (they are the client).
# - The contract records the user's role at the time of upload in commissionRole.
#
@external
def addCommission(_commission_art_piece: address):
    """
    @notice Adds a commission to this profile, to verified or unverified list based on verification status
    @dev Access control:
         - self.owner: The owner of the profile can add commissions to their own profile
         - self.hub: The ProfileFactoryAndRegistry contract can add commissions on behalf of users
         - Any other user: Can add commissions based on whitelist/blacklist status
    @param _commission_art_piece The address of the commission art piece
    """
    # Get the art piece details to check permissions
    art_piece: ArtPiece = ArtPiece(_commission_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    is_potential_commission: bool = staticcall art_piece.isUnverifiedCommission() or staticcall art_piece.isFullyVerifiedCommission()
    
    # Check if sender is the owner of this profile
    is_profile_owner: bool = msg.sender == self.owner
    
    # Check if sender is the hub
    is_hub: bool = msg.sender == self.hub
    
    # Check if sender is the artist or commissioner of the art piece
    is_art_creator: bool = msg.sender == art_artist or msg.sender == commissioner
    
    # Verify the sender has permission to add this commission
    assert is_profile_owner or is_hub or is_art_creator, "No permission to add commission"
    
    # If blacklisted, reject the commission
    if self.blacklist[msg.sender] and not is_profile_owner:
        assert False, "Sender is blacklisted"
    
    # If the profile owner is blacklisted by either the artist or commissioner, reject the commission
    if not is_profile_owner and (self.blacklist[art_artist] or self.blacklist[commissioner]):
        assert False, "Art creator is blacklisted"
    
    # Ensure this is actually a commission
    assert is_potential_commission, "Not a commission art piece"
    
    # Determine if this should be added to verified or unverified list
    # Commissions are now verified only when both parties verify them
    is_verified: bool = False
    if is_potential_commission:
        is_verified = staticcall art_piece.isFullyVerifiedCommission()
    
    if is_verified:
        # Add to verified list
        assert _commission_art_piece not in self.commissions, "Commission already added"
        self.commissions.append(_commission_art_piece)
        self.commissionCount += 1
        # Record the role at upload time
        self.commissionRole[_commission_art_piece] = self.isArtist
    else:
        # Add to unverified list
        assert self.allowUnverifiedCommissions, "Unverified commissions are not allowed"
        assert _commission_art_piece not in self.unverifiedCommissions, "Unverified commission already added"
        self.unverifiedCommissions.append(_commission_art_piece)
        self.unverifiedCommissionCount += 1
        # Record the role at upload time
        self.commissionRole[_commission_art_piece] = self.isArtist

#
# verifyCommission
# -------------
# Verifies a commission piece. The profile owner can verify as artist or commissioner depending on their role.
# Once both parties verify, the piece is moved from unverified to verified and ownership may transfer to the hub.
#
@external
def verifyCommission(_commission_art_piece: address):
    """
    @notice Verifies a commission piece based on the profile owner's role
    @dev Only the profile owner can call this
    @param _commission_art_piece The address of the commission art piece to verify
    """
    assert msg.sender == self.owner, "Only profile owner can verify commission"
    
    # Get the art piece details
    art_piece: ArtPiece = ArtPiece(_commission_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    
    # Check if this is a potential commission (either unverified or verified)
    is_potential_commission: bool = staticcall art_piece.isUnverifiedCommission() or staticcall art_piece.isFullyVerifiedCommission()
    
    # Ensure this is actually a commission
    assert is_potential_commission, "Not a commission art piece"
    
    # Determine if the profile owner is the artist or commissioner
    is_artist: bool = self.owner == art_artist
    is_commissioner: bool = self.owner == commissioner
    
    # Ensure the profile owner is one of the parties involved
    assert is_artist or is_commissioner, "Profile owner not involved in this commission"
    
    # Check verification status
    artist_verified: bool = staticcall art_piece.artistVerified()
    commissioner_verified: bool = staticcall art_piece.commissionerVerified()
    
    # Verify based on role if not already verified
    if is_artist and not artist_verified:
        # Verify as artist
        extcall art_piece.verifyAsArtist()
    elif is_commissioner and not commissioner_verified:
        # Verify as commissioner
        extcall art_piece.verifyAsCommissioner()
    
    # Check if now fully verified - this will move from unverified to verified
    is_now_verified: bool = staticcall art_piece.isFullyVerifiedCommission()
    
    # If now verified, move from unverified to verified list
    if is_now_verified:
        # Check if it's in the unverified list
        found_unverified: bool = False
        unverified_index: uint256 = 0
        
        for i: uint256 in range(0, len(self.unverifiedCommissions), bound=1000):
            if i >= len(self.unverifiedCommissions):
                break
            if self.unverifiedCommissions[i] == _commission_art_piece:
                unverified_index = i
                found_unverified = True
                break
        
        if found_unverified:
            # Remove from unverified list
            if unverified_index < len(self.unverifiedCommissions) - 1:
                last_item: address = self.unverifiedCommissions[len(self.unverifiedCommissions) - 1]
                self.unverifiedCommissions[unverified_index] = last_item
            self.unverifiedCommissions.pop()
            self.unverifiedCommissionCount -= 1
        
        # Add to verified list if not already there
        if _commission_art_piece not in self.commissions:
            self.commissions.append(_commission_art_piece)
            self.commissionCount += 1
        
        # If this profile owner is the commissioner, also add to myArt if not already there
        if is_commissioner and _commission_art_piece not in self.myArt:
            self.myArt.append(_commission_art_piece)
            self.myArtCount += 1
        
        # Now we need to update the other party's profile as well
        # Get the profile factory registry to find the other party's profile
        if self.hub != empty(address):
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
                profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.hub)
                other_profile: address = staticcall profile_factory.getProfileByOwner(other_party)
                
                # If the other party has a profile, update their commission status
                if other_profile != empty(address):
                    # Call the updateCommissionVerificationStatus method on the other profile
                    profile_interface: Profile = Profile(other_profile)
                    extcall profile_interface.updateCommissionVerificationStatus(_commission_art_piece)
    
    log CommissionVerifiedInProfile(profile=self, art_piece=_commission_art_piece, is_artist=is_artist)

#
# removeCommission
# ----------------
# Removes a commission from this profile's verified or unverified commissions list
# Use case:
# - If a commission is no longer relevant, or was added in error, it can be removed.
# - This also removes the recorded role for that commission.
# Example:
# - Alice accidentally adds the wrong commission: removeCommission(commissionAddress).
#
@external
def removeCommission(_commission: address):
    """
    @notice Removes a commission from this profile's verified or unverified commissions list
    @dev Access control:
         - self.owner: The owner of the profile can remove their own commissions
         - self.hub: The ProfileFactoryAndRegistry contract can remove commissions on behalf of users
         - Art piece artist: Can remove unverified commissions they created
         - ArtCommissionHub owner: Can remove commissions from the hub
    @param _commission The address of the commission to remove
    """
    # Get the art piece details to check permissions
    art_piece: ArtPiece = ArtPiece(_commission)
    art_artist: address = staticcall art_piece.getArtist()
    commission_hub: address = staticcall art_piece.getArtCommissionHubAddress()
    
    # Check if sender is the owner of this profile
    is_profile_owner: bool = msg.sender == self.owner
    
    # Check if sender is the hub
    is_hub: bool = msg.sender == self.hub
    
    # Check if sender is the artist of the art piece
    is_art_artist: bool = msg.sender == art_artist
    
    # Check if sender is the owner of the commission hub
    is_commission_hub_owner: bool = False
    if commission_hub != empty(address):
        commission_hub_interface: ArtCommissionHub = ArtCommissionHub(commission_hub)
        hub_owner: address = staticcall commission_hub_interface.owner()
        is_commission_hub_owner = (hub_owner == msg.sender)
    
    # First check if the commission is in the verified list
    found_verified: bool = False
    verified_index: uint256 = 0
    
    for i: uint256 in range(0, len(self.commissions), bound=1000):
        if i >= len(self.commissions):
            break
        if self.commissions[i] == _commission:
            verified_index = i
            found_verified = True
            break
    
    # Then check if it's in the unverified list
    found_unverified: bool = False
    unverified_index: uint256 = 0
    
    for i: uint256 in range(0, len(self.unverifiedCommissions), bound=1000):
        if i >= len(self.unverifiedCommissions):
            break
        if self.unverifiedCommissions[i] == _commission:
            unverified_index = i
            found_unverified = True
            break
    
    # Verify permissions based on which list the commission is in
    if found_verified:
        # For verified commissions, only profile owner, hub, or commission hub owner can remove
        assert is_profile_owner or is_hub or is_commission_hub_owner, "No permission to remove verified commission"
        
        # Remove from verified list
        if verified_index < len(self.commissions) - 1:
            last_item: address = self.commissions[len(self.commissions) - 1]
            self.commissions[verified_index] = last_item
        self.commissions.pop()
        self.commissionCount -= 1
        
    elif found_unverified:
        # For unverified commissions, profile owner, hub, art artist, or commission hub owner can remove
        assert is_profile_owner or is_hub or is_art_artist or is_commission_hub_owner, "No permission to remove unverified commission"
        
        # Remove from unverified list
        if unverified_index < len(self.unverifiedCommissions) - 1:
            last_item: address = self.unverifiedCommissions[len(self.unverifiedCommissions) - 1]
            self.unverifiedCommissions[unverified_index] = last_item
        self.unverifiedCommissions.pop()
        self.unverifiedCommissionCount -= 1
        
    else:
        assert False, "Commission not found"
    
    # Clear role data (optional)
    self.commissionRole[_commission] = False

#
# getCommissions
# ---------------
# Returns a paginated list of commissions (verified or unverified) for this profile.
# Use case:
# - Used by the frontend to display all commissions associated with this profile, either as artist or commissioner.
# - The frontend can also query commissionRole to determine the user's role at the time of upload for each commission.
# Example:
# - Alice wants to see all her commissions (as artist or as commissioner): getCommissions(page, pageSize).
#
@view
@external
def getCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.commissions)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.commissions[start + i])
    return result

@view
@external
def getRecentCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.commissions)
    
    # Early returns for empty array or out-of-bounds page
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    
    # Calculate start index from the end and how many items to return
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    
    # Populate result array in reverse order
    for i: uint256 in range(0, items, bound=100):
        result.append(self.commissions[start - i])
    
    return result

## Unverified Commissions
#
# getUnverifiedCommissions
# -------------------------
# Returns a paginated list of unverified commissions for this profile.
# Use case:
# - Used by the frontend to display all unverified commissions associated with this profile.
# Example:
# - Alice wants to see all her unverified commissions: getUnverifiedCommissions(page, pageSize).
#
@view
@external
def getUnverifiedCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.unverifiedCommissions)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(0, items, bound=100):
        result.append(self.unverifiedCommissions[start + i])
    return result

@view
@external
def getRecentUnverifiedCommissions(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.unverifiedCommissions)
    
    # Early returns for empty array or out-of-bounds page
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    
    # Calculate start index from the end and how many items to return
    start: uint256 = arr_len - 1 - (_page * _page_size)
    items: uint256 = min(min(_page_size, start + 1), 100)
    
    # Populate result array in reverse order
    for i: uint256 in range(0, items, bound=100):
        result.append(self.unverifiedCommissions[start - i])
    
    return result

@external
def clearUnverifiedCommissions():
    assert msg.sender == self.owner, "Only owner can clear unverified commissions"
    self.unverifiedCommissions = []
    self.unverifiedCommissionCount = 0

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
# #1 - Personal Art Piece (non-commission)
# #2 - Commission Art Piece
# #3 - Profile Art Piece (special case for profile image)
@external
def createArtPiece(
    _art_piece_template: address,
    _token_uri_data: Bytes[45000],
    _token_uri_data_format: String[10],
    _title: String[100],
    _description: String[200],
    _is_artist: bool,
    _other_party: address,
    _ai_generated: bool,
    _art_commission_hub: address = empty(address),  # Register with art commission hub
    _is_profile_art: bool = False
) -> address:
    """
    @notice Create a new art piece with optional profile art and commission registration
    @dev New workflow: uploader is initial owner, commission pieces start with uploader's side verified
    @param _art_piece_template The template contract to clone for this art piece
    @param _token_uri_data The art data
    @param _token_uri_data_format Format of the art data
    @param _title Title of the art piece
    @param _description Description of the art piece
    @param _is_artist Flag indicating if the uploader is the artist (or commissioner)
    @param _other_party Address of the other party (artist if uploader is commissioner, vice versa)
    @param _ai_generated Flag indicating if the art was AI-generated
    @param _art_commission_hub Optional hub address to register commission with
    @param _is_profile_art Flag indicating if this is a profile image
    @return The address of the created art piece
    """
    # Determine permissions
    if _is_profile_art:
        assert msg.sender == self.owner, "Only profile owner can create profile art"
    if _art_commission_hub != empty(address):
        assert msg.sender == self.owner or msg.sender == self.hub, "Only profile owner can create profile art or register with commission hub"
    else:
        assert msg.sender == self.owner or msg.sender == self.hub or msg.sender == self.deployer, "Only profile owner, hub, or deployer can create art"

    # Adjust parameters for profile art
    is_artist: bool = _is_artist
    other_party: address = _other_party
    art_commission_hub: address = _art_commission_hub

    # If this art piece is your profile, flag as not commissionable
    if _is_profile_art:
        is_artist = True
        other_party = self.owner
        art_commission_hub = empty(address)

    # Calculate owner_input and artist_input
    # NEW WORKFLOW: The uploader (profile owner) is always the initial owner
    owner_input: address = self.owner
    artist_input: address = empty(address)
    
    # Set artist based on uploader's role
    if is_artist:
        artist_input = self.owner
    else:
        # If uploader is commissioner, other party is artist
        artist_input = other_party if other_party != empty(address) else self.owner

    # Create minimal proxy to the ArtPiece template
    art_piece_address: address = create_minimal_proxy_to(_art_piece_template)

    # Initialize the art piece proxy
    art_piece: ArtPiece = ArtPiece(art_piece_address)
    extcall art_piece.initialize(
        _token_uri_data,
        _token_uri_data_format,
        _title,
        _description,
        owner_input,
        artist_input,
        art_commission_hub,
        _ai_generated
    )
        
    # If profile art, set as profile image
    if _is_profile_art:
        self.profileImage = art_piece_address

    # Add to my art collection 
    self.myArt.append(art_piece_address)
    self.myArtCount += 1

    # If this is a commission, add to unverified commissions
    if is_artist != (other_party == empty(address)) and not _is_profile_art:
        # Check if already fully verified (could happen in some edge cases)
        is_verified: bool = staticcall art_piece.isFullyVerifiedCommission()
        
        if is_verified:
            # Add to verified commissions
            self.commissions.append(art_piece_address)
            self.commissionCount += 1
        else:
            # Add to unverified commissions
            self.unverifiedCommissions.append(art_piece_address)
            self.unverifiedCommissionCount += 1
            
        # Record commission role
        self.commissionRole[art_piece_address] = is_artist

    # If commission hub is provided, register with it
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
    is_commission: bool = staticcall art_piece.isFullyVerifiedCommission()
    
    # Verify the profile owner is either the art piece owner or artist
    assert self.owner == effective_owner or self.owner == art_artist, "Can only add art you own or created"
    
    # First, add to myArt if not already there
    if _art_piece not in self.myArt:
        self.myArt.append(_art_piece)
        self.myArtCount += 1
    
    # If this is a commission, determine where to add it
    if is_commission:
        is_verified: bool = staticcall art_piece.isFullyVerifiedCommission()
        
        if is_verified:
            # Add to verified commissions if not already there
            if _art_piece not in self.commissions:
                self.commissions.append(_art_piece)
                self.commissionCount += 1
                # Record the role (owner=commissioner, artist=artist)
                self.commissionRole[_art_piece] = (self.owner == art_artist)
        else:
            # Add to unverified commissions if not already there
            if _art_piece not in self.unverifiedCommissions:
                self.unverifiedCommissions.append(_art_piece)
                self.unverifiedCommissionCount += 1
                # Record the role (owner=commissioner, artist=artist)
                self.commissionRole[_art_piece] = (self.owner == art_artist)

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
    
    # Also check if it's in commissions or unverified commissions and remove if found
    # This is optional - the user can use removeCommission for more explicit control
    
    # Check verified commissions
    for i: uint256 in range(0, len(self.commissions), bound=1000):
        if i >= len(self.commissions):
            break
        if self.commissions[i] == _art_piece:
            # Remove from verified list
            if i < len(self.commissions) - 1:
                last_item: address = self.commissions[len(self.commissions) - 1]
                self.commissions[i] = last_item
            self.commissions.pop()
            self.commissionCount -= 1
            # Clear role data (optional)
            self.commissionRole[_art_piece] = False
            break
    
    # Check unverified commissions
    for i: uint256 in range(0, len(self.unverifiedCommissions), bound=1000):
        if i >= len(self.unverifiedCommissions):
            break
        if self.unverifiedCommissions[i] == _art_piece:
            # Remove from unverified list
            if i < len(self.unverifiedCommissions) - 1:
                last_item: address = self.unverifiedCommissions[len(self.unverifiedCommissions) - 1]
                self.unverifiedCommissions[i] = last_item
            self.unverifiedCommissions.pop()
            self.unverifiedCommissionCount -= 1
            # Clear role data (optional)
            self.commissionRole[_art_piece] = False
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
# Adds a commission hub to this profile.
# Use case:
# - When a user becomes the owner of an ArtCommissionHub (either via NFT ownership or generic hub creation),
#   the hub is added to their profile for tracking.
# - Only the hub or owner registry can add hubs to ensure proper ownership tracking.
# Example:
# - When Alice buys an NFT, the ArtCommissionHubOwners calls addCommissionHub to link the hub to Alice's profile.
#
@external
def addCommissionHub(_hub: address):
    # Allow the hub (ProfileFactoryAndRegistry), owner registry, or original deployer to add commission hubs
    # Check if we have an owner registry first
    registry_address: address = empty(address)
    if self.hub != empty(address):
        # Try to get the owner registry from the profile-factory-and-registry
        profile_factory_and_regsitry_interface: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.hub)
        registry_address = staticcall profile_factory_and_regsitry_interface.artCommissionHubOwners()
    
    assert msg.sender == self.hub or msg.sender == self.deployer or msg.sender == registry_address, "Only hub or registry can add commission hub"
    
    # Check if hub is already in the list
    hubs_len: uint256 = len(self.commissionHubs)
    for i: uint256 in range(10**8):  # Use a large fixed bound
        if i >= hubs_len:
            break
        if self.commissionHubs[i] == _hub:
            return  # Hub already exists, nothing to do
    
    # Add the hub to the list
    self.commissionHubs.append(_hub)
    self.commissionHubCount += 1

#
# removeCommissionHub
# -------------------
# Removes a commission hub from this profile's list.
# Use case:
# - When a user transfers ownership of an NFT, the associated hub is removed from their profile.
# - Only the hub or owner registry can remove hubs to ensure proper ownership tracking.
# Example:
# - When Alice sells her NFT to Bob, the ArtCommissionHubOwners calls removeCommissionHub to unlink the hub from Alice's profile.
#
@external
def removeCommissionHub(_hub: address):
    # Allow the hub (ProfileFactoryAndRegistry), owner registry, or original deployer to remove commission hubs
    # Check if we have an owner registry first
    registry_address: address = empty(address)
    if self.hub != empty(address):
        # Try to get the owner registry from the profile-factory-and-registry
        profile_factory_and_regsitry_interface: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.hub)
        registry_address = staticcall profile_factory_and_regsitry_interface.artCommissionHubOwners()
    
    assert msg.sender == self.hub or msg.sender == self.deployer or msg.sender == registry_address, "Only hub or registry can remove commission hub"
    
    # Find the index of the hub to remove
    index: uint256 = 0
    found: bool = False
    hubs_len: uint256 = len(self.commissionHubs)
    for i: uint256 in range(10**8):  # Use a large fixed bound
        if i >= hubs_len:
            break
        if self.commissionHubs[i] == _hub:
            index = i
            found = True
            break
    
    # If hub found, remove it using swap and pop
    if found:
        # If not the last element, swap with the last element
        if index < len(self.commissionHubs) - 1:
            last_hub: address = self.commissionHubs[len(self.commissionHubs) - 1]
            self.commissionHubs[index] = last_hub
        # Remove the last element
        self.commissionHubs.pop()
        self.commissionHubCount -= 1

#
# getCommissionHubs
# ----------------
# Returns a paginated list of commission hubs for this profile.
# Use case:
# - Used by the frontend to display all commission hubs associated with this profile.
# Example:
# - Alice wants to see all her commission hubs: getCommissionHubs(page, pageSize).
#
@view
@external
def getCommissionHubs(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.commissionHubs)
    if arr_len == 0 or _page * _page_size >= arr_len:
        return result
    start: uint256 = _page * _page_size
    items: uint256 = min(min(_page_size, arr_len - start), 100)
    for i: uint256 in range(100):  # Fixed upper bound
        if i >= items:
            break
        result.append(self.commissionHubs[start + i])
    return result

#
# getRecentCommissionHubs
# ----------------------
# Returns a paginated list of commission hubs for this profile, starting from the most recent.
# Use case:
# - Used by the frontend to display the most recent commission hubs associated with this profile.
# Example:
# - Alice wants to see her most recent commission hubs: getRecentCommissionHubs(page, pageSize).
#
@view
@external
def getRecentCommissionHubs(_page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    arr_len: uint256 = len(self.commissionHubs)
    
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
        result.append(self.commissionHubs[start - i])
    
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
    @notice Returns a batch of verified commissions with improved capacity
    @dev Allows retrieving up to 50 commissions at once for efficient frontend loading
    @param _start_idx The starting index in the commissions array
    @param _count The number of commissions to retrieve
    @return Array of commission addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no commissions or start index is out of bounds
    if self.commissionCount == 0 or _start_idx >= self.commissionCount:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.commissionCount)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.commissions[_start_idx + i])
    
    return result

@view
@external
def getBatchUnverifiedCommissions(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a batch of unverified commissions with improved capacity
    @dev Allows retrieving up to 50 unverified commissions at once for efficient frontend loading
    @param _start_idx The starting index in the unverified commissions array
    @param _count The number of unverified commissions to retrieve
    @return Array of unverified commission addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no unverified commissions or start index is out of bounds
    if self.unverifiedCommissionCount == 0 or _start_idx >= self.unverifiedCommissionCount:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.unverifiedCommissionCount)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.unverifiedCommissions[_start_idx + i])
    
    return result

@view
@external
def getBatchCommissionHubs(_start_idx: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a batch of commission hubs with improved capacity
    @dev Allows retrieving up to 50 commission hubs at once for efficient frontend loading
    @param _start_idx The starting index in the commission hubs array
    @param _count The number of commission hubs to retrieve
    @return Array of commission hub addresses, up to 50
    """
    result: DynArray[address, 50] = []
    
    # Early return if no commission hubs or start index is out of bounds
    if self.commissionHubCount == 0 or _start_idx >= self.commissionHubCount:
        return result
    
    # Calculate end index, capped by array size and max return size
    end_idx: uint256 = min(_start_idx + _count, self.commissionHubCount)
    max_items: uint256 = min(end_idx - _start_idx, 50)
    
    # Populate result array
    for i: uint256 in range(0, max_items, bound=50):
        result.append(self.commissionHubs[_start_idx + i])
    
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
    @notice Returns a paginated list of verified commissions using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the commissions array
    @param _count The number of commissions to return (capped at 50)
    @return A list of commission addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no commissions or offset is out of bounds
    if self.commissionCount == 0 or _offset >= self.commissionCount:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.commissionCount - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.commissions[_offset + i])
    
    return result

@view
@external
def getUnverifiedCommissionsByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of unverified commissions using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the unverified commissions array
    @param _count The number of unverified commissions to return (capped at 50)
    @return A list of unverified commission addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no unverified commissions or offset is out of bounds
    if self.unverifiedCommissionCount == 0 or _offset >= self.unverifiedCommissionCount:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.unverifiedCommissionCount - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.unverifiedCommissions[_offset + i])
    
    return result

@view
@external
def getCommissionHubsByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of commission hubs using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the commission hubs array
    @param _count The number of commission hubs to return (capped at 50)
    @return A list of commission hub addresses
    """
    result: DynArray[address, 50] = []
    
    # Early return if no commission hubs or offset is out of bounds
    if self.commissionHubCount == 0 or _offset >= self.commissionHubCount:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = self.commissionHubCount - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.commissionHubs[_offset + i])
    
    return result

@external
def updateCommissionVerificationStatus(_commission_art_piece: address):
    """
    @notice Updates the verification status of a commission in this profile
    @dev Access control:
         - self.owner: The owner of the profile can update verification status
         - The commissioner or artist of the art piece can update status
         - The hub owner can update status
    @param _commission_art_piece The address of the commission art piece
    """
    # Get the art piece details
    art_piece: ArtPiece = ArtPiece(_commission_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    is_commission: bool = staticcall art_piece.isFullyVerifiedCommission()
    commission_hub: address = staticcall art_piece.getArtCommissionHubAddress()
    
    # Check if sender is the owner of this profile
    is_profile_owner: bool = msg.sender == self.owner
    
    # Check if sender is the artist or commissioner of the art piece
    is_art_creator: bool = msg.sender == art_artist or msg.sender == commissioner
    
    # Check if sender is the hub owner
    is_hub_owner: bool = False
    if commission_hub != empty(address):
        commission_hub_interface: ArtCommissionHub = ArtCommissionHub(commission_hub)
        hub_owner: address = staticcall commission_hub_interface.owner()
        is_hub_owner = (hub_owner == msg.sender)
    
    # Verify the sender has permission to update verification status
    assert is_profile_owner or is_art_creator or is_hub_owner, "No permission to update verification status"
    
    # Ensure the profile owner is one of the parties involved
    is_artist: bool = self.owner == art_artist
    is_commissioner: bool = self.owner == commissioner
    assert is_artist or is_commissioner, "Profile owner not involved in this commission"
    
    # Check if the commission is verified
    is_verified: bool = staticcall art_piece.isFullyVerifiedCommission()
    
    # If verified, move from unverified to verified list
    if is_verified:
        # Check if it's in the unverified list
        found_unverified: bool = False
        unverified_index: uint256 = 0
        
        for i: uint256 in range(0, len(self.unverifiedCommissions), bound=1000):
            if i >= len(self.unverifiedCommissions):
                break
            if self.unverifiedCommissions[i] == _commission_art_piece:
                unverified_index = i
                found_unverified = True
                break
        
        if found_unverified:
            # Remove from unverified list
            if unverified_index < len(self.unverifiedCommissions) - 1:
                last_item: address = self.unverifiedCommissions[len(self.unverifiedCommissions) - 1]
                self.unverifiedCommissions[unverified_index] = last_item
            self.unverifiedCommissions.pop()
            self.unverifiedCommissionCount -= 1
            
            # Add to verified list if not already there
            if _commission_art_piece not in self.commissions:
                self.commissions.append(_commission_art_piece)
                self.commissionCount += 1
        
        # If this profile owner is the commissioner, also add to myArt if not already there
        if is_commissioner and _commission_art_piece not in self.myArt:
            self.myArt.append(_commission_art_piece)
            self.myArtCount += 1

# NOTE: For any commission art piece attached to a hub and fully verified, the true owner is always the hub's owner (as set by ArtCommissionHubOwners). The Profile contract should never override this; always query the hub for the current owner if needed.
