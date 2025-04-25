# @version 0.4.1
# ProfileHub - Central registry for user profiles
# Maps user addresses to their profile contracts
# Allows for creation of new profiles and querying existing ones

interface Profile:
    def initialize(_owner: address): nonpayable
    def deployer() -> address: view

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
    self.accountToProfile[msg.sender] = profile
    self.userCount += 1
    
    # Add to the list of users in a rotating manner
    self.latestUsers[self.userCount % 1000] = msg.sender
    
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