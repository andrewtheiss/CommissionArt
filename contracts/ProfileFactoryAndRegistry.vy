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
    def initialize(_owner: address, _profile_social: address): nonpayable
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

interface ProfileSocial:
    def initialize(_owner: address, _profile: address): nonpayable

interface ArtCommissionHubOwners:
    def getCommissionHubsByOwner(_owner: address, _page: uint256, _page_size: uint256) -> DynArray[address, 100]: view
    def getCommissionHubCountByOwner(_owner: address) -> uint256: view

owner: public(address)
profileTemplate: public(address)  # Address of the profile contract template to clone
profileSocialTemplate: public(address)  # Address of the profile social contract template to clone
accountToProfile: public(HashMap[address, address])  # Maps user address to profile contract
userProfileCount: public(uint256)  # Total number of registered user profiles
latestUsers: public(DynArray[address, 1000])  # List of registered users for easy querying
artCommissionHubOwners: public(address)  # Address of the ArtCommissionHubOwners contract

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

event ArtPieceCreatedForParty:
    creator: indexed(address)
    other_party: indexed(address)
    art_piece: indexed(address)
    is_artist: bool

event ArtCommissionHubOwnersSet:
    registry: indexed(address)

@deploy
def __init__(_profile_template: address, _profile_social_template: address):
    self.owner = msg.sender
    # Verify the profile template was deployed by the same address
    template_deployer: address = staticcall Profile(_profile_template).deployer()
    assert template_deployer == msg.sender, "Profile template must be deployed by the same address"
    self.profileTemplate = _profile_template
    self.profileSocialTemplate = _profile_social_template
    self.userProfileCount = 0
    self.artCommissionHubOwners = empty(address)

# Internal function to link existing commission hubs to a profile
@internal
def _linkExistingHubs(_user: address, _profile: address):
    """
    @notice Links all commission hubs a user already owns to their newly created profile
    @dev This function handles the important edge case where:
         1. A user buys an NFT, creating a commission hub in ArtCommissionHubOwners
         2. Later, the user creates a profile
         3. We need to automatically link their existing hubs to their new profile
    
    @dev Without this function, users who owned NFTs before creating a profile would:
         - Not see their commission hubs in their profile
         - Need to manually link their hubs or wait for ownership transfers
    
    @dev This function is called internally during all profile creation flows:
         - createProfile
         - createNewArtPieceAndRegisterProfile
    
    @dev It queries the ArtCommissionHubOwners for all hubs owned by the user and adds them
         to the user's profile in batches to handle gas limits efficiently
    
    @param _user The address of the user whose hubs should be linked
    @param _profile The address of the user's newly created profile
    """
    # If owner registry is not set, skip this step
    if self.artCommissionHubOwners == empty(address):
        return
    
    registry: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
    hub_count: uint256 = staticcall registry.getCommissionHubCountByOwner(_user)
    
    # If user has no hubs, nothing to do
    if hub_count == 0:
        return
    
    # Get all hubs in batches of 100 (maximum return size)
    profile_instance: Profile = Profile(_profile)
    page: uint256 = 0
    page_size: uint256 = 100
    
    # Process all hubs in batches (max 100 pages = 10,000 hubs should be enough)
    max_pages: uint256 = (hub_count + page_size - 1) // page_size  # Ceiling division
    max_pages = min(max_pages, 100)  # Limit to 100 pages maximum
    
    for p: uint256 in range(100):  # Fixed bound as required by Vyper 0.4.1
        if p >= max_pages:
            break
            
        hubs: DynArray[address, 100] = staticcall registry.getCommissionHubsByOwner(_user, p, page_size)
        
        # Add each hub to the profile
        for i: uint256 in range(100):  # Fixed bound as required by Vyper 0.4.1
            if i >= len(hubs):
                break
            extcall profile_instance.addCommissionHub(hubs[i])

