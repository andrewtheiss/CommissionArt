# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# Function to handle owner verification on L3
# This takes in messages from the L2 and updates a registry of nft/id pairs to their owner
# This handles taking queries from other contracts on L3 and returning the owner of the NFT

# Need to double check storage variables
l2Relay: public(address)
artCommissionHubTemplate: public(address)
owner: public(address)
# Updated data structures to include chain ID
artCommissionHubs: public(HashMap[uint256, HashMap[address, HashMap[uint256, address]]])  # chain_id -> nft_contract -> token_id -> commission_hub
owners: public(HashMap[uint256, HashMap[address, HashMap[uint256, address]]])  # chain_id -> nft_contract -> token_id -> owner
# Add last update timestamps for each NFT/token ID pair
lastUpdated: public(HashMap[uint256, HashMap[address, HashMap[uint256, uint256]]])  # chain_id -> nft_contract -> token_id -> timestamp

# Mapping to track commission hubs owned by each address
ownerToCommissionHubs: public(HashMap[address, DynArray[address, 10**8]])  # owner -> list of commission hubs

# Track which commission hubs are generic (not tied to NFTs)
isGenericHub: public(HashMap[address, bool])  # commission_hub -> is_generic

# Profile-Factory-And-Registry address
profileFactoryAndRegistry: public(address)

interface ArtCommissionHub:
    def initialize(chain_id: uint256, nft_contract: address, token_id: uint256, registry: address): nonpayable
    def updateRegistration(chain_id: uint256, nft_contract: address, token_id: uint256, owner: address): nonpayable
    def initializeGeneric(chain_id: uint256, owner: address, registry: address, is_generic: bool): nonpayable

interface ProfileFactoryAndRegistry:
    def hasProfile(_user: address) -> bool: view
    def getProfile(_user: address) -> address: view
    def createProfile(_user: address) -> address: nonpayable
    def setOwnerRegistry(_registry: address): nonpayable
    def createProfileFor(_user: address) -> address: nonpayable

interface Profile:
    def addCommissionHub(_hub: address): nonpayable
    def removeCommissionHub(_hub: address): nonpayable

event Registered:
    chain_id: uint256
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address
    commission_hub: indexed(address)
    timestamp: uint256
    source: address

event ArtCommissionHubCreated:
    chain_id: uint256
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    commission_hub: indexed(address)
    is_generic: bool

event GenericCommissionHubCreated:
    chain_id: uint256
    owner: indexed(address)
    commission_hub: indexed(address)

event HubLinkedToOwner:
    owner: indexed(address)
    hub: indexed(address)

event HubUnlinkedFromOwner:
    owner: indexed(address)
    hub: indexed(address)

event ProfileCreated:
    owner: indexed(address)
    profile: indexed(address)

@deploy
def __init__(_initial_l2relay: address, _initial_commission_hub_template: address):
    self.l2Relay = _initial_l2relay
    self.artCommissionHubTemplate = _initial_commission_hub_template
    self.owner = msg.sender
    self.profileFactoryAndRegistry = empty(address)

# Internal function to ensure a user has a profile
@internal
def _ensureProfile(_user: address) -> address:
    """
    @notice Ensures that a user has a profile, creating one if needed
    @dev This function will check if a profile exists and create one if not
    @param _user The address of the user to check/create a profile for
    @return The address of the user's profile
    """
    if self.profileFactoryAndRegistry == empty(address):
        return empty(address)  # Profile-Factory-And-Registry not set, can't create profiles
    
    profile_factory_and_regsitry: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
    
    # Check if user already has a profile
    if staticcall profile_factory_and_regsitry.hasProfile(_user):
        return staticcall profile_factory_and_regsitry.getProfile(_user)
    
    # Create a new profile for the user using the createProfileFor function
    profile_address: address = extcall profile_factory_and_regsitry.createProfileFor(_user)
    
    return profile_address

