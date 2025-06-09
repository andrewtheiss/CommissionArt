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
deployer: public(address)
profileFactoryAndRegistry: public(address)  # Address of the hub that created this profile
owner: public(address)
profileImage: public(address)  # Changed from Bytes[45000] to address

# Commissions and counters
myCommissions: public(DynArray[address, MAX_ITEMS])
myCommissionCount: public(uint256)
myUnverifiedCommissions: public(DynArray[address, MAX_ITEMS])
myUnverifiedCommissionCount: public(uint256)
allowUnverifiedCommissions: public(bool)

# Wtf is going on with this hideous variable name?  
# We can actually absolutely SLAUGHTER 2 birds with one stone here!  
# We NEED to know if a commission exists, and we NEED to know the position of the commission
#   in the list.  So we can remove it.  So we can do both with one variable.
#   We're going to use the offset by one so that the 0 index can be used to check if the commission
#   exists.  This is a hack, but it works.  And saves considerable gas.
myCommissionExistsAndPositionOffsetByOne: public(HashMap[address, uint256])
myUnverifiedCommissionsExistsAndPositionOffsetByOne : public(HashMap[address, uint256])

# Add myCommissionRole mapping to track role at time of myCommission upload
myCommissionRole: public(HashMap[address, bool])  # true = artist, false = commissioner

# Art pieces collection
myArt: public(DynArray[address, MAX_ITEMS])
myArtCount: public(uint256)
myArtExistsAndPositionOffsetByOne: public(HashMap[address, uint256])

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
    def owner() -> address: view
    def artSales1155Template() -> address: view

# Interface for Profile (for cross-profile calls)
interface Profile:
    def updateCommissionVerificationStatus(_commission_art_piece: address): nonpayable
    def owner() -> address: view
    def linkArtPieceAsMyCommission(_art_piece: address) -> bool: nonpayable

# Interface for ArtPiece contract - updated with new verification methods
interface ArtPiece:
    def getOwner() -> address: view
    def getArtist() -> address: view
    def getCommissioner() -> address: view
    def getArtCommissionHubAddress() -> address: view
    def initialize(_token_uri_data: Bytes[45000], _token_uri_data_format: String[10], _title_input: String[100], _description_input: String[200], _commissioner_input: address, _artist_input: address, _commission_hub: address, _ai_generated: bool, _original_uploader: address, _profile_factory_address: address): nonpayable
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
    def createEditionFromArtPiece(_art_piece: address, _edition_name: String[100], _edition_symbol: String[10], _base_uri: String[256], _mint_price: uint256, _max_supply: uint256, _royalty_percent: uint256) -> address: nonpayable
    def hasEditions(_art_piece: address) -> bool: view
    def initialize(_profile_address: address, _owner: address, _profile_factory_and_registry: address): nonpayable

# Add this interface at the top
interface ArtCommissionHubOwners:
    def getCommissionHubCountByOwner(_owner: address) -> uint256: view
    def getCommissionHubsByOwnerWithOffset(_owner: address, _offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]: view
    def artCommissionHubsByOwnerIndexOffsetByOne(_owner: address, _hub: address) -> uint256: view


# Event for myCommission verification in profile context
event CommissionVerifiedInProfile:
    profile: indexed(address)
    art_piece: indexed(address)
    is_artist: bool

# Constructor
@deploy
def __init__():
    pass

# Initialization Function
@external
def initialize(_owner: address, _profile_social: address, _profile_factory_and_registry: address, _is_artist: bool = False):
    assert self.owner == empty(address), "Already initialized"
    assert _profile_factory_and_registry == msg.sender, "Profile factory and registry address cannot be empty"
    assert _profile_social != empty(address), "Profile social address cannot be empty"

    self.profileFactoryAndRegistry = _profile_factory_and_registry  # Set the hub to be the contract that called initialize
    self.deployer = msg.sender
    self.owner = _owner
    self.isArtist = _is_artist 
    self.profileSocial = _profile_social
    self.allowUnverifiedCommissions = True  # Default to allowing myCommissions
    
    # Initialize counters
    self.myCommissionCount = 0
    self.myUnverifiedCommissionCount = 0
    self.myArtCount = 0
    
    # If this is an artist profile, ensure ArtSales1155 exists
    if _is_artist:
        self._assuresArtSalesExists()

# Internal function to get deployer address
@internal
@view
def _getDeployer() -> address:
    profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
    return staticcall profile_factory.owner()

