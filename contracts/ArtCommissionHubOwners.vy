# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# Contract links
l2OwnershipRelay: public(address)
artCommissionHubTemplate: public(address) 
profileFactoryAndRegistry: public(address)

# Owner of the contract
owner: public(address)
ownerRevokedToDAO: public(bool)

# Container for ArtCommissionHubs (NFT vs Generic):
# artCommissionHubRegistry[chain_id][nft_contract][nft_token_id_or_generic_hub_account] = commission_hub_address
# artCommissionHubRegistry[chain_id][GENERIC_HUB_CONTRACT][convert(owner_address, uint256)] = commission_hub_address
GENERIC_ART_COMMISSION_HUB_CONTRACT: constant(address) = 0x1000000000000000000000000000000000000001
GENERIC_ART_COMMISSION_HUB_CHAIN_ID: constant(uint256) = 1
artCommissionHubRegistry: public(HashMap[uint256, HashMap[address, HashMap[uint256, address]]])  # chain_id -> nft_contract -> nft_token_id_or_generic_hub_account -> commission_hub
artCommissionHubOwners: public(HashMap[uint256, HashMap[address, HashMap[uint256, address]]])  # chain_id -> nft_contract -> nft_token_id_or_generic_hub_account -> owner
artCommissionHubLastUpdated: public(HashMap[uint256, HashMap[address, HashMap[uint256, uint256]]])  # chain_id -> nft_contract -> nft_token_id_or_generic_hub_account -> timestamp
artCommissionHubsByOwner: public(HashMap[address, DynArray[address, 10**8]])  # owner -> list of commission hubs

# Track which commission hubs are generic (not tied to NFTs)
isGenericHub: public(HashMap[address, bool])  # commission_hub -> is_generic

# Track which art piece code hashes are approved
approvedArtPieceCodeHashes: public(HashMap[bytes32, bool])  # code_hash -> is_approved


interface ArtCommissionHub:
    def initializeForArtCommissionHub(chain_id: uint256, nft_contract: address, nft_token_id_or_generic_hub_account: uint256, owner: address): nonpayable
    def syncArtCommissionHubOwner(chain_id: uint256, nft_contract: address, nft_token_id_or_generic_hub_account: uint256, owner: address): nonpayable
    def getOwner() -> address: view

interface ProfileFactoryAndRegistry:
    def hasProfile(_address: address) -> bool: view
    def getProfile(_address: address) -> address: view
    def createProfile(_address: address) -> address: nonpayable
    def linkArtCommissionHubOwnersContract(_registry: address): nonpayable

interface Profile:
    def addCommissionHub(_hub: address): nonpayable
    def removeCommissionHub(_hub: address): nonpayable

event Registered:
    chain_id: uint256
    nft_contract: indexed(address)
    nft_token_id_or_generic_hub_account: indexed(uint256)
    owner: address
    commission_hub: indexed(address)
    timestamp: uint256
    source: address

event ArtCommissionHubCreated:
    chain_id: uint256
    nft_contract: indexed(address)
    nft_token_id_or_generic_hub_account: indexed(uint256)
    commission_hub: indexed(address)
    is_generic: bool

event GenericCommissionHubCreated:
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

event L2OwnershipRelaySet:
    l2OwnershipRelay: address

event CodeHashWhitelistUpdated:
    code_hash: indexed(bytes32)
    status: bool
   
@deploy
def __init__(_initial_l2relay: address, _initial_commission_hub_template: address, _art_piece_template: address):
    self.l2OwnershipRelay = _initial_l2relay
    self.artCommissionHubTemplate = _initial_commission_hub_template
    self.owner = msg.sender
    self.profileFactoryAndRegistry = empty(address)
    code_hash: bytes32 = _art_piece_template.codehash
    log CodeHashWhitelistUpdated(code_hash=code_hash, status=True)
    self.approvedArtPieceCodeHashes[code_hash] = True

