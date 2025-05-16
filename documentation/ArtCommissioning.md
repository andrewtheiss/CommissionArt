# Art Commissioning System Documentation

## Overview

The Art Commissioning System consists of several smart contracts that work together to manage the creation, ownership, and transfer of art pieces in a blockchain-based marketplace. This document focuses on the relationship between ArtPiece contracts and the ArtCommissionHub contract, which is critical to understand how ownership is determined and managed.

## Permanent Commission Hub Relationship

A key concept in this system is the **permanent relationship** between an Art Piece and an Art Commission Hub:

1. When an Art Piece is first attached to a Commission Hub, this establishes a permanent relationship.
2. Even if the Art Piece is later detached from the Hub, the Hub remains the ultimate authority for determining ownership.
3. This means that if ownership of the Commission Hub changes, the effective ownership of all Art Pieces ever attached to it also changes, regardless of their current attached status.

## ArtPiece Contract

### Ownership Model

The ArtPiece contract implements the ERC721 standard with important modifications:

- Each ArtPiece has a direct owner (`self.owner`), which is typically set during initialization
- If an ArtPiece is attached to a Commission Hub, the effective owner is the owner of that Hub
- Once attached to a Hub, the Hub's owner is ALWAYS considered the owner, even if detached later

### Critical Variables

- `owner`: The direct owner of the Art Piece (for ERC721 compatibility)
- `attachedToArtCommissionHub`: Boolean flag indicating if the piece is currently attached to a hub
- `artCommissionHubAddress`: The address of the currently attached hub (if any)
- `everAttachedToHub`: Boolean flag indicating if the piece was ever attached to a hub
- `permanentHubAddress`: The address of the first hub the piece was attached to (never changes once set)

### Key Methods

#### `checkOwner()`

This critical method determines the effective owner of an Art Piece:

```
def checkOwner() -> address:
    if self.everAttachedToHub and self.permanentHubAddress != empty(address):
        return staticcall ArtCommissionHub(self.permanentHubAddress).owner()
    return self.owner
```

The logic is straightforward:
- If the piece was ever attached to a hub, return the current owner of that hub
- Otherwise, return the direct owner

#### `attachToArtCommissionHub(_commission_hub: address)`

This method allows attaching an Art Piece to a Commission Hub:

- Can only be called by the direct owner or artist
- Cannot be attached if already attached to a hub
- Sets both the current hub address and, if this is the first attachment, the permanent hub address

#### `detachFromArtCommissionHub()`

This method allows detaching an Art Piece from its current Commission Hub:

- Can only be called by the effective owner (as determined by `checkOwner()`)
- Only affects the `attachedToArtCommissionHub` flag and `artCommissionHubAddress`
- Does NOT change the `permanentHubAddress` or `everAttachedToHub` flag

### Transfer Restrictions

Unlike standard ERC721 tokens, Art Pieces have strict transfer restrictions:

1. Only the effective owner (as determined by `checkOwner()`) can transfer an Art Piece
2. Approvals and operator approvals are disabled
3. The `safeTransferFrom` and `transferFrom` methods check the effective owner rather than relying on standard approval checks

## ArtCommissionHub Contract

The ArtCommissionHub acts as a collection manager for Art Pieces. Key properties:

- It has a single owner who has authority over all attached Art Pieces
- When ownership of the Hub changes, the effective ownership of all Art Pieces (current and previously attached) also changes
- It serves as a permanent reference point for ownership checking

## Integration with Other Contracts

The system is designed to be compatible with ERC6551 token-bound accounts, allowing:

1. NFT collections to be represented as on-chain entities with their own storage and actions
2. Ownership propagation from L1 chains to L2 chains through the ArtCommissionHubOwners
3. Batch management of art pieces through a single Commission Hub

## Usage Examples

### For Artists

1. Create an Art Piece with yourself as both artist and owner
2. Later attach it to a Commission Hub when ready to sell/transfer
3. Once attached, ownership will always be determined by the Hub owner

### For Commissioners

1. Acquire ownership of a Commission Hub
2. The Hub gives you effective ownership of all Art Pieces ever attached to it
3. You can detach pieces from the Hub, but ownership determination still goes through the Hub

## Security Considerations

1. The permanent hub relationship means that ownership determination is immutable once a piece is attached to a hub
2. Detaching a piece from a hub does not break the ownership determination path
3. The hub owner always maintains control over all pieces ever attached to the hub
4. Standard transfer and approval mechanisms are disabled to enforce this ownership model

## Important Notes

- Understanding the `checkOwner()` method is crucial for comprehending how ownership is determined
- The permanent relationship with the first hub an Art Piece is attached to is by design and cannot be changed
- This model enables collection-based ownership that can be managed at the hub level, simplifying operations for large collections