# Internal function to ensure ArtSales1155 exists for artists
@internal
def _assuresArtSalesExists():
    """
    @notice Ensures that an ArtSales1155 contract exists for this profile if it's an artist
    @dev Automatically creates ArtSales1155 if the profile is an artist and doesn't have one
    """
    if self.isArtist and self.artSales1155 == empty(address):
        # Get the ArtSales1155 template from ProfileFactoryAndRegistry
        profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
        art_sales_template: address = staticcall profile_factory.artSales1155Template()
        assert art_sales_template != empty(address), "ArtSales1155 template not set in factory"
        
        # Create ArtSales1155 contract using minimal proxy
        art_sales_contract: address = create_minimal_proxy_to(art_sales_template, revert_on_failure=True)
        
        # Initialize the ArtSales1155 contract
        art_sales: ArtSales1155 = ArtSales1155(art_sales_contract)
        extcall art_sales.initialize(self, self.owner, self.profileFactoryAndRegistry)
        
        # Set the artSales1155 address
        self.artSales1155 = art_sales_contract

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
    # Remove from whitelist when adding to blacklist
    self.whitelist[_address] = False

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
# Links a art piece to this profile, always to the myUnverified list until both parties verify it
# Use case:
# - If the profile is an artist, this is a piece of work they draw/paint/etc for someone else (they are the artist).
# - If the profile is a non-artist (commissioner/curator), this is a piece of work they commissioned from an artist (they are the client).
# - The contract records the user's role at the time of upload in myCommissionRole.
# Linked pieces have the following preconditions:
# - The piece must not be a private/non-commission piece (commissioner == artist)
# - The piece must be owned by the profile owner, profile factory, artist ,or artist/commissioner profile
# - The piece must be a commission (commissioner != artist)
# - The piece cannot be on the blacklist
# - The piece CAN bypass permissions if on the whitelist
#
@external
def linkArtPieceAsMyCommission(_art_piece: address) -> bool:
    """
    @notice Adds an ArtPiece to this profile, to myCommissions or myUnverified list based on verification status
    @dev Access control - Allowed callers:
         1. Profile owner (direct)
         2. ProfileFactoryAndRegistry (system)
         3. The art piece itself (during verification)
         4. A valid profile contract representing artist/commissioner
    @param _art_piece The address of the myCommission art piece
    """
    # Get the art piece details to check permissions
    art_piece: ArtPiece = ArtPiece(_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    is_potential_commission: bool = commissioner != art_artist
    
    # Define clear permission categories
    is_profile_owner: bool = msg.sender == self.owner
    is_system: bool = msg.sender == self.profileFactoryAndRegistry
    is_art_piece_self: bool = msg.sender == _art_piece
    
    # Check if caller is a valid profile representing one of the parties
    is_valid_profile_caller: bool = False
    if msg.sender != self.owner and msg.sender != self.profileFactoryAndRegistry and msg.sender != _art_piece:
        # Only check profile validity for non-system/non-art-piece callers
        # Verify this is a valid profile contract from our factory
        profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
        artist_profile: address = staticcall profile_factory.getProfile(art_artist)
        commissioner_profile: address = staticcall profile_factory.getProfile(commissioner)
        
        # Allow calls from the official profiles of the artist or commissioner
        is_valid_profile_caller = (msg.sender == artist_profile or msg.sender == commissioner_profile)
    
    # Require at least one valid permission
    assert is_profile_owner or is_system or is_art_piece_self or is_valid_profile_caller, "No permission to add commission"

    if self.myCommissionExistsAndPositionOffsetByOne[_art_piece] != 0:
        log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Commission already added")
        return False

    if not is_potential_commission:
        log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Not a commission art piece")
        return False
    
    # If artist/commissioner are blacklisted by THIS profile, reject the commission
    if (self.blacklist[commissioner] or self.blacklist[art_artist]):
        log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Artist or commissioner is on blacklist")
        return False

    # For profile callers (not owner/system/art piece), require whitelisting
    if is_valid_profile_caller and not (self.whitelist[commissioner] or self.whitelist[art_artist]):
        log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Artist or commissioner is not whitelisted")
        return False
    
    # Add to myArt collection if the profile owner is the commissioner
    if self.owner == commissioner and self.myArtExistsAndPositionOffsetByOne[_art_piece] == 0:
        self.myArt.append(_art_piece)
        self.myArtCount += 1
        self.myArtExistsAndPositionOffsetByOne[_art_piece] = self.myArtCount
    
    # Determine if this should be added to verified or myUnverified list
    # Commissions are now verified only when both parties verify them
    is_verified_by_both: bool = False
    if is_potential_commission:
        is_verified_by_both = staticcall art_piece.isFullyVerifiedCommission()
    
    # Check if we should add to verified list due to whitelisting
    should_add_to_verified: bool = is_verified_by_both
    if is_potential_commission and not is_verified_by_both:
        # If the artist or commissioner is whitelisted by this profile, add to verified list
        if self.whitelist[commissioner] or self.whitelist[art_artist]:
            should_add_to_verified = True
    
    # Add to verified list
    if should_add_to_verified:
        self._addToVerifiedList(_art_piece)

    # Add to myUnverified list
    else:
        if not self.allowUnverifiedCommissions:
            log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Unverified commissions are disallowed by this Profile.")
            return False
        if self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] != 0:
            log CommissionFailedToLink(profile=self, art_piece=_art_piece, reason="Commission already added, but unverified.  Please verify.")
            return False
        self._addToUnverifiedList(_art_piece)

    return True