@internal
def _ensureProfileForAddress(_address: address) -> address:
    """
    @notice Ensures that a user has a profile, creating one if needed
    @dev This function will check if a profile exists and create one if not
    @param _address The address of the user to check/create a profile for
    @return The address of the user's profile
    """
    if self.profileFactoryAndRegistry == empty(address):
        return empty(address)  # Profile-Factory-And-Registry not set, can't create profiles
    
    profile_factory_and_regsitry: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
    
    # Check if user already has a profile
    if staticcall profile_factory_and_regsitry.hasProfile(_address):
        return staticcall profile_factory_and_regsitry.getProfile(_address)
    
    # Create a new profile for the user using the createProfile function
    profile_address: address = extcall profile_factory_and_regsitry.createProfile(_address)
    return profile_address

@internal
def _appendHubToOwner(_owner: address, _hub: address):
    # Check if hub is already in the owner's list
    hubs_len: uint256 = len(self.artCommissionHubsByOwner[_owner])
    for i:uint256 in range(10**8):
        if i >= hubs_len:
            break
        if self.artCommissionHubsByOwner[_owner][i] == _hub:
            return  # Hub already exists, nothing to do
    
    # Add the hub to the owner's list
    self.artCommissionHubsByOwner[_owner].append(_hub)
    
    # Emit event for tracking
    log HubLinkedToOwner(owner=_owner, hub=_hub)
    
    # Ensure the owner has a profile and link the hub to it, but only if profile-factory-and-registry is set
    if self.profileFactoryAndRegistry != empty(address):
        # This will create a profile if one doesn't exist
        profile_address: address = self._ensureProfileForAddress(_owner)
        if profile_address != empty(address):
            profile: Profile = Profile(profile_address)
            extcall profile.addCommissionHub(_hub)

@internal
def _removeHubFromOwner(_owner: address, _hub: address):
    # Find the hub in the owner's list
    hub_index: int256 = -1
    hubs_len: uint256 = len(self.artCommissionHubsByOwner[_owner])
    for i:uint256 in range(10**8):
        if i >= hubs_len:
            break
        if self.artCommissionHubsByOwner[_owner][i] == _hub:
            hub_index = convert(i, int256)
            break
    
    # If hub found, remove it using swap and pop
    if hub_index >= 0:
        # Convert back to uint256 for array operations
        idx: uint256 = convert(hub_index, uint256)
        # If not the last element, swap with the last element
        if idx < len(self.artCommissionHubsByOwner[_owner]) - 1:
            last_hub: address = self.artCommissionHubsByOwner[_owner][len(self.artCommissionHubsByOwner[_owner]) - 1]
            self.artCommissionHubsByOwner[_owner][idx] = last_hub
        # Remove the last element
        self.artCommissionHubsByOwner[_owner].pop()
        
        # Emit event for tracking
        log HubUnlinkedFromOwner(owner=_owner, hub=_hub)
        
        # If the owner has a profile, remove the hub from their profile
        if self.profileFactoryAndRegistry != empty(address):
            profile_factory_and_regsitry: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
            if staticcall profile_factory_and_regsitry.hasProfile(_owner):
                profile_address: address = staticcall profile_factory_and_regsitry.getProfile(_owner)
                profile: Profile = Profile(profile_address)
                extcall profile.removeCommissionHub(_hub)

