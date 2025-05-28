# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# ProfileHub - Central registry for user profiles
# Maps user addresses to their profile contracts
# Allows for creation of new profiles and querying existing ones
# Keeps track of all Profiles on app

interface Profile:
    def deployer() -> address: view
    def initialize(_owner: address, _profile_social: address, _profile_factory_and_registry: address, _is_artist: bool): nonpayable
    def createArtPiece(
        _art_piece_template: address, 
        _token_uri_data: Bytes[45000], 
        _token_uri_data_format: String[10],
        _title: String[100], 
        _description: String[200], 
        _is_artist: bool, 
        _other_party: address, 
        _ai_generated: bool,
        _commission_hub: address
    ) -> address: nonpayable
    def addCommissionHub(_hub: address): nonpayable
    def blacklist(_address: address) -> bool: view
    def whitelist(_address: address) -> bool: view
    def allowUnverifiedCommissions() -> bool: view
    def addCommission(_commission: address): nonpayable
    def myCommissionCount() -> uint256: view
    def linkArtPieceAsMyCommission(_art_piece: address) -> bool: nonpayable

interface ProfileSocial:
    def initialize(_owner: address, _profile: address, _profile_factory_and_registry: address): nonpayable

interface ArtCommissionHub:
    def initializeForArtCommissionHub(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256): nonpayable
    def initializeParentCommissionHubOwnerContract(_art_commission_hub_owners: address): nonpayable

interface ArtCommissionHubOwners:
    def getCommissionHubsByOwner(_owner: address, _page: uint256, _page_size: uint256) -> DynArray[address, 100]: view
    def getCommissionHubCountByOwner(_owner: address) -> uint256: view
    def isSystemAllowed(_address: address) -> bool: view
    def getCommissionHubsByOwnerWithOffset(_owner: address, _offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]: view    
    def registerNFTOwnerFromParentChain(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256, _owner: address): nonpayable
    def createGenericCommissionHub(_owner: address) -> address: nonpayable

owner: public(address)
profileTemplate: public(address)  # Address of the profile contract template to clone
profileSocialTemplate: public(address)  # Address of the profile social contract template to clone
userAddressToProfile: public(HashMap[address, address])  # Maps user address to profile contract
userAddressToProfileSocial: public(HashMap[address, address])  # Maps user address to profile social contract
artCommissionHubOwners: public(address)  # Address of the ArtCommissionHubOwners contract
commissionHubTemplate: public(address)  # Address of the commission hub contract template to clone

# Profile variables
latestUsers: public(address[100])  # List of registered users for easy querying
allUserProfiles: public(DynArray[address,10**9])  # List of all users for easy querying
allUserProfilesCount: public(uint256)  # Total number of registered user profiles
activeUsersWithCommissionsCount: public(uint256)  # Total number of registered user profiles
activeUsersWithCommissions: public(DynArray[address,10**9])  # List of all users for easy querying
activeUsersWithCommissionsRegistry: public(HashMap[address, bool])  # Maps user address to profile contract

GENERIC_ART_COMMISSION_HUB_CONTRACT: constant(address) = 0x1000000000000000000000000000000000000001
GENERIC_ART_COMMISSION_HUB_CHAIN_ID: constant(uint256) = 1

# Events
event ProfileCreated:
    user: indexed(address)
    profile: indexed(address)
    social: indexed(address)

event OwnershipTransferred:
    previous_owner: indexed(address)
    new_owner: indexed(address)

event ProfileTemplateUpdated:
    previous_template: indexed(address)
    new_template: indexed(address)
    
event ProfileSocialTemplateUpdated:
    previous_template: indexed(address)
    new_template: indexed(address)
    
event ArtPieceCreated:
    profile: indexed(address)
    art_piece: indexed(address)
    user: indexed(address)

event ArtPieceCreatedForOtherParty:
    creator: indexed(address)
    other_party: indexed(address)
    art_piece: indexed(address)
    is_artist: bool

event ArtCommissionHubOwnersSet:
    registry: indexed(address)

event ActiveUserProfileAdded:
    user: indexed(address)

# Called once on deployment.  There's only one ProfileFactoryAndRegistry for all time!  Dayummm
@deploy
def __init__(_profile_template: address, _profile_social_template: address, _commission_hub_template: address):
    self.owner = msg.sender
    self.profileTemplate = _profile_template
    self.profileSocialTemplate = _profile_social_template
    self.allUserProfilesCount = 0
    self.artCommissionHubOwners = empty(address)
    self.commissionHubTemplate = _commission_hub_template

