# CommissionArt
Creating a community art commission platform 

# Token Bound Sub-NFT System for Commissioned Artwork

## Abstract
This proposal introduces a **Token Bound Sub-NFT System** designed to manage commissioned artwork tied to original NFTs (OG NFTs). The system allows artists to create sub-NFTs—representing commissioned pieces—that are verifiably linked to an OG NFT, ensuring authenticity and ownership alignment. Below are the key features, each with a detailed explanation:

- **Verification**: Sub-NFTs are approved by the OG NFT holder via cryptographic signatures. This ensures that only commissions explicitly authorized by the OG NFT owner are recognized as legitimate, fostering trust and preventing unauthorized derivatives.
- **Ownership Synchronization**: Sub-NFT ownership automatically updates when the OG NFT is transferred. This keeps commissioned artwork bound to the OG NFT, maintaining its value and context even as ownership changes hands.
- **Minting Copies**: Users can mint copies of verified sub-NFTs, with royalties distributed to the artist and commissioner. This incentivizes creation and sharing of high-quality artwork while rewarding both parties financially.
- **Scam Mitigation**: A registry ensures only approved contracts mint sub-NFTs, reducing fraud risks. This protects collectors from unwanted or fraudulent NFTs that could clutter or devalue their collections.

This system addresses the lack of standardization for commissioned NFT artwork by providing a secure, transparent, and user-friendly framework that benefits artists, commissioners, and collectors alike.

## Motivation
Commissioned artwork in the NFT space faces several challenges that this system aims to resolve. Here’s why this system is needed, with detailed reasoning:

- **Ownership Tracking**: It’s difficult to associate commissioned pieces with the OG NFT and ensure they transfer with it. Without a clear link, commissioned works can become detached, losing their significance and value. This system ensures sub-NFTs stay tied to the OG NFT across transfers.
- **Verification**: There’s no standard way to confirm that a sub-NFT is an authorized commission. This leads to uncertainty about authenticity, reducing trust. The system introduces a cryptographic verification process to guarantee legitimacy.
- **Royalties**: Artists and commissioners often struggle to agree on and enforce royalty splits. Disputes or unclear terms can discourage collaboration. This system automates royalty distribution, ensuring fair and transparent compensation.
- **Scams**: Unwanted or fraudulent NFTs can clutter collections, diminishing their value and user experience. Without controls, malicious actors can exploit the ecosystem. The system mitigates this through a registry and optional reputation mechanisms.

The intention is to create a structured ecosystem where sub-NFTs are verifiably tied to OG NFTs, ownership is seamlessly synchronized, royalties are transparently managed, and scams are minimized—ultimately enhancing trust and usability in the NFT commission space.

## Specification
The system consists of six main components, each designed with a specific purpose and set of behaviors to form a cohesive framework. Below is an overview of each, with their roles clearly defined:

1. **Sub-NFT Contract**: Manages the creation, metadata, and verification of sub-NFTs. This is the foundation for minting and tracking commissioned artwork.
2. **Verification Mechanism**: Ensures sub-NFTs are approved by the OG NFT holder. This establishes authenticity and trust in the system.
3. **Registry Contract**: Tracks approved sub-NFT contracts to prevent unauthorized minting. This acts as a gatekeeper against fraud.
4. **Ownership Synchronization**: Aligns sub-NFT ownership with the OG NFT’s owner. This keeps commissioned works tied to their origin.
5. **Minting and Royalties**: Allows minting of sub-NFT copies with royalty distribution. This rewards creators and encourages wider distribution.
6. **Scam Mitigation**: Implements safeguards like registry approval and reputation systems. This protects the ecosystem’s integrity.

Each component is interconnected, working together to create a secure, efficient, and transparent environment for commissioned artwork in the NFT space.

## Overall Design
The **Token Bound Sub-NFT System** operates as a holistic solution with the following workflow, detailed for clarity:

- **Sub-NFTs** are minted in dedicated contracts, each linked to a specific OG NFT (identified by its contract address and token ID). This ensures every sub-NFT has a clear origin, making it easy to trace back to the OG NFT.
- A **Registry Contract** maintains a list of approved sub-NFT contracts for each OG NFT, ensuring only authorized contracts can create sub-NFTs. This prevents rogue contracts from flooding the system with unapproved works.
- The OG NFT holder verifies sub-NFTs using a cryptographic signature, marking them as legitimate commissions. This step confirms authenticity, giving collectors confidence in their value.
- When the OG NFT is transferred, sub-NFT ownership is automatically updated to the new holder, keeping the commissioned artwork bound to the OG NFT. This automation simplifies ownership management and preserves the relationship between the assets.
- Users can mint copies of verified sub-NFTs, with royalties automatically split between the artist and the commissioner (OG NFT holder). This creates a revenue stream while promoting the artwork’s reach.
- **Scam Mitigation** is enforced through the registry, ensuring only approved contracts mint sub-NFTs, and optional reputation systems to filter low-quality content. This maintains the system’s credibility and user trust.