@internal
def _createOrUpdateCommissionHubAndOwner(_chain_id: uint256,_nft_contract: address,_nft_token_id_or_generic_hub_account: uint256, _owner: address):
    
    current_time: uint256 = block.timestamp
    previous_owner: address = self.artCommissionHubOwners[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account]
    
    # Update the owner 
    self.artCommissionHubOwners[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account] = _owner
    self.artCommissionHubLastUpdated[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account] = current_time
    
    # Update or create the commission hub
    commission_hub: address = empty(address)

    # If there has NEVER been a commissionHub, we need to create one before we can give it an owner
    if previous_owner == empty(address):
        #1. Create the commission hub
        #2. Initialize the commission hub
        #3. Register the commission hub
        #4. Add the commission hub to the new owner's list  
        commission_hub = create_minimal_proxy_to(self.artCommissionHubTemplate)
        commission_hub_instance: ArtCommissionHub = ArtCommissionHub(commission_hub)
        extcall commission_hub_instance.initializeForArtCommissionHub(_chain_id, _nft_contract, _nft_token_id_or_generic_hub_account, _owner)
        self.artCommissionHubRegistry[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account] = commission_hub
        self.isGenericHub[commission_hub] = False
        log ArtCommissionHubCreated(chain_id=_chain_id, nft_contract=_nft_contract, nft_token_id_or_generic_hub_account=_nft_token_id_or_generic_hub_account, commission_hub=commission_hub, is_generic=False)
        if _owner != empty(address):
            self._appendHubToOwner(_owner, commission_hub)

    # If the owner is changing, we need to update the commission hub
    elif previous_owner != _owner:
        commission_hub = self.artCommissionHubRegistry[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account]
        commission_hub_instance: ArtCommissionHub = ArtCommissionHub(commission_hub)
        extcall commission_hub_instance.syncArtCommissionHubOwner(_chain_id, _nft_contract, _nft_token_id_or_generic_hub_account, _owner)
        
        # Remove the hub from the old owner's list
        if previous_owner != empty(address):
            self._removeHubFromOwner(previous_owner, commission_hub)
        
        # Add the hub to the new owner's list
        if _owner != empty(address):
            self._appendHubToOwner(_owner, commission_hub)
    else:
        # Owner hasn't changed, just get the existing hub
        commission_hub = self.artCommissionHubRegistry[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account]
    
    log Registered(
        chain_id=_chain_id,
        nft_contract=_nft_contract, 
        nft_token_id_or_generic_hub_account=_nft_token_id_or_generic_hub_account, 
        owner=_owner, 
        commission_hub=commission_hub,
        timestamp=current_time,
        source=msg.sender
    )

@internal
@view
def _isContract(_addr: address) -> bool:
    """
    @notice Check if an address is a contract
    @param _addr The address to check
    @return Whether the address is a contract
    """
    size: uint256 = 0
    # Check code size at address
    if _addr != empty(address):
        if len(slice(_addr.code, 0, 1)) > 0:
            size = 1
    return size > 0

#Called by L2OwnershipRelay when ownership is verified, including chain_id, nft_contract, nft_token_id_or_generic_hub_account, and owner as parameters.
@external
def registerNFTOwnerFromParentChain(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256, _owner: address):
    # Only allow registration from L2OwnershipRelay
    assert msg.sender == self.l2OwnershipRelay or msg.sender == self.owner, "Only L2OwnershipRelay or the owner can register artCommissionHubOwners"
    self._createOrUpdateCommissionHubAndOwner(_chain_id, _nft_contract, _nft_token_id_or_generic_hub_account, _owner)

# Create a generic commission hub for non-NFT artCommissionHubOwners like multisigs, DAOs, or individual wallets
@external
def createGenericCommissionHub(_owner: address) -> address:
    """
    @notice Creates a generic commission hub for non-NFT artCommissionHubOwners
    @dev This allows multisigs, DAOs, or individual wallets to have commission hubs
         without requiring them to own an NFT
    @param _owner The address that will own this commission hub
    @return The address of the newly created commission hub
    """

    assert msg.sender == _owner or msg.sender == self.owner, "Only the owner can create their own generic commission hub"
    assert self.profileFactoryAndRegistry != empty(address), "Profile-Factory-And-Registry not set"
    
    # check its not already registered
    if self.artCommissionHubRegistry[GENERIC_ART_COMMISSION_HUB_CHAIN_ID][GENERIC_ART_COMMISSION_HUB_CONTRACT][convert(_owner, uint256)] != empty(address):
        return self.artCommissionHubRegistry[GENERIC_ART_COMMISSION_HUB_CHAIN_ID][GENERIC_ART_COMMISSION_HUB_CONTRACT][convert(_owner, uint256)]

    # Create a profile for the owner if the owner doesn't have a profile yet
    profile_factory_and_regsitry: ProfileFactoryAndRegistry = ProfileFactoryAndRegistry(self.profileFactoryAndRegistry)
    if not staticcall profile_factory_and_regsitry.hasProfile(_owner):
        # Create a profile for the owner using createProfile
        profile_address: address = extcall profile_factory_and_regsitry.createProfile(_owner)
        # Log profile creation
        log ProfileCreated(owner=_owner, profile=profile_address)
    
    _nft_token_id_or_generic_hub_account: uint256 = convert(_owner, uint256)

    # Create a new commission hub
    commission_hub: address = create_minimal_proxy_to(self.artCommissionHubTemplate)
    commission_hub_instance: ArtCommissionHub = ArtCommissionHub(commission_hub)
    
    # Initialize the generic hub
    extcall commission_hub_instance.initializeForArtCommissionHub(
        GENERIC_ART_COMMISSION_HUB_CHAIN_ID, 
        GENERIC_ART_COMMISSION_HUB_CONTRACT, 
        _nft_token_id_or_generic_hub_account, 
        _owner)
    
    self.isGenericHub[commission_hub] = True
    self._appendHubToOwner(_owner, commission_hub)
    log GenericCommissionHubCreated(owner=_owner, commission_hub=commission_hub)
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
    profile_address: address = self._ensureProfileForAddress(_owner)
    if profile_address == empty(address):
        return
    
    profile: Profile = Profile(profile_address)
    
    # Link all hubs to the profile
    hubs_len: uint256 = len(self.artCommissionHubsByOwner[_owner])
    for i:uint256 in range(10**8):
        if i >= hubs_len:
            break
        hub: address = self.artCommissionHubsByOwner[_owner][i]
        extcall profile.addCommissionHub(hub)