@internal
def _addNewUserAndProfileAndSocial(_user: address, _profile: address, _social: address):
    # Update latest users now that its an array in a rotating way
    index: uint256 = self.allUserProfilesCount % 100
    self.latestUsers[index] = _user
    self.allUserProfiles.append(_user)
    self.userAddressToProfile[_user] = _profile
    self.userAddressToProfileSocial[_user] = _social
    self.allUserProfilesCount += 1
    
# Its true, anyone can create a profile for anyone else!
# returns the profile and profile social addresses
@internal
def _createProfile(_new_profile_address: address, _is_artist: bool = False) -> (address, address):
    # Check if the caller has a profile, create one if not
    assert _new_profile_address != empty(address), "Invalid profile address"
    caller_profile: address = self.userAddressToProfile[_new_profile_address]
    caller_profile_social: address = self.userAddressToProfileSocial[_new_profile_address]
    
    caller_profile_instance: Profile = Profile(empty(address))
    caller_profile_social_instance: ProfileSocial = ProfileSocial(empty(address))

    if caller_profile == empty(address):
        # Create a new profile for the caller
        caller_profile = create_minimal_proxy_to(self.profileTemplate, revert_on_failure=True)
        caller_profile_instance = Profile(caller_profile)
        
        # Create a new profile social contract for the caller
        caller_social: address = create_minimal_proxy_to(self.profileSocialTemplate, revert_on_failure=True)
        caller_profile_social_instance = ProfileSocial(caller_social)
        
        # Initialize the profile with the caller as the owner
        extcall caller_profile_instance.initialize(_new_profile_address, caller_social, self, _is_artist)
        extcall caller_profile_social_instance.initialize(_new_profile_address, caller_profile, self)
        
        self._addNewUserAndProfileAndSocial(_new_profile_address, caller_profile, caller_social)        
        log ProfileCreated(user=_new_profile_address, profile=caller_profile, social=caller_social)
    else:
        caller_profile_instance = Profile(caller_profile)
        caller_profile_social_instance = ProfileSocial(caller_profile_social)

    return (caller_profile_instance.address, caller_profile_social_instance.address)

# Optionally on behalf of another user
@external
def createProfile(_owner: address = empty(address)):
    owner: address = _owner
    if (owner == empty(address)):
        owner = msg.sender
    self._createProfile(owner)