The purpose of this design is to ensure that commissioned artwork remains valuable, transferable, and secure within the NFT ecosystem, with clear effects: increased trust, streamlined processes, and fair compensation.

## Detailed Breakdown

### 1. Sub-NFT Contract
The Sub-NFT Contract is the core component for creating and managing sub-NFTs. Each sub-NFT is uniquely tied to an OG NFT and includes metadata about the artist and commissioner.

#### 1.1. Purpose
- **Intention**: To provide a standardized way to mint and track commissioned artwork as NFTs, ensuring consistency across the ecosystem.
- **Goal**: To store essential metadata (e.g., artist, commissioner, verification status) in a structured format, making sub-NFTs easily identifiable and verifiable.

#### 1.2. Behaviors
- **Linking**: Each sub-NFT is associated with a specific OG NFT via its contract address and token ID, creating a permanent connection that’s visible on-chain.
- **Metadata**: Stores detailed information about the artist (e.g., address) and commissioner (OG NFT holder), alongside a token URI pointing to the artwork.
- **Verification**: Allows the OG NFT holder to mark sub-NFTs as verified using a signature, signaling to the ecosystem that they are legitimate commissions.

#### 1.3. Key Functions
| Function                          | Description                                      |
|-----------------------------------|--------------------------------------------------|
| `mintSubNFT(address to, string memory tokenURI, address artist)` | Mints a new sub-NFT to a specified address (e.g., the commissioner) with metadata like the token URI (artwork link) and artist address. This initiates the sub-NFT’s lifecycle. |
| `verifySubNFT(uint256 tokenId, bytes memory signature)`          | Verifies a sub-NFT using a cryptographic signature from the OG NFT holder, updating its `verified` status to true. This confirms its authenticity. |
| `revokeVerification(uint256 tokenId)`                            | Revokes the verification status of a sub-NFT, restricted to the OG NFT holder. This allows disassociation from unwanted sub-NFTs. |

#### 1.4. Technical Notes
- Built on ERC-721 or ERC-1155 standards for compatibility with wallets, marketplaces, and other NFT platforms.
- Uses EIP-712 for structured, secure signature verification, ensuring signatures are tamper-proof and user-friendly.
- Stores `ogNFTContract` (address) and `ogNFTTokenId` (uint256) as immutable references to the OG NFT, ensuring a reliable link.

#### 1.5. Effects
- Artists and commissioners benefit from a clear, standardized process for creating sub-NFTs.
- Collectors trust verified sub-NFTs as authentic, increasing their marketability and value.

### 2. Verification Mechanism
The Verification Mechanism ensures that sub-NFTs are explicitly approved by the OG NFT holder, establishing trust and authenticity.

#### 2.1. Purpose
- **Intention**: To confirm that a sub-NFT is a legitimate commission, authorized by the OG NFT holder, preventing unauthorized derivatives.
- **Goal**: To provide a way for the OG NFT holder to revoke approval if the sub-NFT no longer meets their standards or was minted fraudulently.

#### 2.2. Behaviors
- Requires a cryptographic signature from the OG NFT holder to verify a sub-NFT, ensuring only the rightful owner can approve it.
- Allows the OG NFT holder to revoke verification, removing the sub-NFT’s approved status and signaling it’s no longer endorsed.

#### 2.3. Implementation Example
```solidity
function verifySubNFT(uint256 tokenId, bytes memory signature) external {
    address ogOwner = IERC721(ogNFTContract).ownerOf(ogNFTTokenId);
    bytes32 messageHash = keccak256(abi.encodePacked(tokenId, address(this), nonce));
    bytes32 ethSignedMessageHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash));
    require(ecrecover(ethSignedMessageHash, v, r, s) == ogOwner, "Invalid signature");
    verified[tokenId] = true;
}
```
### Signature Validation and Nonce

#### Signature Validation
Uses ecrecover to confirm that the signature matches the OG NFT holder’s address, ensuring the security of the verification process.

#### Nonce
Incorporates a unique nonce in the signed message to prevent replay attacks, enhancing the reliability of the system.

#### Effects
Verified sub-NFTs gain credibility, making them more appealing to collectors and increasing their perceived value.  
Revocation empowers OG NFT holders to maintain control over their collection’s integrity, reducing the impact of scams or poor-quality commissions.

### Registry Contract
The Registry Contract manages which sub-NFT contracts are approved to mint sub-NFTs for a given OG NFT.

#### Purpose
**Intention:** To prevent unauthorized or scam sub-NFT contracts from minting sub-NFTs linked to an OG NFT, protecting the ecosystem’s integrity.  
**Goal:** To give the OG NFT holder control over which contracts can create sub-NFTs, ensuring only trusted sources are used.

#### Behaviors
Maintains a mapping of OG NFTs (identified by contract address and token ID) to their approved sub-NFT contracts, functioning as a whitelist.  
Allows the OG NFT holder to add or remove sub-NFT contracts from the registry, providing flexibility and control.