# Internal function to add a hub to an owner's list
@internal
def _addHubToOwner(_owner: address, _hub: address):
    # Check if hub is already in the owner's list
    hubs_len: uint256 = len(self.ownerToCommissionHubs[_owner])
    for i:uint256 in range(10**8):
        if i >= hubs_len:
            break
        if self.ownerToCommissionHubs[_owner][i] == _hub:
            return  # Hub already exists, nothing to do
    
    # Add the hub to the owner's list
    self.ownerToCommissionHubs[_owner].append(_hub)
    
    # Emit event for tracking
    log HubLinkedToOwner(owner=_owner, hub=_hub)
    
    # Ensure the owner has a profile and link the hub to it, but only if profile-factory-and-registry is set
    if self.profileFactoryAndRegistry != empty(address):
        # This will create a profile if one doesn't exist
        profile_address: address = self._ensureProfile(_owner)
        if profile_address != empty(address):
            profile: Profile = Profile(profile_address)
            extcall profile.addCommissionHub(_hub)

# Internal function to remove a hub from an owner's list
@internal
def _removeHubFromOwner(_owner: address, _hub: address):
    # Find the hub in the owner's list
    hub_index: int256 = -1
    hubs_len: uint256 = len(self.ownerToCommissionHubs[_owner])
    for i:uint256 in range(10**8):
        if i >= hubs_len:
            break
        if self.ownerToCommissionHubs[_owner][i] == _hub:
            hub_index = convert(i, int256)
            break
    
    # If hub found, remove it using swap and pop
    if hub_index >= 0:
        # Convert back to uint256 for array operations
        idx: uint256 = convert(hub_index, uint256)
        # If not the last element, swap with the last element
        if idx < len(self.ownerToCommissionHubs[_owner]) - 1:
            last_hub: address = self.ownerToCommissionHubs[_owner][len(self.ownerToCommissionHubs[_owner]) - 1]
            self.ownerToCommissionHubs[_owner][idx] = last_hub
        # Remove the last element
        self.ownerToCommissionHubs[_owner].pop()
        
        # Emit event for tracking
        log HubUnlinkedFromOwner(owner=_owner, hub=_hub)
        
        # If the owner has a profile, remove the hub from their profile
        if self.profileFactoryAndRegistry != empty(address):
            profile_factory_and_regsitry: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
            if staticcall profile_factory_and_regsitry.hasProfile(_owner):
                profile_address: address = staticcall profile_factory_and_regsitry.getProfile(_owner)
                profile: Profile = Profile(profile_address)
                extcall profile.removeCommissionHub(_hub)

# Internal function to register NFT ownership
@internal
def _registerNFTOwner(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _owner: address, _source: address):
    # Record the current timestamp
    current_time: uint256 = block.timestamp
    
    # Store the old owner before updating
    old_owner: address = self.owners[_chain_id][_nft_contract][_token_id]
    
    # If the commission hub doesn't exist, create it
    if old_owner == empty(address):
        commission_hub: address = create_minimal_proxy_to(self.artCommissionHubTemplate)
        commission_hub_instance: ArtCommissionHub = ArtCommissionHub(commission_hub)
        extcall commission_hub_instance.initialize(_chain_id, _nft_contract, _token_id, self)
        self.artCommissionHubs[_chain_id][_nft_contract][_token_id] = commission_hub
        self.isGenericHub[commission_hub] = False
        log ArtCommissionHubCreated(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, commission_hub=commission_hub, is_generic=False)
        
        # Add the hub to the new owner's list
        if _owner != empty(address):
            self._addHubToOwner(_owner, commission_hub)
    elif old_owner != _owner:
        # If the owner is changing, we need to update the commission hub
        commission_hub: address = self.artCommissionHubs[_chain_id][_nft_contract][_token_id]
        commission_hub_instance: ArtCommissionHub = ArtCommissionHub(commission_hub)
        extcall commission_hub_instance.updateRegistration(_chain_id, _nft_contract, _token_id, _owner)
        
        # Remove the hub from the old owner's list
        if old_owner != empty(address):
            self._removeHubFromOwner(old_owner, commission_hub)
        
        # Add the hub to the new owner's list
        if _owner != empty(address):
            self._addHubToOwner(_owner, commission_hub)

    # Update the owner and the last update timestamp
    self.owners[_chain_id][_nft_contract][_token_id] = _owner
    self.lastUpdated[_chain_id][_nft_contract][_token_id] = current_time
    
    log Registered(
        chain_id=_chain_id,
        nft_contract=_nft_contract, 
        token_id=_token_id, 
        owner=_owner, 
        commission_hub=self.artCommissionHubs[_chain_id][_nft_contract][_token_id],
        timestamp=current_time,
        source=_source
    )