#Called by other contracts on L3 to query the owner of an NFT
@view
@external
def lookupRegisteredOwner(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256) -> address:
    return self.artCommissionHubOwners[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account]

#Get the timestamp when an owner was last updated
@view
@external
def getArtCommissionHubLastUpdated(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256) -> uint256:
    return self.artCommissionHubLastUpdated[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account]

@view
@external
def getArtCommissionHubByOwner(_chain_id: uint256, _nft_contract: address, _nft_token_id_or_generic_hub_account: uint256) -> address:
    return self.artCommissionHubRegistry[_chain_id][_nft_contract][_nft_token_id_or_generic_hub_account]

@view
@external
def lookupEthereumRegisteredOwner(_nft_contract: address, _nft_token_id_or_generic_hub_account: uint256) -> address:
    return self.artCommissionHubOwners[1][_nft_contract][_nft_token_id_or_generic_hub_account]

@view
@external
def getEthereumArtCommissionHubLastUpdated(_nft_contract: address, _nft_token_id_or_generic_hub_account: uint256) -> uint256:
    return self.artCommissionHubLastUpdated[1][_nft_contract][_nft_token_id_or_generic_hub_account]

@view
@external
def getEthereumArtCommissionHubByOwner(_nft_contract: address, _nft_token_id_or_generic_hub_account: uint256) -> address:
    return self.artCommissionHubRegistry[1][_nft_contract][_nft_token_id_or_generic_hub_account]
    
# Set commission hub template
@external
def setArtCommissionHubTemplate(_new_template: address):
    assert msg.sender == self.owner, "Only owner can set commission hub template"
    self.artCommissionHubTemplate = _new_template

# Set L2 relay
@external
def setL2OwnershipRelay(_new_l2relay: address):
    assert msg.sender == self.owner, "Only owner can set L2 relay"
    self.l2OwnershipRelay = _new_l2relay
    log L2OwnershipRelaySet(l2OwnershipRelay=_new_l2relay)

# IMPORTANT: Deployment Order Requirements
# This function MUST be called after both contracts are deployed in this order:
# 1. Deploy ProfileFactoryAndRegistry
# 2. Deploy ArtCommissionHubOwners
# 3. Call linkProfileFactoryAndRegistry on ArtCommissionHubOwners
# Failure to call this function will prevent automatic linking of commission hubs to profiles,
# causing hubs to be invisible in user profiles until manually linked.
# Set profile-factory-and-registry
@external
def linkProfileFactoryAndRegistry(_profile_factory_and_regsitry: address):
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
        extcall profile_factory_and_regsitry_interface.linkArtCommissionHubOwnersContract(self)

# Get commission hubs for an owner with pagination
@view
@external
def getCommissionHubsByOwner(_owner: address, _page: uint256, _page_size: uint256) -> DynArray[address, 100]:
    result: DynArray[address, 100] = []
    
    total_hubs: uint256 = len(self.artCommissionHubsByOwner[_owner])
    if total_hubs == 0 or _page * _page_size >= total_hubs:
        return result
    
    start: uint256 = _page * _page_size
    count: uint256 = min(min(_page_size, total_hubs - start), 100)  # Cap at 100 due to return type
    
    for i: uint256 in range(100):
        if i >= count:
            break
        if start + i < total_hubs:  # Safety check
            result.append(self.artCommissionHubsByOwner[_owner][start + i])
    
    return result