@external
@nonreentrant
def createNewArtPieceAndRegisterProfileAndAttachToHub(
    _art_piece_template: address,
    _token_uri_data: Bytes[45000],
    _token_uri_data_format: String[10],
    _title: String[100],
    _description: String[200],
    _is_artist: bool,
    _other_party: address,
    _commission_hub: address,
    _ai_generated: bool,
    _linked_to_art_commission_hub_chain_id: uint256,  # use generic addresses for generic entry
    _linked_to_art_commission_hub_address: address,
    _linked_to_art_commission_hub_token_id_or_generic_hub_account: uint256
) -> (address, address):
    """
    @notice Creates a new profile for the caller if needed, then creates a new art piece
    @param _art_piece_template The address of the ArtPiece template
    @param _token_uri_data The tokenURI data for the art piece
    @param _token_uri_data_format Format of the token URI data (e.g., "avif", "webp", etc.)
    @param _title The title of the art piece
    @param _description The description of the art piece
    @param _is_artist Whether the caller is the artist
    @param _other_party The address of the other party (artist or commissioner)
    @param _commission_hub The art commission hub address, or empty address if you want to create a new one
    @param _ai_generated Whether the art is AI generated
    @param _linked_to_art_commission_hub_chain_id The chain ID of the ArtCommissionHub this piece is linked to
    @param _linked_to_art_commission_hub_address The address of the ArtCommissionHub this piece is linked to
        ** Note - if Address is 
    @return Tuple of (profile_address, art_piece_address)
    @dev When creating a generic hub (not tied to an NFT), you'd use:
        _linked_to_art_commission_hub_address = GENERIC_ART_COMMISSION_HUB_CONTRACT (which is the constant address 0x1000000000000000000000000000000000000001)
        _linked_to_art_commission_hub_chain_id = 1 (or whatever chain ID is appropriate for generic hubs)
    """

    # Validation
    assert _art_piece_template != empty(address), "Invalid art piece template"
    assert self.artCommissionHubOwners != empty(address), "ArtCommissionHubOwners not set"

    # Create profile
    profile: address = empty(address)
    profile_social: address = empty(address)
    (profile, profile_social) = self._createProfile(msg.sender)
    
    # Determine which commission hub to use
    commission_hub_to_use: address = _commission_hub
    
    # If no commission hub provided AND we have details to create one
    if _commission_hub == empty(address) and _linked_to_art_commission_hub_address != empty(address):
        # Create a new commission hub
        new_hub: address = create_minimal_proxy_to(self.commissionHubTemplate, revert_on_failure=True)
        commission_hub_instance: ArtCommissionHub = ArtCommissionHub(new_hub)
        
        # CRITICAL: Initialize with parent contract first
        extcall commission_hub_instance.initializeParentCommissionHubOwnerContract(self.artCommissionHubOwners)
        
        # Determine if generic or NFT-based hub
        if _linked_to_art_commission_hub_address == GENERIC_ART_COMMISSION_HUB_CONTRACT:
            # For generic hub, use the caller's address as the account
            generic_account: uint256 = convert(msg.sender, uint256)
            
            # Initialize as generic hub
            extcall commission_hub_instance.initializeForArtCommissionHub(
                GENERIC_ART_COMMISSION_HUB_CHAIN_ID,
                GENERIC_ART_COMMISSION_HUB_CONTRACT,
                generic_account
            )
            
            # Register with ArtCommissionHubOwners for generic hub
            owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
            if staticcall owners_interface.isSystemAllowed(self):
                # If we're allowed, register directly
                extcall owners_interface.registerNFTOwnerFromParentChain(
                    GENERIC_ART_COMMISSION_HUB_CHAIN_ID,
                    GENERIC_ART_COMMISSION_HUB_CONTRACT,
                    generic_account,
                    msg.sender
                )
            else:
                # Otherwise use createGenericCommissionHub which handles registration
                new_hub = extcall owners_interface.createGenericCommissionHub(msg.sender)
                commission_hub_instance = ArtCommissionHub(new_hub)
        else:
            # Initialize as NFT-based hub
            extcall commission_hub_instance.initializeForArtCommissionHub(
                _linked_to_art_commission_hub_chain_id,
                _linked_to_art_commission_hub_address,
                _linked_to_art_commission_hub_token_id_or_generic_hub_account
            )
            
            # For NFT hubs, registration happens through L2OwnershipRelay
            # The hub will be in "pending registration" state until owner is verified
        
        commission_hub_to_use = new_hub
 
    # Create the art piece on the profile with the correct hub
    profile_instance: Profile = Profile(profile)
    art_piece: address = extcall profile_instance.createArtPiece(
        _art_piece_template,
        _token_uri_data,
        _token_uri_data_format,
        _title,
        _description,
        _is_artist,
        _other_party,
        _ai_generated,
        commission_hub_to_use  # Use the determined hub (original or new)
    )
    
    log ArtPieceCreated(profile=profile, art_piece=art_piece, user=msg.sender)
    
    # Explicitly create and return the tuple
    return (profile, art_piece)