#Called by L2Relay when ownership is verified, including chain_id, nft_contract, token_id, and owner as parameters.
@external
def registerNFTOwnerFromParentChain(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _owner: address):
    # Only allow registration from L2Relay
    assert msg.sender == self.l2Relay, "Only L2Relay can register NFT owners"
    self._registerNFTOwner(_chain_id, _nft_contract, _token_id, _owner, msg.sender)

# Create a generic commission hub for non-NFT owners like multisigs, DAOs, or individual wallets
@external
def createGenericCommissionHub(_chain_id: uint256, _owner: address) -> address:
    """
    @notice Creates a generic commission hub for non-NFT owners
    @dev This allows multisigs, DAOs, or individual wallets to have commission hubs
         without requiring them to own an NFT
    @param _chain_id The chain ID where the hub will be registered
    @param _owner The address that will own this commission hub
    @return The address of the newly created commission hub
    """
    # Ensure the owner address is valid
    assert _owner != empty(address), "Owner cannot be empty"

    # Only the owner can create their own commission hub
    assert msg.sender == _owner, "Only the owner can create their own generic commission hub"
    
    # Create a profile for the owner if the profile-factory-and-registry is set and the owner doesn't have a profile yet
    if self.profileFactoryAndRegistry != empty(address):
        profile_factory_and_regsitry: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
        if not staticcall profile_factory_and_regsitry.hasProfile(_owner):
            # Create a profile for the owner using createProfileFor
            profile_address: address = extcall profile_factory_and_regsitry.createProfileFor(_owner)
            # Log profile creation
            log ProfileCreated(owner=_owner, profile=profile_address)
    
    # Create a new commission hub
    commission_hub: address = create_minimal_proxy_to(self.artCommissionHubTemplate)
    commission_hub_instance: ArtCommissionHub = ArtCommissionHub(commission_hub)
    
    # Initialize the generic hub
    extcall commission_hub_instance.initializeGeneric(_chain_id, _owner, self, True)
    
    # Mark this hub as generic
    self.isGenericHub[commission_hub] = True
    
    # Add the hub to the owner's list
    self._addHubToOwner(_owner, commission_hub)
    
    # Emit event for tracking
    log GenericCommissionHubCreated(chain_id=_chain_id, owner=_owner, commission_hub=commission_hub)
    
    return commission_hub

# Check if a commission hub is generic
@view
@external
def isGeneric(_commission_hub: address) -> bool:
    """
    @notice Checks if a commission hub is generic (not tied to an NFT)
    @param _commission_hub The address of the commission hub to check
    @return True if the hub is generic, False otherwise
    """
    return self.isGenericHub[_commission_hub]