@internal
def _addToUnverifiedList(_art_piece: address):
    art_piece: ArtPiece = ArtPiece(_art_piece)
    self.myUnverifiedCommissions.append(_art_piece)
    self.myUnverifiedCommissionCount += 1
    self.myCommissionRole[_art_piece] = (self.owner == staticcall art_piece.getArtist())
    self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] = self.myUnverifiedCommissionCount
    log UnverifiedCommissionLinked(profile=self, art_piece=_art_piece)

@internal
def _addToVerifiedList(_art_piece: address):
    art_piece: ArtPiece = ArtPiece(_art_piece)
    self.myCommissions.append(_art_piece)
    self.myCommissionCount += 1
    self.myCommissionRole[_art_piece] = (self.owner == staticcall art_piece.getArtist())
    self.myCommissionExistsAndPositionOffsetByOne[_art_piece] = self.myCommissionCount
    log CommissionLinked(profile=self, art_piece=_art_piece, is_artist=self.isArtist)

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
    assert self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] != 0, "Unverified myCommission not found"
    
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
    
    # Check if now fully verified - this will move from myUnverified to verified
    is_now_verified: bool = staticcall art_piece.isFullyVerifiedCommission()
    
    # If now verified, move from myUnverified to verified list
    if is_now_verified:
        # Add to myArt collection if the profile owner is the commissioner and not already there
        if is_commissioner and self.myArtExistsAndPositionOffsetByOne[_art_piece] == 0:
            self.myArt.append(_art_piece)
            self.myArtCount += 1
            self.myArtExistsAndPositionOffsetByOne[_art_piece] = self.myArtCount
        
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
            # Remove from myUnverified list and update mappings
            if myUnverified_index < len(self.myUnverifiedCommissions) - 1:
                last_item: address = self.myUnverifiedCommissions[len(self.myUnverifiedCommissions) - 1]
                self.myUnverifiedCommissions[myUnverified_index] = last_item
                # Update mapping for the moved item
                self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[last_item] = myUnverified_index + 1  # offset by 1
            self.myUnverifiedCommissions.pop()
            self.myUnverifiedCommissionCount -= 1
            # Clear mapping for the removed item
            self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] = 0
        
        # Add to verified list if not already there
        if self.myCommissionExistsAndPositionOffsetByOne[_art_piece] == 0:
            self.myCommissions.append(_art_piece)
            self.myCommissionCount += 1
            # Set mapping for the newly added verified item
            self.myCommissionExistsAndPositionOffsetByOne[_art_piece] = self.myCommissionCount  # offset by 1
            # Set the role based on whether profile owner is artist or commissioner
            self.myCommissionRole[_art_piece] = is_artist
        
        # Now we need to update the other party's profile as well
        # Get the profile factory registry to find the other party's profile
        if self.profileFactoryAndRegistry != empty(address) and found_myUnverified:
            # Only update the other profile if we actually moved something from unverified to verified
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
# Removes a commission from this profile's verified or unverified commissions list
# Use case:
# - If a commission is no longer relevant, or was added in error, it can be removed.
# - This also removes the recorded role for that commission.
# - If you remove a commission from your myCommissions list, it will REMOVE itself ONLY from unverified ArtCommissionHubs
#
@external
def removeArtLinkToMyCommission(_my_commission: address):
    """
    @notice Removes a commission from this profile's verified or unverified commissions list
    @dev Access control - Allowed callers:
         1. Profile owner (can remove any commission from their profile)
         2. ProfileFactoryAndRegistry (system operations)
         3. The art piece itself (during verification)
         4. Valid profile contracts representing artist/commissioner (with restrictions)
    @param _my_commission The address of the commission to remove
    """

    # Check that the commission exists in this profile
    assert self.myCommissionExistsAndPositionOffsetByOne[_my_commission] != 0 or self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_my_commission] != 0, "No commission to unlink"
    
    # Get art piece details
    art_piece: ArtPiece = ArtPiece(_my_commission)
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    
    # Define clear permission categories
    is_profile_owner: bool = msg.sender == self.owner
    is_system: bool = msg.sender == self.profileFactoryAndRegistry
    is_art_piece_self: bool = msg.sender == _my_commission
    
    # Check if caller is a valid profile representing one of the parties
    is_valid_profile_caller: bool = False
    if msg.sender != self.owner and msg.sender != self.profileFactoryAndRegistry and msg.sender != _my_commission:
        # Verify this is a valid profile contract from our factory
        profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
        artist_profile: address = staticcall profile_factory.getProfile(art_artist)
        commissioner_profile: address = staticcall profile_factory.getProfile(commissioner)
        
        # Allow calls from the official profiles of the artist or commissioner
        is_valid_profile_caller = (msg.sender == artist_profile or msg.sender == commissioner_profile)
    
    # Require at least one valid permission
    assert is_profile_owner or is_system or is_art_piece_self or is_valid_profile_caller, "No permission to remove commission"
    
    # Remove from correct list
    if (self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_my_commission] != 0):
        last_item: address = self.myUnverifiedCommissions[len(self.myUnverifiedCommissions) - 1]
        self.myUnverifiedCommissions[self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_my_commission] - 1] = last_item #offset by 1 so indices are 0 when absent
        # Update mapping for the moved item
        if len(self.myUnverifiedCommissions) > 1:  # Only update if we're actually moving an item
            self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[last_item] = self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_my_commission]
        self.myUnverifiedCommissions.pop()
        self.myUnverifiedCommissionCount -= 1
        self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_my_commission] = 0

    elif (self.myCommissionExistsAndPositionOffsetByOne[_my_commission] != 0):
        last_item: address = self.myCommissions[len(self.myCommissions) - 1]
        self.myCommissions[self.myCommissionExistsAndPositionOffsetByOne[_my_commission] - 1] = last_item #offset by 1 so indices are 0 when absent
        # Update mapping for the moved item
        if len(self.myCommissions) > 1:  # Only update if we're actually moving an item
            self.myCommissionExistsAndPositionOffsetByOne[last_item] = self.myCommissionExistsAndPositionOffsetByOne[_my_commission]
        self.myCommissions.pop()
        self.myCommissionCount -= 1
        self.myCommissionExistsAndPositionOffsetByOne[_my_commission] = 0


