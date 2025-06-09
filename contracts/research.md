Background and Context
The user is developing an application on AnimeChain, an L3 chain built using Arbitrum Orbit, which settles on Arbitrum (L2), itself an L2 rollup on Ethereum (L1). The app mints commission NFTs on L3, linked to parent NFTs on L1 (Ethereum), and needs to verify the L1 NFT owner to update the L3-linked NFT's owner. The user prefers avoiding third-party oracles like Chainlink, is fine with user-triggered processes, and favors Vyper for contract development to reduce code complexity over time.
Given the layered architecture (L1 → L2 → L3), cross-chain messaging is essential. Arbitrum provides mechanisms for L2-to-L1 and L1-to-L2 communication, and Arbitrum Orbit likely extends this for L3-to-L2 and L2-to-L3 messaging, leveraging the Nitro tech stack for security and scalability.

Technical Solution: Cross-Chain Messaging Approach
The solution involves deploying contracts on each layer to facilitate trustless communication:
L1 Contract (Ethereum): Queries the NFT owner and sends the result back to L2.

L2 Contract (Arbitrum): Acts as a relay, forwarding requests from L3 to L1 and results back to L3.

L3 Contract (AnimeChain): Initiates the request and updates based on the response.

This flow ensures no reliance on external oracles, aligning with the user's preference for decentralization.
L1 Contract Implementation
The L1 contract, written in Vyper, queries the NFT owner using the ERC721 ownerOf function and sends the result back to L2 via the Arbitrum Inbox contract. The Inbox contract, located at 0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f on Ethereum, facilitates L1-to-L2 messaging using createRetryableTicket.



** 
L1 Contract Implementation
The L1 contract, written in Vyper, queries the NFT owner using the ERC721 ownerOf function and sends the result back to L2 via the Arbitrum Inbox contract. The Inbox contract, located at 0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f on Ethereum, facilitates L1-to-L2 messaging using createRetryableTicket.

L2 Contract Implementation
The L2 contract, also in Vyper, handles messaging to L1 via the ArbSys precompile at 0x0000000000000000000000000000000000000064 and to L3 via an assumed OrbitMessenger. Vyper's ability to interact with precompiles was confirmed through documentation, supporting calls like sendTxToL1.


# https://docs.arbitrum.io/how-arbitrum-works/l1-to-l2-messaging
# https://docs.arbitrum.io/build-decentralized-apps/reference/contract-addresses 

## Animechain Testnet Deployment Strategy

### Network Architecture
The Animechain development network follows a three-layer architecture for testing the complete cross-chain functionality:

- **L1 (Ethereum Sepolia)**: Deploys L1QueryOwnership contract for NFT ownership verification
- **L2 (Arbitrum Sepolia)**: Deploys L2OwnershipRelay contract for cross-chain message routing
- **L3 (Animechain Testnet)**: Deploys all application logic contracts including templates and factories

### Animechain Testnet Configuration
The Animechain testnet is built on Conduit infrastructure with the following parameters:

- **Chain ID**: 6900
- **RPC Endpoint**: `https://rpc-animechain-testnet-i8yja6a1a0.t.conduit.xyz`
- **Block Explorer**: `https://explorer-animechain-testnet-i8yja6a1a0.t.conduit.xyz/`
- **Native Token**: Animecoin (ANIME)
- **Architecture**: Arbitrum Orbit L3 settling to Arbitrum Sepolia

### Contract Deployment Distribution
The deployment strategy isolates cross-chain infrastructure from application logic:

**L3 (Animechain Testnet) Contracts:**
- `ArtCommissionHubOwners` - Main registry and ownership management
- `ArtCommissionHub` (template) - Commission hub template for cloning
- `ArtPiece` (template) - NFT template for art pieces
- `Profile` (template) - User profile template
- `ProfileSocial` (template) - Social features template
- `ProfileFactoryAndRegistry` - Factory for creating user profiles
- `ArtEdition1155` (template) - ERC-1155 art edition template
- `ArtSales1155` (template) - Sales contract template

**L2 (Arbitrum Sepolia) Contracts:**
- `L2OwnershipRelay` - Cross-chain message relay between L1 and L3

**L1 (Ethereum Sepolia) Contracts:**
- `L1QueryOwnership` - NFT ownership verification and L1-to-L2 messaging

### Development Benefits
1. **Cost Efficiency**: Primary application logic runs on L3 with minimal gas costs
2. **Testing Fidelity**: Full cross-chain message testing without mainnet costs
3. **Rapid Iteration**: Fast deployment cycle for contract updates on testnet
4. **Cross-Chain Validation**: End-to-end testing of L1 → L2 → L3 messaging flows

### Deployment Automation
The `deploy_testnet.py` script automates the complete three-layer deployment:
- Automatically configures network connections for each layer
- Establishes bidirectional contract linking (L2 ↔ L3)
- Registers L1 contract in L2 relay for cross-chain communication
- Validates deployment integrity across all three networks

This approach enables comprehensive testing of the commission art platform while maintaining separation of concerns between cross-chain infrastructure and application business logic. 