# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.


# # EXACT INTEGRATION LOCATIONS FOR EXISTING CONTRACTS

# # ==========================================
# # Profile.vy - Line-by-line integration
# # ==========================================

# # 1. After line 47 (end of existing interfaces), ADD:
# interface CommissionEscrow:
#     def state() -> uint256: view
#     def commissioner() -> address: view
#     def artist() -> address: view
#     def escrow_amount() -> uint256: view
#     def has_funds() -> bool: view
#     def art_piece() -> address: view
#     def created_at() -> uint256: view
#     def accepted_at() -> uint256: view

# interface CommissionEscrowFactory:
#     def getArtistProposals(_artist: address, _offset: uint256, _count: uint256) -> DynArray[address, 50]: view
#     def getArtistEscrows(_artist: address, _offset: uint256, _count: uint256) -> DynArray[address, 50]: view
#     def getCommissionerEscrows(_commissioner: address, _offset: uint256, _count: uint256) -> DynArray[address, 50]: view
#     def getActiveProposalCount(_artist_profile: address) -> uint256: view

# # 2. After line 110 (after artSales1155 variable), ADD:
# commission_escrow_factory: public(address)

# # 3. After line 900, in linkArtPieceAsMyCommission method,
# # Right after the line "is_valid_profile_caller = (msg.sender == artist_profile or msg.sender == commissioner_profile)"
# # ADD this new check:
    
#     # Check if caller is a valid escrow contract
#     is_valid_escrow_caller: bool = False
#     if self.commission_escrow_factory != empty(address) and msg.sender != self.owner and msg.sender != self.profileFactoryAndRegistry and msg.sender != _art_piece:
#         try_escrow: CommissionEscrow = CommissionEscrow(msg.sender)
#         try:
#             escrow_artist: address = staticcall try_escrow.artist()
#             escrow_commissioner: address = staticcall try_escrow.commissioner()
#             escrow_art_piece: address = staticcall try_escrow.art_piece()
            
#             if escrow_art_piece == _art_piece and (escrow_artist == self.owner or escrow_commissioner == self.owner):
#                 is_valid_escrow_caller = True
#         except:
#             pass

# # 4. Update line 908 permission check FROM:
#     assert is_profile_owner or is_system or is_art_piece_self or is_valid_profile_caller, "No permission to add commission"
# # TO:
#     assert is_profile_owner or is_system or is_art_piece_self or is_valid_profile_caller or is_valid_escrow_caller, "No permission to add commission"

# # 5. After line 1850 (after getArtPiecesByOffset method), ADD all these methods:
# @external
# def setCommissionEscrowFactory(_factory: address):
#     """
#     @notice Set the commission escrow factory address (one time only)
#     @dev Can be called by owner or ProfileFactoryAndRegistry
#     """
#     assert msg.sender == self.owner or msg.sender == self.profileFactoryAndRegistry, "Not authorized"
#     assert self.commission_escrow_factory == empty(address), "Already set"
#     assert _factory != empty(address), "Invalid factory address"
#     self.commission_escrow_factory = _factory

# @external
# @view
# def getMyCommissionProposals(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
#     """
#     @notice Get commission proposals sent to this profile
#     @return List of escrow addresses
#     """
#     if self.commission_escrow_factory == empty(address):
#         return []
    
#     factory: CommissionEscrowFactory = CommissionEscrowFactory(self.commission_escrow_factory)
#     return staticcall factory.getArtistProposals(self.owner, _offset, _count)

# @external
# @view
# def getMyActiveEscrowsAsArtist(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
#     """
#     @notice Get active escrows where this profile owner is the artist
#     @return List of escrow addresses
#     """
#     if self.commission_escrow_factory == empty(address):
#         return []
    
#     factory: CommissionEscrowFactory = CommissionEscrowFactory(self.commission_escrow_factory)
#     return staticcall factory.getArtistEscrows(self.owner, _offset, _count)

