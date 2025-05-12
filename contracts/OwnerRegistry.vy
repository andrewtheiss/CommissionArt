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
ownerToCommissionHubs: public(HashMap[address, DynArray[address, 10**6]])  # owner -> list of commission hubs

# Profile Hub address
profileHub: public(address)

interface ArtCommissionHub:
    def initialize(chain_id: uint256, nft_contract: address, token_id: uint256, registry: address): nonpayable
    def updateRegistration(chain_id: uint256, nft_contract: address, token_id: uint256, owner: address): nonpayable

interface ProfileHub:
    def hasProfile(_user: address) -> bool: view
    def getProfile(_user: address) -> address: view
    def setOwnerRegistry(_registry: address): nonpayable

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

event HubLinkedToOwner:
    owner: indexed(address)
    hub: indexed(address)

event HubUnlinkedFromOwner:
    owner: indexed(address)
    hub: indexed(address)

@deploy
def __init__(_initial_l2relay: address, _initial_commission_hub_template: address):
    self.l2Relay = _initial_l2relay
    self.artCommissionHubTemplate = _initial_commission_hub_template
    self.owner = msg.sender
    self.profileHub = empty(address)

# Internal function to add a hub to an owner's list
@internal
def _addHubToOwner(_owner: address, _hub: address):
    # Check if hub is already in the owner's list
    hubs_len: uint256 = len(self.ownerToCommissionHubs[_owner])
    for i:uint256 in range(10**6):
        if i >= hubs_len:
            break
        if self.ownerToCommissionHubs[_owner][i] == _hub:
            return  # Hub already exists, nothing to do
    
    # Add the hub to the owner's list
    self.ownerToCommissionHubs[_owner].append(_hub)
    
    # Emit event for tracking
    log HubLinkedToOwner(owner=_owner, hub=_hub)
    
    # If the owner has a profile, add the hub to their profile
    if self.profileHub != empty(address):
        profile_hub: ProfileHub = ProfileHub(self.profileHub)
        if staticcall profile_hub.hasProfile(_owner):
            profile_address: address = staticcall profile_hub.getProfile(_owner)
            profile: Profile = Profile(profile_address)
            extcall profile.addCommissionHub(_hub)

# Internal function to remove a hub from an owner's list
@internal
def _removeHubFromOwner(_owner: address, _hub: address):
    # Find the hub in the owner's list
    hub_index: int256 = -1
    hubs_len: uint256 = len(self.ownerToCommissionHubs[_owner])
    for i:uint256 in range(10**6):
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
        if self.profileHub != empty(address):
            profile_hub: ProfileHub = ProfileHub(self.profileHub)
            if staticcall profile_hub.hasProfile(_owner):
                profile_address: address = staticcall profile_hub.getProfile(_owner)
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
        log ArtCommissionHubCreated(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, commission_hub=commission_hub)
        
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

# Set profile hub
@external
def setProfileHub(_profile_hub: address):
    """
    @notice Sets the address of the ProfileHub contract and establishes bidirectional connection
    @dev This function should be called:
         1. During initial system deployment after both contracts are deployed
         2. When upgrading to a new ProfileHub implementation
         3. If the connection between contracts needs to be reset
    @dev This establishes a critical link that enables:
         - Automatic linking of commission hubs to user profiles when NFT ownership changes
         - Automatic linking of existing hubs when a user creates a new profile
         - Proper unlinking of hubs when NFT ownership transfers to another user
    @dev Only the contract owner can call this function
    @param _profile_hub The address of the ProfileHub contract
    """
    assert msg.sender == self.owner, "Only owner can set profile hub"
    self.profileHub = _profile_hub
    
    # Inform the ProfileHub about this registry to establish bidirectional connection
    if _profile_hub != empty(address):
        profile_hub_interface: ProfileHub = ProfileHub(_profile_hub)
        extcall profile_hub_interface.setOwnerRegistry(self)

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

# Get the total number of commission hubs for an owner
@view
@external
def getCommissionHubCountForOwner(_owner: address) -> uint256:
    return len(self.ownerToCommissionHubs[_owner])

event L2RelaySet:
    l2Relay: address
    
    