@external
def createProfile():
    assert self.accountToProfile[msg.sender] == empty(address), "Profile already exists"
    
    # Create a new profile contract for the user
    profile: address = create_minimal_proxy_to(self.profileTemplate)
    profile_instance: Profile = Profile(profile)
    
    # Create a new profile social contract for the user
    profile_social: address = create_minimal_proxy_to(self.profileSocialTemplate)
    profile_social_instance: ProfileSocial = ProfileSocial(profile_social)
    
    # Initialize the profile with the user as the owner
    extcall profile_instance.initialize(msg.sender, profile_social)
    
    # Initialize the profile social with the user and profile
    extcall profile_social_instance.initialize(msg.sender, profile)
    
    # Update our records
    # TODO - actuall save the latest 10 even if we max out
    if (self.userProfileCount < 1000):
        self.latestUsers.append(msg.sender)
    else:
        self.latestUsers.pop()
        self.latestUsers.append(msg.sender)

    self.accountToProfile[msg.sender] = profile
    self.userProfileCount += 1
    
    # Link any existing commission hubs from the ArtCommissionHubOwners
    self._linkExistingHubs(msg.sender, profile)
    
    log ProfileCreated(user=msg.sender, profile=profile, social=profile_social)

@external
def createProfileFor(_user: address) -> address:
    """
    @notice Creates a new profile for a specific user, only callable by the ArtCommissionHubOwners
    @dev This enables automatic profile creation when a user gets a commission hub
         but doesn't have a profile yet
    @param _user The address of the user to create a profile for
    @return The address of the newly created profile
    """
    # Only allow the ArtCommissionHubOwners to call this function
    assert msg.sender == self.artCommissionHubOwners, "Only ArtCommissionHubOwners can call this function"
    
    # Ensure the user doesn't already have a profile
    assert self.accountToProfile[_user] == empty(address), "Profile already exists"
    
    # Create a new profile contract for the user
    profile: address = create_minimal_proxy_to(self.profileTemplate)
    profile_instance: Profile = Profile(profile)
    
    # Create a new profile social contract for the user
    profile_social: address = create_minimal_proxy_to(self.profileSocialTemplate)
    profile_social_instance: ProfileSocial = ProfileSocial(profile_social)
    
    # Initialize the profile with the specified user as the owner
    extcall profile_instance.initialize(_user, profile_social)
    
    # Initialize the profile social with the user and profile
    extcall profile_social_instance.initialize(_user, profile)
    
    # Update our records
    if (self.userProfileCount < 1000):
        self.latestUsers.append(_user)
    else:
        self.latestUsers.pop()
        self.latestUsers.append(_user)

    self.accountToProfile[_user] = profile
    self.userProfileCount += 1
    
    # Link any existing commission hubs from the ArtCommissionHubOwners
    self._linkExistingHubs(_user, profile)
    
    log ProfileCreated(user=_user, profile=profile, social=profile_social)
    
    return profile

@view
@external
def getProfile(_user: address) -> address:
    return self.accountToProfile[_user]

@view
@external
def getProfileByOwner(_owner: address) -> address:
    """
    @notice Gets the profile contract address associated with an owner address
    @param _owner The address of the profile owner
    @return Address of the profile contract for the given owner
    """
    return self.accountToProfile[_owner]

@view
@external
def hasProfile(_user: address) -> bool:
    return self.accountToProfile[_user] != empty(address)

@external
def updateProfileTemplateContract(_new_template: address):
    assert msg.sender == self.owner, "Only owner can update template"
    assert _new_template != empty(address), "Invalid template address"
    
    log ProfileTemplateUpdated(previous_template=self.profileTemplate, new_template=_new_template)
    self.profileTemplate = _new_template

@external
def setArtCommissionHubOwners(_registry: address):
    # Allow the owner or the owner registry itself to set this relationship
    # This modification enables bidirectional connection setup from either side
    assert msg.sender == self.owner or msg.sender == _registry, "Only owner or registry can set owner registry"
    self.artCommissionHubOwners = _registry
    log ArtCommissionHubOwnersSet(registry=_registry)
    