## get Commissions
#
# getCommissionsByOffset
# -------------------------
# Returns a paginated list of myUnverified myCommissions for this profile.
# Use case:
# - Used by the frontend to display all myUnverified myCommissions associated with this profile.
# Example:
# - Alice wants to see all her myUnverified myCommissions: getUnverifiedCommissions(page, pageSize).
#
@view
@external
def getCommissionsByOffset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of commissions using offset-based pagination.
    @dev Forward pagination: _offset is starting index, _count is number of items
         Reverse pagination: _offset is number of items to skip from end, _count is number of items
    @param _offset For forward: starting index. For reverse: items to skip from end
    @param _count Number of items to return (capped at 50)
    @param reverse Direction: False = forward (oldest first), True = reverse (newest first)
    @return A list of up to 50 commission addresses
    """
    result: DynArray[address, 50] = []
    array_length: uint256 = self.myCommissionCount
    
    # Handle empty array
    if array_length == 0:
        return result
    
    if not reverse:
        # FORWARD PAGINATION: _offset is starting index
        if _offset >= array_length:
            return result  # Offset beyond array bounds
        
        available_items: uint256 = array_length - _offset
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            result.append(self.myCommissions[_offset + i])
    else:
        # REVERSE PAGINATION: _offset is items to skip from end
        if _offset >= array_length:
            return result  # Skip more items than exist
            
        # Calculate starting index (skip _offset items from the end)
        start_index: uint256 = array_length - 1 - _offset
        available_items: uint256 = start_index + 1  # Items available going backwards
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            index: uint256 = start_index - i
            result.append(self.myCommissions[index])
    
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
def getUnverifiedCommissionsByOffset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of unverified commissions using offset-based pagination.
    @dev Forward pagination: _offset is starting index, _count is number of items
         Reverse pagination: _offset is number of items to skip from end, _count is number of items
    @param _offset For forward: starting index. For reverse: items to skip from end
    @param _count Number of items to return (capped at 50)
    @param reverse Direction: False = forward (oldest first), True = reverse (newest first)
    @return A list of up to 50 unverified commission addresses
    """
    result: DynArray[address, 50] = []
    array_length: uint256 = self.myUnverifiedCommissionCount
    
    # Handle empty array
    if array_length == 0:
        return result
    
    if not reverse:
        # FORWARD PAGINATION: _offset is starting index
        if _offset >= array_length:
            return result  # Offset beyond array bounds
        
        available_items: uint256 = array_length - _offset
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            result.append(self.myUnverifiedCommissions[_offset + i])
    else:
        # REVERSE PAGINATION: _offset is items to skip from end
        if _offset >= array_length:
            return result  # Skip more items than exist
            
        # Calculate starting index (skip _offset items from the end)
        start_index: uint256 = array_length - 1 - _offset
        available_items: uint256 = start_index + 1  # Items available going backwards
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            index: uint256 = start_index - i
            result.append(self.myUnverifiedCommissions[index])
    
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
    _is_profile_art: bool = False,
    _off_chain_data: String[2500] = empty(String[2500])
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
        assert msg.sender == self.owner or indirect_creation_call, "Only profile owner or system can create personal art piece"
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
    art_piece_address: address = create_minimal_proxy_to(_art_piece_template, revert_on_failure=True)
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
        self.owner,  # _original_uploader
        self.profileFactoryAndRegistry
    )
        
    # If profile art, set as profile image
    if _is_profile_art:
        self.profileImage = art_piece_address

    # Add to my art collection (check for duplicates first)
    if self.myArtExistsAndPositionOffsetByOne[art_piece_address] == 0:
        self.myArt.append(art_piece_address)
        self.myArtCount += 1
        self.myArtExistsAndPositionOffsetByOne[art_piece_address] = self.myArtCount

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
        
        # Only try to link if the other party has a profile
        linked_other_profile: bool = False
        if other_profile_address != empty(address):
            other_profile_instance: Profile = Profile(other_profile_address)
            linked_other_profile = extcall other_profile_instance.linkArtPieceAsMyCommission(art_piece_address)
                
        # Flag as verified by this account as its the uploader
        # If the other party is set, check if they are whitelisted... if so, verify by both
        # Check if already fully verified (could happen in some edge cases)
        is_verified_by_both: bool = staticcall art_piece.isFullyVerifiedCommission()
        if is_verified_by_both:
            # Add to verified myCommissions
            self.myCommissions.append(art_piece_address)
            self.myCommissionCount += 1
            # Update mapping for position tracking
            self.myCommissionExistsAndPositionOffsetByOne[art_piece_address] = self.myCommissionCount
            
            # If both parties are whitelisted, we can have an already-verified piece
            if art_commission_hub != empty(address):
                _art_commission_hub_link: ArtCommissionHub = ArtCommissionHub(art_commission_hub)
                extcall _art_commission_hub_link.submitCommission(art_piece_address)
        else:
            # Add to myUnverified myCommissions
            self.myUnverifiedCommissions.append(art_piece_address)
            self.myUnverifiedCommissionCount += 1
            # Update mapping for position tracking
            self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[art_piece_address] = self.myUnverifiedCommissionCount

    # Always return the originally created art piece address
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
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    is_commission: bool = commissioner != art_artist  # Check if it's a commission piece
    
    # Verify the profile owner is either the art piece owner or artist
    assert self.owner == art_artist or self.owner == commissioner, "Can only add art you own or created"
    
    # First, add to myArt if not already there
    if self.myArtExistsAndPositionOffsetByOne[_art_piece] == 0:
        self.myArt.append(_art_piece)
        self.myArtCount += 1
        self.myArtExistsAndPositionOffsetByOne[_art_piece] = self.myArtCount
    
    # If this is a myCommission, determine where to add it
    if is_commission:
        is_verified_by_both: bool = staticcall art_piece.isFullyVerifiedCommission()
        
        if is_verified_by_both:
            # Add to verified myCommissions if not already there
            if self.myCommissionExistsAndPositionOffsetByOne[_art_piece] == 0:
                self.myCommissions.append(_art_piece)
                self.myCommissionCount += 1
                self.myCommissionExistsAndPositionOffsetByOne[_art_piece] = self.myCommissionCount
                # Record the role (owner=commissioner, artist=artist)
                self.myCommissionRole[_art_piece] = (self.owner == art_artist)
        else:
            # Add to myUnverified myCommissions if not already there
            if self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] == 0:
                self.myUnverifiedCommissions.append(_art_piece)
                self.myUnverifiedCommissionCount += 1
                self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] = self.myUnverifiedCommissionCount
                # Record the role (owner=commissioner, artist=artist)
                self.myCommissionRole[_art_piece] = (self.owner == art_artist)

