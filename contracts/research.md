Background and Context
The user is developing an application on AnimeChain, an L3 chain built using Arbitrum Orbit, which settles on Arbitrum (L2), itself an L2 rollup on Ethereum (L1). The app mints commission NFTs on L3, linked to parent NFTs on L1 (Ethereum), and needs to verify the L1 NFT owner to update the L3-linked NFT’s owner. The user prefers avoiding third-party oracles like Chainlink, is fine with user-triggered processes, and favors Vyper for contract development to reduce code complexity over time.
Given the layered architecture (L1 → L2 → L3), cross-chain messaging is essential. Arbitrum provides mechanisms for L2-to-L1 and L1-to-L2 communication, and Arbitrum Orbit likely extends this for L3-to-L2 and L2-to-L3 messaging, leveraging the Nitro tech stack for security and scalability.

Technical Solution: Cross-Chain Messaging Approach
The solution involves deploying contracts on each layer to facilitate trustless communication:
L1 Contract (Ethereum): Queries the NFT owner and sends the result back to L2.

L2 Contract (Arbitrum): Acts as a relay, forwarding requests from L3 to L1 and results back to L3.

L3 Contract (AnimeChain): Initiates the request and updates based on the response.

This flow ensures no reliance on external oracles, aligning with the user’s preference for decentralization.
L1 Contract Implementation
The L1 contract, written in Vyper, queries the NFT owner using the ERC721 ownerOf function and sends the result back to L2 via the Arbitrum Inbox contract. The Inbox contract, located at 0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f on Ethereum, facilitates L1-to-L2 messaging using createRetryableTicket.



** 
L1 Contract Implementation
The L1 contract, written in Vyper, queries the NFT owner using the ERC721 ownerOf function and sends the result back to L2 via the Arbitrum Inbox contract. The Inbox contract, located at 0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f on Ethereum, facilitates L1-to-L2 messaging using createRetryableTicket.

L2 Contract Implementation
The L2 contract, also in Vyper, handles messaging to L1 via the ArbSys precompile at 0x0000000000000000000000000000000000000064 and to L3 via an assumed OrbitMessenger. Vyper’s ability to interact with precompiles was confirmed through documentation, supporting calls like sendTxToL1.