@view
@external
def getUserProfiles(_page_size: uint256, _page_number: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    
    # Get total number of users
    total_users: uint256 = len(self.latestUsers)
    if total_users == 0:
        return result
    
    # Check if the requested page is beyond the total number of users
    if _page_size * _page_number >= total_users:
        return result
    
    # Calculate start index from the end (most recent users)
    start_idx: uint256 = total_users - 1 - (_page_number * _page_size)
    
    # Calculate how many items to return
    items_to_return: uint256 = min(_page_size, start_idx + 1)
    items_to_return = min(items_to_return, 100)  # Cap at DynArray size
    
    # Populate result array with profile addresses in reverse order
    for i: uint256 in range(100):
        if i >= items_to_return:
            break
        user_idx: uint256 = start_idx - i
        user_address: address = self.latestUsers[user_idx]
        profile_address: address = self.accountToProfile[user_address]
        result.append(profile_address)
    
    return result

@external
def createNewArtPieceAndRegisterProfile(
    _art_piece_template: address,
    _token_uri_data: Bytes[45000],
    _token_uri_data_format: String[10],
    _title: String[100],
    _description: String[200],
    _is_artist: bool,
    _other_party: address,
    _commission_hub: address,
    _ai_generated: bool,
    _linked_to_art_commission_hub_chain_id: uint256,
    _linked_to_art_commission_hub_address: address
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
    @param _commission_hub The commission hub address
    @param _ai_generated Whether the art is AI generated
    @param _linked_to_art_commission_hub_chain_id The chain ID of the ArtCommissionHub this piece is linked to
    @param _linked_to_art_commission_hub_address The address of the ArtCommissionHub this piece is linked to
        ** Note - if Address is 
    @return Tuple of (profile_address, art_piece_address)
    """
    # Check if the user already has a profile
    assert self.accountToProfile[msg.sender] == empty(address), "Profile already exists"
    
    # Create a new profile
    profile: address = create_minimal_proxy_to(self.profileTemplate)
    profile_instance: Profile = Profile(profile)
    
    # Create a new profile social contract for the user
    profile_social: address = create_minimal_proxy_to(self.profileSocialTemplate)
    profile_social_instance: ProfileSocial = ProfileSocial(profile_social)
    
    # Initialize the profile
    extcall profile_instance.initialize(msg.sender, profile_social)
    
    # Initialize the profile social with the user and profile
    extcall profile_social_instance.initialize(msg.sender, profile)
    
    # If there is no commission hub address AND we have details to create one, do so
    if empty(address) == _commission_hub:
        # Create a new commission hub
        commission_hub: address = create_minimal_proxy_to(self.commissionHubTemplate)
        commission_hub_instance: ArtCommissionHub = ArtCommissionHub(commission_hub)
        extcall commission_hub_instance.initialize(_linked_to_art_commission_hub_chain_id, _linked_to_art_commission_hub_address)


    # Submit profile recort to latest... 
    # # Update profile records
    # if (self.userProfileCount < 1000):
    #     self.latestUsers.append(msg.sender)
    # else:
    #     self.latestUsers.pop()
    #     self.latestUsers.append(msg.sender)

    self.accountToProfile[msg.sender] = profile
    self.userProfileCount += 1
    
    # Link any existing commission hubs from the ArtCommissionHubOwners
    self._linkExistingHubs(msg.sender, profile)
    
    log ProfileCreated(user=msg.sender, profile=profile, social=profile_social)
    
    # Create the art piece on the profile
    art_piece: address = extcall profile_instance.createArtPiece(
        _art_piece_template,
        _token_uri_data,
        _token_uri_data_format,
        _title,
        _description,
        _is_artist,
        _other_party,
        _ai_generated,
        _commission_hub
    )
    
    log ArtPieceCreated(profile=profile, art_piece=art_piece, user=msg.sender)
    
    # Explicitly create and return the tuple
    return (profile, art_piece)

@view
@external
def getLatestUserAtIndex(_index: uint256) -> address:
    """
    @notice Debug function to get a user address at a specific index from the latestUsers array
    @param _index The index to get the user address from
    @return The user address at the specified index
    """
    assert _index < len(self.latestUsers), "Index out of bounds"
    return self.latestUsers[_index]

@external
def createArtPieceForParty(
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
    # Check if the other party is a valid address
    assert _other_party != empty(address), "Other party address cannot be empty"
    assert _other_party != msg.sender, "Cannot create art piece for yourself"
    
    # Check if the caller has a profile, create one if not
    caller_profile: address = self.accountToProfile[msg.sender]
    if caller_profile == empty(address):
        # Create a new profile for the caller
        caller_profile = create_minimal_proxy_to(self.profileTemplate)
        caller_profile_instance: Profile = Profile(caller_profile)
        
        # Create a new profile social contract for the caller
        caller_social: address = create_minimal_proxy_to(self.profileSocialTemplate)
        caller_social_instance: ProfileSocial = ProfileSocial(caller_social)
        
        # Initialize the profile with the caller as the owner
        extcall caller_profile_instance.initialize(msg.sender, caller_social)
        
        # Initialize the profile social with the caller and profile
        extcall caller_social_instance.initialize(msg.sender, caller_profile)
        
        # Update our records
        if (self.userProfileCount < 1000):
            self.latestUsers.append(msg.sender)
        else:
            self.latestUsers.pop()
            self.latestUsers.append(msg.sender)

        self.accountToProfile[msg.sender] = caller_profile
        self.userProfileCount += 1
        
        # Link any existing commission hubs from the ArtCommissionHubOwners
        self._linkExistingHubs(msg.sender, caller_profile)
        
        log ProfileCreated(user=msg.sender, profile=caller_profile, social=caller_social)
    
    # Check if the other party has a profile, create one if not
    other_profile: address = self.accountToProfile[_other_party]
    if other_profile == empty(address):
        # Create a new profile for the other party
        other_profile = create_minimal_proxy_to(self.profileTemplate)
        other_profile_instance: Profile = Profile(other_profile)
        
        # Create a new profile social contract for the other party
        other_social: address = create_minimal_proxy_to(self.profileSocialTemplate)
        other_social_instance: ProfileSocial = ProfileSocial(other_social)
        
        # Initialize the profile with the other party as the owner
        extcall other_profile_instance.initialize(_other_party, other_social)
        
        # Initialize the profile social with the other party and profile
        extcall other_social_instance.initialize(_other_party, other_profile)
        
        # Update our records
        if (self.userProfileCount < 1000):
            self.latestUsers.append(_other_party)
        else:
            self.latestUsers.pop()
            self.latestUsers.append(_other_party)

        self.accountToProfile[_other_party] = other_profile
        self.userProfileCount += 1
        
        # Link any existing commission hubs from the ArtCommissionHubOwners
        self._linkExistingHubs(_other_party, other_profile)
        
        log ProfileCreated(user=_other_party, profile=other_profile, social=other_social)
    
    # Get the profile instances
    caller_profile_instance: Profile = Profile(caller_profile)
    other_profile_instance: Profile = Profile(other_profile)
    
    # Create the art piece on the caller's profile
    art_piece: address = extcall caller_profile_instance.createArtPiece(
        _art_piece_template,
        _token_uri_data,
        _token_uri_data_format,
        _title,
        _description,
        _is_artist,
        _other_party,
        _ai_generated,
        _commission_hub
    )
    
    log ArtPieceCreated(profile=caller_profile, art_piece=art_piece, user=msg.sender)
    log ArtPieceCreatedForParty(creator=msg.sender, other_party=_other_party, art_piece=art_piece, is_artist=_is_artist)
    
    # Check if the other party has blacklisted the caller
    if staticcall other_profile_instance.blacklist(msg.sender):
        # Just return without adding to unverified commissions
        # This silently fails to add to unverified commissions, but the art piece is still created
        return (caller_profile, other_profile, art_piece, _commission_hub)
    
    # Check if unverified commissions are allowed
    allow_unverified: bool = staticcall other_profile_instance.allowUnverifiedCommissions()
    
    # Add to the other party's commissions if allowed
    if allow_unverified:
        extcall other_profile_instance.addCommission(art_piece)
    
    return (caller_profile, other_profile, art_piece, _commission_hub)

@view
@external
def getRandomProfiles(_count: uint256, _seed: uint256) -> DynArray[address, 20]:
    """
    @notice Returns a set of random user profiles for discovery
    @dev Uses the provided seed combined with block timestamp for randomness
    @param _count The number of random profiles to return (capped at 20)
    @param _seed A seed value to influence the randomness
    @return A list of random profile addresses
    """
    result: DynArray[address, 20] = []
    
    # Early return if no profiles
    if self.userProfileCount == 0:
        return result
    
    # Get the latest users array length
    latest_users_len: uint256 = len(self.latestUsers)
    if latest_users_len == 0:
        return result
    
    # Cap the count at 20 or the total number of users, whichever is smaller
    count: uint256 = min(min(_count, latest_users_len), 20)
    
    # Use a simple pseudo-random approach
    random_seed: uint256 = block.timestamp + _seed
    
    # Track indices we've already used with a simple array search
    for i: uint256 in range(20):  # Fixed bound as required by Vyper
        if i >= count:
            break
        
        # Generate a random index
        random_index: uint256 = (random_seed + i * 17) % latest_users_len
        user_address: address = self.latestUsers[random_index]
        
        # Check if this profile is already in our result
        already_added: bool = False
        for j: uint256 in range(20):
            if j >= i:  # Only check up to our current position in the result array
                break
            if result[j] == user_address:
                already_added = True
                break
        
        # If not already added, add it and its profile
        if not already_added:
            profile_address: address = self.accountToProfile[user_address]
            if profile_address != empty(address):
                result.append(profile_address)
    
    return result

@view
@external
def getProfilesByOffset(_offset: uint256, _count: uint256) -> DynArray[address, 20]:
    """
    @notice Returns a paginated list of profiles using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _offset The starting index in the users array
    @param _count The number of profiles to return (capped at 20)
    @return A list of profile addresses
    """
    result: DynArray[address, 20] = []
    
    # Get the latest users array length
    latest_users_len: uint256 = len(self.latestUsers)
    if latest_users_len == 0 or _offset >= latest_users_len:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = latest_users_len - _offset
    count: uint256 = min(min(_count, available_items), 20)
    
    # Populate result array
    for i: uint256 in range(20):
        if i >= count:
            break
        user_address: address = self.latestUsers[_offset + i]
        profile_address: address = self.accountToProfile[user_address]
        if profile_address != empty(address):
            result.append(profile_address)
    
    return result

@view
@external
def getLatestProfiles(_count: uint256) -> DynArray[address, 20]:
    """
    @notice Returns the most recently created profiles
    @dev Returns profiles from the end of the latestUsers array (most recently added)
    @param _count The number of recent profiles to retrieve
    @return Array of recent profile addresses, up to 20
    """
    result: DynArray[address, 20] = []
    
    # Get the latest users array length
    latest_users_len: uint256 = len(self.latestUsers)
    if latest_users_len == 0:
        return result
    
    # Calculate how many items to return, capped by array size and max return size
    count: uint256 = min(min(_count, latest_users_len), 20)
    
    # Start from the end of the array (most recent)
    for i: uint256 in range(20):
        if i >= count:
            break
        
        # Get user from the end of the array (most recent first)
        idx: uint256 = latest_users_len - 1 - i
        user_address: address = self.latestUsers[idx]
        
        # Get the profile address
        profile_address: address = self.accountToProfile[user_address]
        if profile_address != empty(address):
            result.append(profile_address)
    
    return result

@view
@external
def getLatestProfilesPaginated(_page: uint256, _page_size: uint256) -> DynArray[address, 20]:
    """
    @notice Returns a paginated list of the most recently created profiles
    @dev Provides efficient pagination for frontend queries
    @param _page The page number (0-indexed)
    @param _page_size The number of profiles per page
    @return Array of profile addresses, up to 20 per page
    """
    result: DynArray[address, 20] = []
    
    # Get the latest users array length
    latest_users_len: uint256 = len(self.latestUsers)
    if latest_users_len == 0 or _page * _page_size >= latest_users_len:
        return result
    
    # Calculate start index from the end of the array
    start_idx: uint256 = latest_users_len - 1 - (_page * _page_size)
    
    # Calculate how many items to return, capped by array size and max return size
    count: uint256 = min(min(_page_size, start_idx + 1), 20)
    
    # Populate result array in reverse order (newest first)
    for i: uint256 in range(20):
        if i >= count:
            break
        
        # Check bounds to prevent underflow
        if start_idx >= i:
            idx: uint256 = start_idx - i
            user_address: address = self.latestUsers[idx]
            
            # Get the profile address
            profile_address: address = self.accountToProfile[user_address]
            if profile_address != empty(address):
                result.append(profile_address)
    
    return result

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