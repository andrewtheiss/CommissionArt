# @version 0.4.1
# ProfileHub - Central registry for user profiles
# Maps user addresses to their profile contracts
# Allows for creation of new profiles and querying existing ones

interface Profile:
    def initialize(_owner: address): nonpayable

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

@deploy
def __init__(_profile_template: address):
    self.owner = msg.sender
    self.profileTemplate = _profile_template
    self.userCount = 0

@external
def createProfile():
    """
    Create a new profile for a user
    """
    assert self.accountToProfile[msg.sender] == empty(address), "Profile already exists"
    
    # Create a new profile contract for the user
    profile: address = create_minimal_proxy_to(self.profileTemplate)
    profile_instance: Profile = Profile(profile)
    
    # Initialize the profile with the user as the owner
    extcall profile_instance.initialize(msg.sender)
    
    # Update our records
    self.accountToProfile[msg.sender] = profile
    self.userCount += 1
    
    # Add to the list of users
    if len(self.latestUsers) < 1000:
        self.latestUsers.append(msg.sender)
    
    log ProfileCreated(user=msg.sender, profile=profile)

@view
@external
def getProfile(_user: address) -> address:
    """
    Get a user's profile contract address
    """
    return self.accountToProfile[_user]

@view
@external
def hasProfile(_user: address) -> bool:
    """
    Check if a user has a profile
    """
    return self.accountToProfile[_user] != empty(address)

@external
def transferOwnership(_new_owner: address):
    """
    Transfer ownership of the ProfileHub contract
    """
    assert msg.sender == self.owner, "Only owner can transfer ownership"
    assert _new_owner != empty(address), "Invalid new owner address"
    
    log OwnershipTransferred(previous_owner=self.owner, new_owner=_new_owner)
    self.owner = _new_owner

@external
def updateProfileTemplate(_new_template: address):
    """
    Update the profile template contract
    Only for future profiles, existing ones are not affected
    """
    assert msg.sender == self.owner, "Only owner can update template"
    assert _new_template != empty(address), "Invalid template address"
    
    log ProfileTemplateUpdated(previous_template=self.profileTemplate, new_template=_new_template)
    self.profileTemplate = _new_template

@view
@external
def getUserProfiles(_start: uint256, _limit: uint256) -> DynArray[address, 100]:
    """
    Get a list of user profiles
    @param _start Starting index
    @param _limit Maximum number of profiles to return
    @return List of user addresses with profiles
    """
    result: DynArray[address, 100] = []
    
    if _start >= len(self.latestUsers):
        return result
    
    end: uint256 = min(_start + _limit, len(self.latestUsers))
    
    for i in range(_start, end):
        result.append(self.latestUsers[i])
    
    return result 