# Link existing commission hubs to the owner's profile
@external
def linkHubsToProfile(_owner: address):
    """
    @notice Links all commission hubs owned by an address to their profile
    @dev This can be used to sync hubs with a newly created profile
         or to repair links if they become out of sync
    @param _owner The address whose hubs should be linked to their profile
    """
    # Ensure profile-factory-and-registry is set
    assert self.profileFactoryAndRegistry != empty(address), "Profile-Factory-And-Registry not set"
    
    # Ensure the owner has a profile (creates one if needed)
    profile_address: address = self._ensureProfile(_owner)
    if profile_address == empty(address):
        return
    
    profile: Profile = Profile(profile_address)
    
    # Link all hubs to the profile
    hubs_len: uint256 = len(self.ownerToCommissionHubs[_owner])
    for i:uint256 in range(10**8):
        if i >= hubs_len:
            break
        hub: address = self.ownerToCommissionHubs[_owner][i]
        extcall profile.addCommissionHub(hub)

#Called by other contracts on L3 to query the owner of an NFT
@view
@external
def lookupRegisteredOwner(_chain_id: uint256, _nft_contract: address, _token_id: uint256) -> address:
    return self.owners[_chain_id][_nft_contract][_token_id]

#Get the timestamp when an owner was last updated
@view
@external
def getLastUpdated(_chain_id: uint256, _nft_contract: address, _token_id: uint256) -> uint256:
    return self.lastUpdated[_chain_id][_nft_contract][_token_id]

@view
@external
def getArtCommissionHubByOwner(_chain_id: uint256, _nft_contract: address, _token_id: uint256) -> address:
    return self.artCommissionHubs[_chain_id][_nft_contract][_token_id]

@view
@external
def lookupEthereumRegisteredOwner(_nft_contract: address, _token_id: uint256) -> address:
    return self.owners[1][_nft_contract][_token_id]

@view
@external
def getEthereumLastUpdated(_nft_contract: address, _token_id: uint256) -> uint256:
    return self.lastUpdated[1][_nft_contract][_token_id]

@view
@external
def getEthereumArtCommissionHubByOwner(_nft_contract: address, _token_id: uint256) -> address:
    return self.artCommissionHubs[1][_nft_contract][_token_id]
    
# Set commission hub template
@external
def setArtCommissionHubTemplate(_new_template: address):
    assert msg.sender == self.owner, "Only owner can set commission hub template"
    self.artCommissionHubTemplate = _new_template

# Set L2 relay
@external
def setL2Relay(_new_l2relay: address):
    assert msg.sender == self.owner, "Only owner can set L2 relay"
    self.l2Relay = _new_l2relay
    log L2RelaySet(l2Relay=_new_l2relay)

# IMPORTANT: Deployment Order Requirements
# This function MUST be called after both contracts are deployed in this order:
# 1. Deploy ProfileFactoryAndRegistry
# 2. Deploy OwnerRegistry
# 3. Call setProfileFactoryAndRegistry on OwnerRegistry
# Failure to call this function will prevent automatic linking of commission hubs to profiles,
# causing hubs to be invisible in user profiles until manually linked.
# Set profile-factory-and-registry
@external
def setProfileFactoryAndRegistry(_profile_factory_and_regsitry: address):
    """
    @notice Sets the address of the ProfileFactoryAndRegistry contract and establishes bidirectional connection
    @dev This function should be called:
         1. During initial system deployment after both contracts are deployed
         2. When upgrading to a new ProfileFactoryAndRegistry implementation
         3. If the connection between contracts needs to be reset
    @dev This establishes a critical link that enables:
         - Automatic linking of commission hubs to user profiles when NFT ownership changes
         - Automatic linking of existing hubs when a user creates a new profile
         - Proper unlinking of hubs when NFT ownership transfers to another user
    @dev Only the contract owner can call this function
    @param _profile_factory_and_regsitry The address of the ProfileFactoryAndRegistry contract
    """
    assert msg.sender == self.owner, "Only owner can set profile-factory-and-registry"
    self.profileFactoryAndRegistry = _profile_factory_and_regsitry
    
    # Inform the ProfileFactoryAndRegistry about this registry to establish bidirectional connection
    if _profile_factory_and_regsitry != empty(address):
        profile_factory_and_regsitry_interface: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(_profile_factory_and_regsitry)
        extcall profile_factory_and_regsitry_interface.setOwnerRegistry(self)