# Get commission hubs for an owner with offset-based pagination
@view
@external
def getCommissionHubsByOwnerWithOffset(_owner: address, _offset: uint256, _count: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a paginated list of commission hubs owned by a specific address using offset-based pagination
    @dev This allows the UI to implement its own randomization by fetching different pages
    @param _owner The address whose commission hubs to query
    @param _offset The starting index in the commission hubs array
    @param _count The number of hubs to return (capped at 50)
    @return A list of commission hub addresses
    """
    result: DynArray[address, 50] = []
    
    total_hubs: uint256 = len(self.artCommissionHubsByOwner[_owner])
    if total_hubs == 0 or _offset >= total_hubs:
        return result
    
    # Calculate how many items to return
    available_items: uint256 = total_hubs - _offset
    count: uint256 = min(min(_count, available_items), 50)
    
    # Populate result array
    for i: uint256 in range(50):
        if i >= count:
            break
        result.append(self.artCommissionHubsByOwner[_owner][_offset + i])
    
    return result

# Get the total number of commission hubs for an owner
@view
@external
def getCommissionHubCountByOwner(_owner: address) -> uint256:
    return len(self.artCommissionHubsByOwner[_owner])

# Get random commission hubs for an owner
@view
@external
def getRandomCommissionHubsByOwner(_owner: address, _count: uint256, _seed: uint256) -> DynArray[address, 50]:
    """
    @notice Returns a set of random commission hubs owned by a specific address
    @dev Uses the provided seed combined with block timestamp for randomness
    @param _owner The address whose commission hubs to query
    @param _count The number of random hubs to return (capped at 50)
    @param _seed A seed value to influence the randomness
    @return A list of random commission hub addresses
    """
    result: DynArray[address, 50] = []
    
    total_hubs: uint256 = len(self.artCommissionHubsByOwner[_owner])
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
                result.append(self.artCommissionHubsByOwner[_owner][i])
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
        hub_address: address = self.artCommissionHubsByOwner[_owner][random_index]
        
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
                next_hub: address = self.artCommissionHubsByOwner[_owner][k]
                
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
    
# Call once to revoke ownership to DAO
@external
def revokeOwnershipToDAO(_dao_contract_address: address):
    assert not self.ownerRevokedToDAO, "Ownership already revoked to DAO"
    assert msg.sender == self.owner, "Only the owner can revoke ownership to DAO"
    self.ownerRevokedToDAO = True
    self.owner = _dao_contract_address

@external
def setApprovedArtPiece(_art_piece: address, _is_approved: bool):
    assert msg.sender == self.owner, "Only the owner can set approved art piece code hashes"
    assert self._isContract(_art_piece), "Art piece is not a contract"
    code_hash: bytes32 = _art_piece.codehash
    log CodeHashWhitelistUpdated(code_hash=code_hash, status=_is_approved)
    self.approvedArtPieceCodeHashes[code_hash] = _is_approved

@external
@view
def isApprovedArtPiece(_code_hash: bytes32) -> bool:
    return self.approvedArtPieceCodeHashes[_code_hash]

@external
@view
def isApprovedArtPieceAddress(_art_piece: address) -> bool:
    code_hash: bytes32 = _art_piece.codehash
    return self.approvedArtPieceCodeHashes[code_hash]

@external
@view
def isAllowedToUpdateHubForAddress(_commission_hub: address, _user: address) -> bool:
    commission_hub: ArtCommissionHub = ArtCommissionHub(_commission_hub)
    if commission_hub.address == empty(address):
        return False
    owner: address = staticcall commission_hub.getOwner()
    return _user == owner

@external
@view
def isSystemAllowed(_address: address) -> bool:
    # Either the owner or the L2OwnershipRelay or the address itself can update the owner
    allowed: bool = (_address == self.owner or  _address == self.l2OwnershipRelay)
    return allowed