@external
def removeArtPiece(_art_piece: address):
    assert msg.sender == self.owner, "Only owner can remove art piece"
    
    # Check if art piece exists using the mapping
    assert self.myArtExistsAndPositionOffsetByOne[_art_piece] != 0, "Art piece not found"
    
    # Get the position (subtract 1 for actual index)
    index: uint256 = self.myArtExistsAndPositionOffsetByOne[_art_piece] - 1
    
    # Swap with the last element and pop
    if index < len(self.myArt) - 1:  # Not the last element
        # Get the last item
        last_item: address = self.myArt[len(self.myArt) - 1]
        # Replace the item to remove with the last item
        self.myArt[index] = last_item
        # Update mapping for the moved item
        self.myArtExistsAndPositionOffsetByOne[last_item] = index + 1  # offset by 1
    
    # Pop the last item (now a duplicate if we did the swap)
    self.myArt.pop()
    self.myArtCount -= 1
    # Clear mapping for the removed item
    self.myArtExistsAndPositionOffsetByOne[_art_piece] = 0
    
    # Also check if it's in myCommissions or myUnverified myCommissions and remove if found
    # This is optional - the user can use removeCommission for more explicit control
    
    # Check verified myCommissions using mapping
    if self.myCommissionExistsAndPositionOffsetByOne[_art_piece] != 0:
        # Remove from verified list
        commission_index: uint256 = self.myCommissionExistsAndPositionOffsetByOne[_art_piece] - 1
        if commission_index < len(self.myCommissions) - 1:
            last_item: address = self.myCommissions[len(self.myCommissions) - 1]
            self.myCommissions[commission_index] = last_item
            # Update mapping for the moved item
            self.myCommissionExistsAndPositionOffsetByOne[last_item] = commission_index + 1  # offset by 1
        self.myCommissions.pop()
        self.myCommissionCount -= 1
        # Clear role data and mapping for removed item
        self.myCommissionRole[_art_piece] = False
        self.myCommissionExistsAndPositionOffsetByOne[_art_piece] = 0
    
    # Check myUnverified myCommissions using mapping
    if self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] != 0:
        # Remove from myUnverified list
        unverified_index: uint256 = self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] - 1
        if unverified_index < len(self.myUnverifiedCommissions) - 1:
            last_item: address = self.myUnverifiedCommissions[len(self.myUnverifiedCommissions) - 1]
            self.myUnverifiedCommissions[unverified_index] = last_item
            # Update mapping for the moved item
            self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[last_item] = unverified_index + 1  # offset by 1
        self.myUnverifiedCommissions.pop()
        self.myUnverifiedCommissionCount -= 1
        # Clear role data and mapping for removed item
        self.myCommissionRole[_art_piece] = False
        self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_art_piece] = 0