# Get commission hubs for an owner with pagination
@view
@external
def getCommissionHubsForOwner(_owner: address, _page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    
    total_hubs: uint256 = len(self.ownerToCommissionHubs[_owner])
    if total_hubs == 0 or _page * _page_size >= total_hubs:
        return result
    
    start: uint256 = _page * _page_size
    count: uint256 = min(min(_page_size, total_hubs - start), 100)  # Cap at 100 due to return type
    
    for i: uint256 in range(100):
        if i >= count:
            break
        if start + i < total_hubs:  # Safety check
            result.append(self.ownerToCommissionHubs[_owner][start + i])
    
    return result

# Get commission hubs for an owner with offset-based pagination
@view
@external
def getCommissionHubsForOwnerByOffset(_owner: address, _offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of commission hubs owned by a specific address using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _owner The address whose commission hubs to query
    @param _offset The starting index in the commission hubs array
    @param _count The number of hubs to return (capped at 50)
    @return A list of commission hub addresses
    """
    result: DynArray[address, 50] = []
    
    total_hubs: uint256 = len(self.ownerToCommissionHubs[_owner])
    if total_hubs == 0 or _offset >= total_hubs:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = total_hubs - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.ownerToCommissionHubs[_owner][_offset + i])
    
    return result

# Get the total number of commission hubs for an owner
@view
@external
def getCommissionHubCountForOwner(_owner: address) -> uint256:
    return len(self.ownerToCommissionHubs[_owner])

# Get random commission hubs for an owner
@view
@external
def getRandomCommissionHubsForOwner(_owner: address, _count: uint256, _seed: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a set of random commission hubs owned by a specific address
    @dev Uses the provided seed combined with block timestamp for randomness
    @param _owner The address whose commission hubs to query
    @param _count The number of random hubs to return (capped at 50)
    @param _seed A seed value to influence the randomness
    @return A list of random commission hub addresses
    """
    result: DynArray[address, 50] = []
    
    total_hubs: uint256 = len(self.ownerToCommissionHubs[_owner])
    if total_hubs == 0:
        return result
    
    # Cap the count at 50 or the total number of hubs, whichever is smaller
    count: uint256 = min(min(_count, total_hubs), 50)
    
    # If we need all or most hubs, just return them sequentially
    if count * 4 >= total_hubs * 3:  # If we need 75% or more of the hubs
        for i: uint256 in range(50):
            if i >= count:
                break
            if i < total_hubs:
                result.append(self.ownerToCommissionHubs[_owner][i])
        return result
    
    # Use a simple pseudo-random approach for selecting a subset
    random_seed: uint256 = block.timestamp + _seed
    
    # Since we can't use a HashMap in memory, we'll use a different approach
    # We'll use the result array to track what we've already added
    for i: uint256 in range(50):  # Fixed bound as required by Vyper
        if i >= count:
            break
            
        # Generate a random index
        random_index: uint256 = (random_seed + i * 13) % total_hubs
        hub_address: address = self.ownerToCommissionHubs[_owner][random_index]
        
        # Check if this hub is already in our result
        already_added: bool = False
        for j: uint256 in range(50):
            if j >= i:  # Only check up to our current position in the result array
                break
            if result[j] == hub_address:
                already_added = True
                break
        
        # If not already added, add it
        if not already_added:
            result.append(hub_address)
        else:
            # If already added, find the next unused one sequentially
            for k: uint256 in range(total_hubs, bound=1000):
                next_hub: address = self.ownerToCommissionHubs[_owner][k]
                
                # Check if this hub is already in our result
                already_in_result: bool = False
                for m: uint256 in range(50):
                    if m >= i:  # Only check up to our current position
                        break
                    if result[m] == next_hub:
                        already_in_result = True
                        break
                
                if not already_in_result:
                    result.append(next_hub)
                    break
    
    return result

event L2RelaySet:
    l2Relay: address
    
    


