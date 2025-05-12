# Art Commissioning NFT Transfer Behavior

## Core Design Philosophy

The Art Commissioning system implements a specialized NFT model with a critical difference from standard ERC721 tokens: **once an Art Piece is attached to an Art Commission Hub, the hub permanently controls ownership determination.**

This document explains the rationale, behavior, and implications of this design decision.

## Permanent Hub Relationship

### How It Works

1. When an Art Piece is first created, it can be transferred like a normal NFT by its direct owner.
2. Once the Art Piece is attached to an Art Commission Hub, a **permanent relationship** is established.
3. After attachment, the following rules apply:
   * The `everAttachedToHub` flag is permanently set to `True`
   * The `permanentHubAddress` is set to the first hub the piece is attached to
   * **All transfers through standard ERC721 methods are blocked**
   * Ownership of the Art Piece is **always** determined by the owner of the hub

### Why Block Transfers?

This design intentionally prevents standard ERC721 transfers for hub-attached art pieces because:

1. **Clarity of Ownership**: The hub owner is always the effective owner, so direct transfers would create confusion
2. **Collection Integrity**: Art pieces in a collection should move together as the hub changes ownership
3. **Consistent Behavior**: The effective owner is always determined by `checkOwner()`, not the direct ERC721 owner

## Ownership Determination

The `checkOwner()` method is the single source of truth for determining the effective owner of an Art Piece:

```vyper
@view
def checkOwner() -> address:
    if self.everAttachedToHub and self.permanentHubAddress != empty(address):
        return staticcall ArtCommissionHub(self.permanentHubAddress).owner()
    return self.owner
```

This means:
* If an Art Piece was ever attached to a hub, the hub's owner is the effective owner
* If an Art Piece was never attached to a hub, the direct ERC721 owner is the effective owner

## Attachment and Detachment

### Attaching to a Hub

* Can only be done once the piece is not already attached
* Only the direct owner or artist can attach a piece to a hub
* Sets both the current attachment status and the permanent relationship

### Detaching from a Hub

* Can only be done by the hub owner
* Only affects the current attachment status
* **Does not break the permanent relationship** - ownership is still determined by the hub

## Intended NFT Transfer Behavior

1. **Never-Attached Pieces**: Can be transferred directly by their owner using standard ERC721 methods
2. **Ever-Attached Pieces**: Cannot be transferred directly - ownership is determined by the hub
3. **Changing Ownership**: To change ownership of an attached Art Piece, transfer ownership of the hub

## Implications for ERC721 Compliance

While our implementation is ERC721-compatible for interface detection, it intentionally:

1. Disables approvals and operator approvals
2. Blocks standard transfer methods for attached pieces
3. Uses a specialized ownership model different from standard ERC721

## Use Case Examples

### Collection Management

Alice creates a collection of 10 Art Pieces and attaches them to her Art Commission Hub. Later, she sells the hub to Bob. All 10 pieces automatically recognize Bob as their effective owner, even if some have been detached from the hub.

### NFT Marketplace Integration

When integrating with NFT marketplaces:
* The Hub itself can be sold as an NFT
* Individual Art Pieces that were ever attached to a hub cannot be sold directly
* Art Pieces never attached to a hub can be sold directly

## Security Considerations

* The permanent hub relationship is immutable by design
* There is no way to "un-attach" a piece once it has been attached
* Hub ownership is the only way to control ownership of attached pieces

## Summary

The permanent hub relationship provides a clean model for collection-based ownership that simplifies the management of art pieces. While it differs from standard NFT behavior, it creates a coherent model where ownership flows from the hub to all attached pieces, both now and in the future. 