#### Key Functions
**Function** | **Description**  
registerSubContract(address ogNFTContract, uint256 ogNFTTokenId, address subNFTContract) | Adds a sub-NFT contract to the approved list for a specific OG NFT, enabling it to mint sub-NFTs.  
unregisterSubContract(address ogNFTContract, uint256 ogNFTTokenId, address subNFTContract) | Removes a sub-NFT contract from the approved list, blocking further minting from that contract.  
getSubContracts(address ogNFTContract, uint256 ogNFTTokenId) | Returns the list of approved sub-NFT contracts for an OG NFT, aiding transparency and discovery.

#### Technical Notes
Utilizes nested mappings (e.g., mapping(address => mapping(uint256 => address[]))) for efficient storage and retrieval of approved contracts.  
Implements access control to ensure only the OG NFT holder can modify the registry, preventing unauthorized changes.

#### Effects
Reduces the risk of fraudulent sub-NFTs by restricting minting to approved contracts, enhancing user trust.  
Empowers OG NFT holders to curate their ecosystem, ensuring only high-quality or desired commissions are linked.

### Ownership Synchronization
This component ensures that sub-NFTs remain tied to the OG NFT’s owner, even after the OG NFT is transferred.

#### Purpose
**Intention:** To maintain the binding between the OG NFT and its commissioned sub-NFTs across ownership changes, preserving their relationship.  
**Goal:** To automate the transfer of sub-NFTs to the new OG NFT owner, reducing manual effort and errors.

#### Behaviors
Detects when the OG NFT is transferred (via Transfer events) and updates sub-NFT ownership to match the new owner.  
Supports batch transfers for efficiency, particularly when an OG NFT has multiple associated sub-NFTs.

#### Technical Notes
Can use an off-chain listener to monitor Transfer events from the OG NFT contract and trigger sub-NFT transfers automatically.  
Alternatively, integrates with ERC-6551 Token Bound Accounts (TBAs) to delegate control of sub-NFTs to the OG NFT, streamlining transfers.

#### Effects
Ensures commissioned artwork remains with the OG NFT, preserving its value and context for collectors.  
Simplifies the user experience by automating ownership updates, making the system more accessible and efficient.

### Minting and Royalties
This component allows users to mint copies of verified sub-NFTs, with royalties distributed to the artist and commissioner.

#### Purpose
**Intention:** To enable broader distribution of commissioned artwork while rewarding creators financially.  
**Goal:** To provide a revenue stream for artists and commissioners through minting fees and secondary sales, encouraging collaboration.

#### Behaviors
Any user can mint a copy of a verified sub-NFT by paying a fee, making the artwork accessible to a wider audience.  
Royalties from minting and secondary sales are split between the artist and commissioner (e.g., 70% artist, 30% commissioner), with configurable rates.

#### Key Functions
**Function** | **Description**  
mintCopy(uint256 tokenId, address recipient) | Mints a copy of a verified sub-NFT to the recipient, distributing royalties to the artist and commissioner.

#### Technical Notes
Employs a royalty splitter contract to automatically divide fees between the artist and commissioner, ensuring transparency.  
Supports dynamic royalty rates (e.g., based on sales volume or price) for flexibility and fairness.

#### Effects
Artists are incentivized to create high-quality commissions, knowing they’ll earn from copies and secondary sales.  
Commissioners benefit from a share of royalties, encouraging them to commission more artwork and promote its distribution.

### Scam Mitigation
This component reduces the risk of fraudulent or unwanted sub-NFTs, protecting users and the ecosystem.

#### Purpose
**Intention:** To protect users from scam sub-NFTs that could devalue or clutter their collections, maintaining ecosystem quality.  
**Goal:** To ensure only legitimate, approved sub-NFTs are associated with OG NFTs, fostering trust and reliability.

#### Features
**Registry Approval:** Only sub-NFTs from registered contracts can be minted, serving as a primary defense against fraud.  
**Reputation System:** Optional ratings or reviews for sub-NFTs, helping users identify and filter low-quality or suspicious content.  
**Whitelists:** Potential for trusted artist lists or DAO governance to approve contracts, adding an extra layer of curation.

#### Effects
Increases trust in the system by reducing scam risks, making it safer for collectors and creators.  
Enhances the overall quality and value of commissioned artwork by filtering out unwanted or fraudulent entries.

### Conclusion
The Token Bound Sub-NFT System provides a comprehensive solution for managing commissioned artwork in the NFT ecosystem. By integrating verification, ownership synchronization, royalty distribution, and scam mitigation, it creates a secure, transparent, and rewarding environment for artists, commissioners, and collectors. Key effects include:  
**Trust:** Verification and scam mitigation ensure authenticity and safety.  
**Efficiency:** Ownership synchronization and automated royalties streamline processes.  
**Value:** Fair compensation and standardized tracking enhance the appeal of commissioned artwork.  

This system is designed to be scalable, compatible with existing NFT standards (e.g., ERC-721, ERC-1155), and adaptable to future enhancements, making it a robust foundation for the evolving NFT space.