@external
@nonreentrant
def createProfilesAndArtPieceWithBothProfilesLinked(
    _art_piece_template: address,
    _token_uri_data: Bytes[45000],
    _token_uri_data_format: String[10],
    _title: String[100],
    _description: String[200],
    _is_artist: bool,
    _other_party: address,
    _commission_hub: address,
    _ai_generated: bool
) -> (address, address, address, address):
    """
    @notice Creates a new art piece linked to another party, creating profile for them if needed
    @dev This method automatically handles profile creation for the other party if they don't have one
    @dev Based on the _is_artist parameter, it determines how to handle the relationship:
         - If caller is artist (_is_artist=True), the art goes to the other party's unverified commissions
         - If caller is commissioner (_is_artist=False), the art goes to the other party's unverified commissions
    @dev The art piece is also added to the caller's myArt collection
    
    @param _art_piece_template The address of the ArtPiece template
    @param _token_uri_data The tokenURI data for the art piece
    @param _token_uri_data_format Format of the token URI data (e.g., "avif", "webp", etc.)
    @param _title The title of the art piece
    @param _description The description of the art piece
    @param _is_artist Whether the caller is the artist
    @param _other_party The address of the other party (artist or commissioner)
    @param _commission_hub The commission hub address
    @param _ai_generated Whether the art is AI generated
    @return Tuple of (caller_profile, other_party_profile, art_piece, commission_hub)
    """
    # Validation
    assert _other_party != empty(address), "Other party address cannot be empty"
    assert _other_party != msg.sender, "Cannot create art piece for yourself"
    assert _art_piece_template != empty(address), "Invalid art piece template"
    
    
    caller_profile: address = empty(address)
    caller_profile_social: address = empty(address)
    other_profile: address = empty(address)
    other_profile_social: address = empty(address)
    (caller_profile, caller_profile_social) = self._createProfile(msg.sender)
    (other_profile, other_profile_social) = self._createProfile(_other_party)
    
    # IMPORTANT: Use the provided commission hub or empty address
    # We do NOT create commission hubs in this function since it's meant for 
    # linking both profiles immediately, and hub submission should wait for verification
    commission_hub_to_use: address = _commission_hub

    # Create the art piece on the caller's profile
    caller_profile_instance: Profile = Profile(caller_profile)
    art_piece: address = extcall caller_profile_instance.createArtPiece(
        _art_piece_template,
        _token_uri_data,
        _token_uri_data_format,
        _title,
        _description,
        _is_artist,
        _other_party,
        _ai_generated,
        commission_hub_to_use
    )
    
    log ArtPieceCreated(profile=caller_profile, art_piece=art_piece, user=msg.sender)
    log ArtPieceCreatedForOtherParty(creator=msg.sender, other_party=_other_party, art_piece=art_piece, is_artist=_is_artist)
    
    # NOTE: all these are called on the other_profile_instance which might have been recently created
    # and not have any of these set
    # Check if the other party has blacklisted the caller
    other_profile_instance: Profile = Profile(other_profile)
    is_blacklisted: bool = staticcall other_profile_instance.blacklist(msg.sender)
    
    if not is_blacklisted:
        # Check if unverified commissions are allowed
        allow_unverified: bool = staticcall other_profile_instance.allowUnverifiedCommissions()
        
        # Link to the other party's profile if allowed
        if allow_unverified:
            # FIX: Use the correct method name
            linked: bool = extcall other_profile_instance.linkArtPieceAsMyCommission(art_piece)
            # Note: We ignore the return value as it might fail for various reasons

    return (caller_profile, other_profile, art_piece, _commission_hub)

@external
def linkArtCommissionHubOwnersContract(_art_commission_hub_owners: address):
    # Allow the owner or the owner registry itself to set this relationship
    # This modification enables bidirectional connection setup from either side
    assert msg.sender == self.owner or msg.sender == _art_commission_hub_owners, "Only owner or registry can set owner registry"
    self.artCommissionHubOwners = _art_commission_hub_owners
    log ArtCommissionHubOwnersSet(registry=_art_commission_hub_owners)

@external
def updateProfileTemplateContract(_new_template: address):
    assert msg.sender == self.owner, "Only owner can update template"
    assert _new_template != empty(address), "Invalid template address"
    
    log ProfileTemplateUpdated(previous_template=self.profileTemplate, new_template=_new_template)
    self.profileTemplate = _new_template

@external
def updateProfileSocialTemplateContract(_new_template: address):
    """
    @notice Updates the profile social template contract address
    @param _new_template The address of the new profile social template contract
    """
    assert msg.sender == self.owner, "Only owner can update template"
    assert _new_template != empty(address), "Invalid template address"
    
    log ProfileSocialTemplateUpdated(previous_template=self.profileSocialTemplate, new_template=_new_template)
    self.profileSocialTemplate = _new_template

# Store active users with commissions so that spamming new accounts with
# no commissions doesn't show up on the homepage
@external 
def addActiveUserProfile(_user: address):
    # Check if user has profile
    # Check if user has commissions
    profile: address = self.userAddressToProfile[_user]
    assert profile != empty(address), "User does not have a profile"
    profile_instance: Profile = Profile(profile)
    if not staticcall profile_instance.myCommissionCount() > 0:
        return
    if not self.activeUsersWithCommissionsRegistry[_user]:
        self.activeUsersWithCommissions.append(_user)
        self.activeUsersWithCommissionsCount += 1
        self.activeUsersWithCommissionsRegistry[_user] = True
        log ActiveUserProfileAdded(user=_user)

@external
@view
def getProfile(_user: address) -> address:
    return self.userAddressToProfile[_user]

@external
@view
def getProfileSocial(_user: address) -> address:
    return self.userAddressToProfileSocial[_user]

@external
@view
def hasProfile(_user: address) -> bool:
    return self.userAddressToProfile[_user] != empty(address)

