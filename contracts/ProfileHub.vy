# @version 0.4.1
# ProfileHub - Central registry for user profiles
# Maps user addresses to their profile contracts
# Allows for creation of new profiles and querying existing ones
# Keeps track of all Profiles on app

interface Profile:
    def deployer() -> address: view
    def initialize(_owner: address): nonpayable
    def createArtPiece(
        _art_piece_template: address, 
        _token_uri_data: Bytes[45000], 
        _title: String[100], 
        _description: String[200], 
        _is_artist: bool, 
        _other_party: address, 
        _commission_hub: address, 
        _ai_generated: bool
    ) -> address: nonpayable

owner: public(address)
profileTemplate: public(address)  # Address of the profile contract template to clone
accountToProfile: public(HashMap[address, address])  # Maps user address to profile contract
userCount: public(uint256)  # Number of registered users
latestUsers: public(DynArray[address, 1000])  # List of registered users for easy querying

# Events
event ProfileCreated:
    user: indexed(address)
    profile: indexed(address)

event OwnershipTransferred:
    previous_owner: indexed(address)
    new_owner: indexed(address)

event ProfileTemplateUpdated:
    previous_template: indexed(address)
    new_template: indexed(address)
    
event ArtPieceCreated:
    profile: indexed(address)
    art_piece: indexed(address)
    user: indexed(address)

@deploy
def __init__(_profile_template: address):
    self.owner = msg.sender
    # Verify the profile template was deployed by the same address
    template_deployer: address = staticcall Profile(_profile_template).deployer()
    assert template_deployer == msg.sender, "Profile template must be deployed by the same address"
    self.profileTemplate = _profile_template
    self.userCount = 0

@external
def createProfile():
    assert self.accountToProfile[msg.sender] == empty(address), "Profile already exists"
    
    # Create a new profile contract for the user
    profile: address = create_minimal_proxy_to(self.profileTemplate)
    profile_instance: Profile = Profile(profile)
    
    # Initialize the profile with the user as the owner
    extcall profile_instance.initialize(msg.sender)
    
    # Update our records
    # TODO - actuall save the latest 10 even if we max out
    if (self.userCount < 1000):
        self.latestUsers.append(msg.sender)
    else:
        self.latestUsers.pop()
        self.latestUsers.append(msg.sender)

    self.accountToProfile[msg.sender] = profile
    self.userCount += 1
    
    log ProfileCreated(user=msg.sender, profile=profile)

@view
@external
def getProfile(_user: address) -> address:
    return self.accountToProfile[_user]

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

@view
@external
def getUserProfiles( _page_size: uint256, _page_number: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    
    # Get total number of users
    total_users: uint256 = len(self.latestUsers)
    if total_users == 0:
        return result
    
    # Cap at the most recent 1000 users
    effective_users: uint256 = min(total_users, 1000)

    # Calculate start index (from end, in reverse)
    start_idx: uint256 = effective_users - (_page_number * _page_size)
    if start_idx >= effective_users:
        return result
    
    # Calculate number of items to return, capped by page size and remaining users
    items_to_return: uint256 = min(_page_size, start_idx)
    items_to_return = min(items_to_return, 100)  # Cap at DynArray size
    
    if items_to_return == 0:
        return result
    
    # Populate result array in reverse order
    for i: uint256 in range(0, items_to_return, bound=100):
        idx: uint256 = start_idx - i - 1
        result.append(self.latestUsers[idx])
    
    return result

@external
def createNewArtPieceAndRegisterProfile(
    _art_piece_template: address,
    _token_uri_data: Bytes[45000],
    _title: String[100],
    _description: String[200],
    _is_artist: bool,
    _other_party: address,
    _commission_hub: address,
    _ai_generated: bool
) -> (address, address):
    """
    @notice Creates a new profile for the caller if needed, then creates a new art piece
    @param _art_piece_template The address of the ArtPiece template
    @param _token_uri_data The tokenURI data for the art piece
    @param _title The title of the art piece
    @param _description The description of the art piece
    @param _is_artist Whether the caller is the artist
    @param _other_party The address of the other party (artist or commissioner)
    @param _commission_hub The commission hub address
    @param _ai_generated Whether the art is AI generated
    @return Tuple of (profile_address, art_piece_address)
    """
    # Check if the user already has a profile
    assert self.accountToProfile[msg.sender] == empty(address), "Profile already exists"
    
    # Create a new profile
    profile: address = create_minimal_proxy_to(self.profileTemplate)
    profile_instance: Profile = Profile(profile)
    
    # Initialize the profile
    extcall profile_instance.initialize(msg.sender)
    
    # Update profile records
    if (self.userCount < 1000):
        self.latestUsers.append(msg.sender)
    else:
        self.latestUsers.pop()
        self.latestUsers.append(msg.sender)

    self.accountToProfile[msg.sender] = profile
    self.userCount += 1
    
    log ProfileCreated(user=msg.sender, profile=profile)
    
    # Create the art piece on the profile
    art_piece: address = extcall profile_instance.createArtPiece(
        _art_piece_template,
        _token_uri_data,
        _title,
        _description,
        _is_artist,
        _other_party,
        _commission_hub,
        _ai_generated
    )
    
    log ArtPieceCreated(profile=profile, art_piece=art_piece, user=msg.sender)
    
    # Explicitly create and return the tuple
    return (profile, art_piece)

@external
def createProfileFromContract(_profile_contract: address) -> address:
    """
    @notice Creates a new profile for the caller using a provided profile contract
    @param _profile_contract The address of the profile contract to use as a template
    @return The address of the newly created profile
    """
    assert self.accountToProfile[msg.sender] == empty(address), "Profile already exists"
    
    # TODO: Add whitelisting for profile contracts that can be used with create_minimal_proxy_to
    
    # Create a new profile contract for the user
    profile: address = create_minimal_proxy_to(_profile_contract)
    profile_instance: Profile = Profile(profile)
    
    # Initialize the profile with the user as the owner
    extcall profile_instance.initialize(msg.sender)
    
    # Update our records
    # TODO - actuall save the latest 10 even if we max out
    if (self.userCount < 1000):
        self.latestUsers.append(msg.sender)
    else:
        self.latestUsers.pop()
        self.latestUsers.append(msg.sender)

    self.accountToProfile[msg.sender] = profile
    self.userCount += 1
    
    log ProfileCreated(user=msg.sender, profile=profile)
    
    return profile