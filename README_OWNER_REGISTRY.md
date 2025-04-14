# L3 Owner Registry Explorer

This document provides information about the L3 OwnerRegistry contract deployment and how to use the Owner Registry Explorer UI.

## Contract Deployments

### Testnet (Arbitrum Sepolia)
- **L3 OwnerRegistry Contract**: `0x8A791620dd6260079BF849Dc5567aDC3F2FdC318`
- **L2 Relay Contract**: `0x3B809278Ba0267059e9641C22E7C7BA9C882E19A`

### Mainnet (Coming Soon)
- **L3 OwnerRegistry Contract**: TBD
- **L2 Relay Contract**: TBD

## Using the Owner Registry Explorer

The Owner Registry Explorer provides a user interface to interact with the OwnerRegistry contract's public getter methods and state variables.

### Available Queries

1. **Owner Lookup**: Query the registered owner of an NFT by contract address and token ID
   - Function: `lookupRegsiteredOwner(address nft_contract, uint256 token_id)`

2. **Commission Hub**: Query the commission hub address for an NFT by contract address and token ID
   - Function: `getCommissionHubByOwner(address nft_contract, uint256 token_id)`

3. **Last Updated**: Query when an NFT's ownership was last updated
   - Function: `getLastUpdated(address nft_contract, uint256 token_id)`

4. **L2 Relay Address**: Query the address of the L2 relay contract that can register owners
   - State Variable: `l2relay`

5. **Commission Hub Template**: Query the address of the template contract used to clone commission hubs
   - State Variable: `commission_hub_template`

6. **Contract Owner**: Query the owner of the OwnerRegistry contract
   - State Variable: `owner`

### How to Use the Explorer

1. Connect your wallet to Arbitrum Sepolia (testnet) or Arbitrum One (mainnet)
2. Use the "Load Contract Info" button to view basic contract information
3. Select a query type from the dropdown menu
4. For NFT-specific queries (Owner, Commission Hub, Last Updated), enter the NFT contract address and token ID
5. Click the "Query" button to execute your query

### Example Test Values (Testnet)

- **NFT Contract Address**: `0x3cF3dada5C03F32F0b77AAE7Ae19F61Ab89dbD06`
- **Token ID**: `1`

## Technical Overview

The OwnerRegistry contract is a Vyper contract deployed on Arbitrum L3 that tracks NFT ownership information. Key features:

- Records the owner of each NFT (contract/tokenId pair)
- Deploys a Commission Hub contract for each registered NFT
- Maintains a timestamp of when each NFT's ownership was last updated
- Only the L2 relay contract can register NFT owners

## Contract Source Code

The OwnerRegistry contract source code is available in the `contracts/OwnerRegistry.vy` file.

```vyper
# @version 0.4.1
# Function to handle owner verification on L3
# This takes in messages from the L2 and updates a registry of nft/id pairs to their owner
# This handles taking queries from other contracts on L3 and returning the owner of the NFT

l2relay: public(address)
commission_hub_template: public(address)
owner: public(address)
commission_hubs: public(HashMap[address, HashMap[uint256, address]])
owners: public(HashMap[address, HashMap[uint256, address]])
last_updated: public(HashMap[address, HashMap[uint256, uint256]])

# ...additional contract code...
```

## Integration

To integrate with the OwnerRegistry from another contract, use:

```solidity
interface IOwnerRegistry {
    function lookupRegsiteredOwner(address nft_contract, uint256 token_id) external view returns (address);
    function getCommissionHubByOwner(address nft_contract, uint256 token_id) external view returns (address);
    function getLastUpdated(address nft_contract, uint256 token_id) external view returns (uint256);
}

// In your contract:
IOwnerRegistry registry = IOwnerRegistry(REGISTRY_ADDRESS);
address owner = registry.lookupRegsiteredOwner(nftContract, tokenId);
``` 