@external
@view
def getLatestUserProfiles() -> address[100]:
    user_profiles: address[100] = empty(address[100])
    
    # Cap at total number of users or array size
    count: uint256 = min(self.allUserProfilesCount, 100)
    if count == 0:
        return user_profiles
        
    # Calculate the starting index (oldest entry in the circular buffer)
    start_index: uint256 = 0

    # If we wrapped around, start at the position after the most recently added user
    if self.allUserProfilesCount > 100:
        start_index = (self.allUserProfilesCount % 100)
    
    # Copy users in chronological order (oldest to newest)
    for i: uint256 in range(100):
        if i >= count:
            break
        # Calculate current position in the circular buffer
        pos: uint256 = (start_index + i) % 100
        user_profiles[i] = self.latestUsers[pos]
    return user_profiles

@external
@view
def getActiveUserProfileAtIndex(_index: uint256) -> address:
    assert _index < self.activeUsersWithCommissionsCount, "Index out of bounds"
    return self.activeUsersWithCommissions[_index]

@external
@view
def getRandomActiveUserProfiles(_count: uint256, _seed: uint256) -> DynArray[address, 20]:
    """
    @notice Returns a set of random user profiles for discovery
    @dev Uses the provided seed combined with block timestamp for randomness
    @param _count The number of random profiles to return (capped at 20)
    @param _seed A seed value to influence the randomness
    @return A list of random profile addresses
    """
    result: DynArray[address, 20] = []
    
    # Early return if no profiles
    if self.allUserProfilesCount == 0:
        return result
    
    # Get the latest users array length
    if self.activeUsersWithCommissionsCount == 0:
        return result
    
    # Cap the count at 20 or the total number of users, whichever is smaller
    count: uint256 = min(min(_count, self.activeUsersWithCommissionsCount), 20)
    
    # Use a simple pseudo-random approach
    random_seed: uint256 = block.timestamp + _seed
    
    # Track indices we've already used with a simple array search
    for i: uint256 in range(20):  # Fixed bound as required by Vyper
        if i >= count:
            break
        
        # Generate a random index
        random_index: uint256 = (random_seed + i * 17) % self.activeUsersWithCommissionsCount
        user_address: address = self.activeUsersWithCommissions[random_index]
        
        # Check if this profile address is already in our result
        already_added: bool = False
        for j: uint256 in range(20):
            if j >= i:  # Only check up to our current position in the result array
                break
            if result[j] == self.userAddressToProfile[user_address]:
                already_added = True
                break
        
        # If not already added, add it and its profile
        if not already_added:
            profile_address: address = self.userAddressToProfile[user_address]
            if profile_address != empty(address):
                result.append(profile_address)
    
    return result


## Get Active Users
#
# getActiveUsersByOffset
# -------------------------
# Returns a paginated list of active users with commissions
# Use case:
# - Used by the frontend to display all active users.
#
@view
@external
def getActiveUsersByOffset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of active users using offset-based pagination.
    @dev Forward pagination: _offset is starting index, _count is number of items
         Reverse pagination: _offset is number of items to skip from end, _count is number of items
    @param _offset For forward: starting index. For reverse: items to skip from end
    @param _count Number of items to return (capped at 50)
    @param reverse Direction: False = forward (oldest first), True = reverse (newest first)
    @return A list of up to 50 active user addresses
    """
    result: DynArray[address, 50] = []
    array_length: uint256 = self.activeUsersWithCommissionsCount
    
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
            result.append(self.activeUsersWithCommissions[_offset + i])
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
            result.append(self.activeUsersWithCommissions[index])
    
    return result



## Get All Users By Offset
#
# getAllUsersByOffset
# -------------------------
# Returns a paginated list of all users with commissions
# Use case:
# - Used by the frontend to display all users.
# Example:
# - Alice wants to see all users: getAllUsersByOffset(page, pageSize).
#
@view
@external
def getAllUsersByOffset(_offset: uint256, _count: uint256, reverse: bool) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of all users using offset-based pagination.
    @dev Forward pagination: _offset is starting index, _count is number of items
         Reverse pagination: _offset is number of items to skip from end, _count is number of items
    @param _offset For forward: starting index. For reverse: items to skip from end
    @param _count Number of items to return (capped at 50)
    @param reverse Direction: False = forward (oldest first), True = reverse (newest first)
    @return A list of up to 50 user addresses
    """
    result: DynArray[address, 50] = []
    array_length: uint256 = self.allUserProfilesCount
    
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
            result.append(self.allUserProfiles[_offset + i])
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
            result.append(self.allUserProfiles[index])
    
    return result