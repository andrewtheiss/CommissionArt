# @version 0.4.1
# Function to handle owner verification on L3
# This takes in messages from the L2 and updates a registry of nft/id pairs to their owner
# This handles taking queries from other contracts on L3 and returning the owner of the NFT

# Need to double check storage variables
l2Relay: public(address)
commissionHubTemplate: public(address)
owner: public(address)
# Updated data structures to include chain ID
commissionHubs: public(HashMap[uint256, HashMap[address, HashMap[uint256, address]]])  # chain_id -> nft_contract -> token_id -> commission_hub
owners: public(HashMap[uint256, HashMap[address, HashMap[uint256, address]]])  # chain_id -> nft_contract -> token_id -> owner
# Add last update timestamps for each NFT/token ID pair
lastUpdated: public(HashMap[uint256, HashMap[address, HashMap[uint256, uint256]]])  # chain_id -> nft_contract -> token_id -> timestamp

interface CommissionHub:
    def initialize(chain_id: uint256, nft_contract: address, token_id: uint256, registry: address): nonpayable
    def updateRegistration(chain_id: uint256, nft_contract: address, token_id: uint256, owner: address): nonpayable

event Registered:
    chain_id: uint256
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address
    commission_hub: indexed(address)
    timestamp: uint256
    source: address

event CommissionHubCreated:
    chain_id: uint256
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    commission_hub: indexed(address)

@deploy
def __init__(_initial_l2relay: address, _initial_commission_hub_template: address):
    self.l2Relay = _initial_l2relay
    self.commissionHubTemplate = _initial_commission_hub_template
    self.owner = msg.sender

# Internal function to register NFT ownership
@internal
def _registerNFTOwner(_chain_id: uint256, _nft_contract: address, _token_id: uint256, _owner: address, _source: address):
    # Record the current timestamp
    current_time: uint256 = block.timestamp
    
    # If the commission hub doesn't exist, create it
    if self.owners[_chain_id][_nft_contract][_token_id] == empty(address):
        commission_hub: address = create_minimal_proxy_to(self.commissionHubTemplate)
        commission_hub_instance: CommissionHub = CommissionHub(commission_hub)
        extcall commission_hub_instance.initialize(_chain_id, _nft_contract, _token_id, self)
        self.commissionHubs[_chain_id][_nft_contract][_token_id] = commission_hub
        log CommissionHubCreated(chain_id=_chain_id, nft_contract=_nft_contract, token_id=_token_id, commission_hub=commission_hub)
    elif self.owners[_chain_id][_nft_contract][_token_id] != _owner:
        # If the owner is changing, we need to update the commission hub
        commission_hub: address = self.commissionHubs[_chain_id][_nft_contract][_token_id]
        commission_hub_instance: CommissionHub = CommissionHub(commission_hub)
        extcall commission_hub_instance.updateRegistration(_chain_id, _nft_contract, _token_id, _owner)

    # Update the owner and the last update timestamp
    self.owners[_chain_id][_nft_contract][_token_id] = _owner
    self.lastUpdated[_chain_id][_nft_contract][_token_id] = current_time
    
    log Registered(
        chain_id=_chain_id,
        nft_contract=_nft_contract, 
        token_id=_token_id, 
        owner=_owner, 
        commission_hub=self.commissionHubs[_chain_id][_nft_contract][_token_id],
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
def getCommissionHubByOwner(_chain_id: uint256, _nft_contract: address, _token_id: uint256) -> address:
    return self.commissionHubs[_chain_id][_nft_contract][_token_id]

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
def getEthereumCommissionHubByOwner(_nft_contract: address, _token_id: uint256) -> address:
    return self.commissionHubs[1][_nft_contract][_token_id]
    
# Set commission hub template
@external
def setCommissionHubTemplate(_new_template: address):
    assert msg.sender == self.owner, "Only owner can set commission hub template"
    self.commissionHubTemplate = _new_template

# Set L2 relay
@external
def setL2Relay(_new_l2relay: address):
    assert msg.sender == self.owner, "Only owner can set L2 relay"
    self.l2Relay = _new_l2relay
    


