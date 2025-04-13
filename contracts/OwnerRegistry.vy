# @version 0.4.1
# Function to handle owner verification on L3
# This takes in messages from the L2 and updates a registry of nft/id pairs to their owner
# This handles taking queries from other contracts on L3 and returning the owner of the NFT

# Need to double check storage variables
l2relay: public(address)
commission_hub_template: public(address)
owner: public(address)
commission_hubs: public(HashMap[address, HashMap[uint256, address]])
owners: public(HashMap[address, HashMap[uint256, address]])

interface CommissionHub:
    def initialize(nft_contract: address, token_id: uint256, registry: address): nonpayable
    def updateRegistration(nft_contract: address, token_id: uint256, owner: address): nonpayable

event Registered:
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    owner: address
    commission_hub: address

event CommissionHubCreated:
    nft_contract: indexed(address)
    token_id: indexed(uint256)
    commission_hub: address

@deploy
def __init__(initial_l2relay: address, initial_commission_hub_template: address):
    self.l2relay = initial_l2relay
    self.commission_hub_template = initial_commission_hub_template
    self.owner = msg.sender

#Called by L2Relay when ownership is verified, taking nft_contract, token_id, and owner as parameters.
@external
def registerNFTOwnerFromParentChain(nft_contract: address, token_id: uint256, owner: address):
    # Only allow registration from L2Relay
    assert msg.sender == self.l2relay, "Only L2Relay can register NFT owners"

    # If the commission hub doesn't exist, create it
    if self.owners[nft_contract][token_id] == empty(address):
        commission_hub: address = create_minimal_proxy_to(self.commission_hub_template)
        commission_hub_instance: CommissionHub = CommissionHub(commission_hub)
        extcall commission_hub_instance.initialize(nft_contract, token_id, self)
        self.commission_hubs[nft_contract][token_id] = commission_hub
        log CommissionHubCreated(nft_contract=nft_contract, token_id=token_id, commission_hub=commission_hub)
    elif self.owners[nft_contract][token_id] != owner:
        # If the owner is changing, we need to update the commission hub
        commission_hub: address = self.commission_hubs[nft_contract][token_id]
        commission_hub_instance: CommissionHub = CommissionHub(commission_hub)
        extcall commission_hub_instance.updateRegistration(nft_contract, token_id, owner)

    self.owners[nft_contract][token_id] = owner
    log Registered(nft_contract=nft_contract, token_id=token_id, owner=owner, commission_hub=self.commission_hubs[nft_contract][token_id])

#Called by other contracts on L3 to query the owner of an NFT
@view
@external
def lookupRegsiteredOwner(nft_contract: address, token_id: uint256) -> address:
    return self.owners[nft_contract][token_id]

@view
@external
def getCommissionHubByOwner(nft_contract: address, token_id: uint256) -> address:
    return self.commission_hubs[nft_contract][token_id]

    
# Set commission hub template
@external
def setCommissionHubTemplate(new_template: address):
    assert msg.sender == self.owner, "Only owner can set commission hub template"
    self.commission_hub_template = new_template

# Set L2 relay
@external
def setL2Relay(new_l2relay: address):
    assert msg.sender == self.owner, "Only owner can set L2 relay"
    self.l2relay = new_l2relay
    