## Get Art Pieces
#
# getArtPiecesByOffset
# -------------------------
# Returns a paginated list of myArt for this profile.
# Use case:
# - Used by the frontend to display all myArt associated with this profile.
# Example:
# - Alice wants to see all her myArt: getArtPiecesByOffset(page, pageSize).
#
@view
@external
def getArtPiecesByOffset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of art pieces using offset-based pagination.
    @dev Forward pagination: _offset is starting index, _count is number of items
         Reverse pagination: _offset is number of items to skip from end, _count is number of items
    @param _offset For forward: starting index. For reverse: items to skip from end
    @param _count Number of items to return (capped at 50)
    @param reverse Direction: False = forward (oldest first), True = reverse (newest first)
    @return A list of up to 50 art piece addresses
    """
    result: DynArray[address, 50] = []
    array_length: uint256 = self.myArtCount
    
    # Handle empty array
    if array_length == 0:
        return result
    
    if not reverse:
        # FORWARD PAGINATION: _offset is starting index
        if _offset >= array_length:
            return result  # Offset beyond array bounds
        
        available_items: uint256 = array_length - _offset
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            result.append(self.myArt[_offset + i])
    else:
        # REVERSE PAGINATION: _offset is items to skip from end
        if _offset >= array_length:
            return result  # Skip more items than exist
            
        # Calculate starting index (skip _offset items from the end)
        start_index: uint256 = array_length - 1 - _offset
        available_items: uint256 = start_index + 1  # Items available going backwards
        count: uint256 = min(min(_count, available_items), 50)
        
        for i: uint256 in range(0, count, bound=50):
            index: uint256 = start_index - i
            result.append(self.myArt[index])
    
    return result

@view
@external
def getArtPieceAtIndex(_index: uint256) -> address:
    return self.myArt[_index]

@view
@external
def artPieceExists(_art_piece: address) -> bool:
    """
    @notice Check if an art piece exists in this profile's myArt collection
    @param _art_piece The address of the art piece to check
    @return True if the art piece exists, False otherwise
    """
    return self.myArtExistsAndPositionOffsetByOne[_art_piece] != 0

@view
@external
def getArtPiecePosition(_art_piece: address) -> uint256:
    """
    @notice Get the position of an art piece in the myArt array (0-indexed)
    @param _art_piece The address of the art piece
    @return The 0-indexed position in the array, or max uint256 if not found
    """
    if self.myArtExistsAndPositionOffsetByOne[_art_piece] == 0:
        return max_value(uint256)  # Return max value to indicate not found
    return self.myArtExistsAndPositionOffsetByOne[_art_piece] - 1

@external
def setIsArtist(_is_artist: bool):
    """
    Set the artist status for this profile. Only the profile owner can call this.
    Use case: Allows a user to toggle their profile between artist and non-artist.
    Example: Alice wants to become an artist: setIsArtist(True).
    """
    assert msg.sender == self.owner, "Only owner can set artist status"
    self.isArtist = _is_artist
    
    # If becoming an artist, ensure ArtSales1155 exists
    if _is_artist:
        self._assuresArtSalesExists()

@external
def updateCommissionVerificationStatus(_commission_art_piece: address):
    """
    @notice Updates the verification status of a myCommission in this profile
    @dev Access control:
         - self.owner: The owner of the profile can update verification status
         - The commissioner or artist of the art piece can update status
         - The hub owner can update status
         - Valid profile contracts representing artist/commissioner can update status
    @param _commission_art_piece The address of the myCommission art piece
    """
    # Get the art piece details
    art_piece: ArtPiece = ArtPiece(_commission_art_piece)
    effective_owner: address = staticcall art_piece.getOwner()
    art_artist: address = staticcall art_piece.getArtist()
    commissioner: address = staticcall art_piece.getCommissioner()
    is_commission: bool = commissioner != art_artist  # Check if it's a commission piece
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
    
    # Check if sender is a valid profile representing one of the parties
    is_valid_profile_caller: bool = False
    if msg.sender != self.owner and msg.sender != art_artist and msg.sender != commissioner and not is_hub_owner:
        # Verify this is a valid profile contract from our factory
        profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
        artist_profile: address = staticcall profile_factory.getProfile(art_artist)
        commissioner_profile: address = staticcall profile_factory.getProfile(commissioner)
        
        # Allow calls from the official profiles of the artist or commissioner
        is_valid_profile_caller = (msg.sender == artist_profile or msg.sender == commissioner_profile)
    
    # Verify the sender has permission to update verification status
    assert is_profile_owner or is_art_creator or is_hub_owner or is_valid_profile_caller, "No permission to update verification status"
    
    # Ensure the profile owner is one of the parties involved
    is_artist: bool = self.owner == art_artist
    is_commissioner: bool = self.owner == commissioner
    assert is_artist or is_commissioner, "Profile owner not involved in this myCommission"
    
    # Check if the myCommission is verified
    is_verified_by_both: bool = staticcall art_piece.isFullyVerifiedCommission()
    
    # If verified, move from myUnverified to verified list
    if is_verified_by_both:
        # Add to myArt collection if the profile owner is the commissioner and not already there
        if is_commissioner and self.myArtExistsAndPositionOffsetByOne[_commission_art_piece] == 0:
            self.myArt.append(_commission_art_piece)
            self.myArtCount += 1
            self.myArtExistsAndPositionOffsetByOne[_commission_art_piece] = self.myArtCount
        
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
            # Remove from myUnverified list and update mappings
            if myUnverified_index < len(self.myUnverifiedCommissions) - 1:
                last_item: address = self.myUnverifiedCommissions[len(self.myUnverifiedCommissions) - 1]
                self.myUnverifiedCommissions[myUnverified_index] = last_item
                # Update mapping for the moved item
                self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[last_item] = myUnverified_index + 1  # offset by 1
            self.myUnverifiedCommissions.pop()
            self.myUnverifiedCommissionCount -= 1
            # Clear mapping for the removed item
            self.myUnverifiedCommissionsExistsAndPositionOffsetByOne[_commission_art_piece] = 0
        
        # Add to verified list if not already there
        if self.myCommissionExistsAndPositionOffsetByOne[_commission_art_piece] == 0:
            self.myCommissions.append(_commission_art_piece)
            self.myCommissionCount += 1
            # Set mapping for the newly added verified item
            self.myCommissionExistsAndPositionOffsetByOne[_commission_art_piece] = self.myCommissionCount  # offset by 1
            # Set the role based on whether profile owner is artist or commissioner
            self.myCommissionRole[_commission_art_piece] = is_artist
        
        # Now we need to update the other party's profile as well
        # Get the profile factory registry to find the other party's profile
        if self.profileFactoryAndRegistry != empty(address) and found_myUnverified:
            # Only update the other profile if we actually moved something from unverified to verified
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
                    extcall profile_interface.updateCommissionVerificationStatus(_commission_art_piece)
    
    log CommissionVerifiedInProfile(profile=self, art_piece=_commission_art_piece, is_artist=is_artist)


# NEW: Helper to get registry
@internal
@view
def _getArtCommissionHubOwners() -> address:
    """Get the ArtCommissionHubOwners registry address"""
    if self.profileFactoryAndRegistry == empty(address):
        return empty(address)
    profile_factory: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
    return staticcall profile_factory.artCommissionHubOwners()

@view
@external
def getCommissionHubsByOffset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]:
    """Query commission hubs directly from ArtCommissionHubOwners"""
    registry_addr: address = self._getArtCommissionHubOwners()
    if registry_addr == empty(address):
        return []
    
    registry: ArtCommissionHubOwners = ArtCommissionHubOwners(registry_addr)
    return staticcall registry.getCommissionHubsByOwnerWithOffset(self.owner, _offset, _count, reverse)

@external
@view
def getCommissionHubCount() -> uint256:
    """Get count of commission hubs from the registry"""
    registry_addr: address = self._getArtCommissionHubOwners()
    if registry_addr == empty(address):
        return 0
    
    registry: ArtCommissionHubOwners = ArtCommissionHubOwners(registry_addr)
    return staticcall registry.getCommissionHubCountByOwner(self.owner)

@external
def createArtEdition(
    _art_piece: address,
    _edition_name: String[100],
    _edition_symbol: String[10],
    _base_uri: String[256],
    _mint_price: uint256,
    _max_supply: uint256,
    _royalty_percent: uint256
) -> address:
    """
    Create an ERC1155 edition from an art piece in this profile
    This is a convenience method that calls through to ArtSales1155
    """
    assert msg.sender == self.owner, "Only owner can create editions"
    assert self.artSales1155 != empty(address), "ArtSales1155 not set"
    
    # Verify the art piece belongs to this profile
    assert self.myArtExistsAndPositionOffsetByOne[_art_piece] != 0, "Art piece not in profile"
    
    # Get the art piece to verify ownership
    art_piece: ArtPiece = ArtPiece(_art_piece)
    art_artist: address = staticcall art_piece.getArtist()
    assert art_artist == self.owner, "Must be the artist of the art piece"
    
    # Call ArtSales1155 to create the edition
    sales_contract: ArtSales1155 = ArtSales1155(self.artSales1155)
    edition: address = extcall sales_contract.createEditionFromArtPiece(
        _art_piece,
        _edition_name,
        _edition_symbol,
        _base_uri,
        _mint_price,
        _max_supply,
        _royalty_percent
    )
    
    return edition

# Add view method to check if art piece has editions
@view
@external
def artPieceHasEditions(_art_piece: address) -> bool:
    """Check if an art piece has any ERC1155 editions"""
    if self.artSales1155 == empty(address):
        return False
    
    sales_contract: ArtSales1155 = ArtSales1155(self.artSales1155)
    return staticcall sales_contract.hasEditions(_art_piece)

# NOTE: For any myCommission art piece attached to a hub and fully verified, the true owner is always the hub's owner (as set by ArtCommissionHubOwners). The Profile contract should never override this; always query the hub for the current owner if needed.