# @external
# @view
# def getMyActiveEscrowsAsCommissioner(_offset: uint256, _count: uint256) -> DynArray[address, 50]:
#     """
#     @notice Get active escrows where this profile owner is the commissioner
#     @return List of escrow addresses
#     """
#     if self.commission_escrow_factory == empty(address):
#         return []
    
#     factory: CommissionEscrowFactory = CommissionEscrowFactory(self.commission_escrow_factory)
#     return staticcall factory.getCommissionerEscrows(self.owner, _offset, _count)

# @external
# @view
# def getPendingProposalCount() -> uint256:
#     """
#     @notice Get count of pending proposals for this profile
#     @return Number of proposals in PROPOSED state
#     """
#     if self.commission_escrow_factory == empty(address):
#         return 0
    
#     factory: CommissionEscrowFactory = CommissionEscrowFactory(self.commission_escrow_factory)
#     return staticcall factory.getActiveProposalCount(self)

# @external
# @view
# def getEscrowDetails(_escrow: address) -> (uint256, address, address, uint256, bool, address):
#     """
#     @notice Get details of an escrow contract
#     @param _escrow Address of the escrow contract
#     @return (state, commissioner, artist, amount, has_funds, art_piece)
#     """
#     escrow: CommissionEscrow = CommissionEscrow(_escrow)
#     return (
#         staticcall escrow.state(),
#         staticcall escrow.commissioner(),
#         staticcall escrow.artist(),
#         staticcall escrow.escrow_amount(),
#         staticcall escrow.has_funds(),
#         staticcall escrow.art_piece()
#     )

# # ==========================================
# # ProfileFactoryAndRegistry.vy - Integration
# # ==========================================

# # 1. After line 23 (after commissionHubTemplate declaration), ADD:
# commission_escrow_factory: public(address)

# # 2. After line 414 (after linkArtCommissionHubOwnersContract method), ADD:
# @external
# def linkCommissionEscrowFactory(_escrow_factory: address):
#     """
#     @notice Links the commission escrow factory to this registry
#     @dev Only owner can set this
#     @param _escrow_factory Address of the CommissionEscrowFactory contract
#     """
#     assert msg.sender == self.owner, "Only owner can set escrow factory"
#     assert _escrow_factory != empty(address), "Invalid factory address"
#     self.commission_escrow_factory = _escrow_factory

# # 3. In _createProfile method, after line 159 (after profile initialization):
# # Right after "extcall caller_profile_social_instance.initialize(_new_profile_address, caller_profile, self)"
# # ADD:
        
#         # If escrow factory is set, link it to the new profile
#         if self.commission_escrow_factory != empty(address):
#             extcall caller_profile_instance.setCommissionEscrowFactory(self.commission_escrow_factory)

# # ==========================================
# # OPTIONAL: ArtCommissionHub.vy - Integration
# # ==========================================

# # 1. After line 36 (after blacklist declaration), ADD:
# allowed_escrow_contracts: public(HashMap[address, bool])

# # 2. After line 250 (after submitCommission method), ADD:
# @external
# def allowEscrowContract(_escrow: address, _allow: bool):
#     """
#     @notice Allow an escrow contract to submit commissions directly
#     @dev Only hub owner can set this
#     """
#     art_commission_hub_owners_interface: ArtCommissionHubOwners = ArtCommissionHubOwners(self.artCommissionHubOwners)
#     assert staticcall art_commission_hub_owners_interface.isAllowedToUpdateHubForAddress(self, msg.sender), "Not allowed to update"
#     self.allowed_escrow_contracts[_escrow] = _allow

# # 3. In submitCommission method, around line 230,
# # After "is_whitelisted_commissioner: bool = self.whitelist[staticcall ArtPiece(_art_piece).getCommissioner()]"
# # ADD:
#     is_allowed_escrow: bool = self.allowed_escrow_contracts[msg.sender]

# # 4. Update the condition on line 234 FROM:
#     if sender_has_permission or is_whitelisted_artist or is_whitelisted_commissioner:
# # TO:
#     if sender_has_permission or is_whitelisted_artist or is_whitelisted_commissioner or is_allowed_escrow: