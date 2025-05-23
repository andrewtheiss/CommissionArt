# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# Contains the image data for a commissioned piece
# Has a list of owners that have commissioned the piece
# Has a list of artists that have commissioned the piece
# Implements ERC721 for a single token NFT


#
# TODO - This is to be supported in the second phase....
#
#   This includes the following issues between the two art pieces 
# On-chain ArtPieces (ArtPiece.vy):
# Track whether they've ever been attached to a hub with everAttachedToHub
# Permanently block transfers if they've ever been attached with:
# Apply to ArtPieceOffC...
# "
# Once attached, the piece is permanently locked to the hub
# Off-chain ArtPieces (ArtPieceOffChain.vy):
# DO NOT have the everAttachedToHub variable
# Track current attachment status but not historical attachment
# Allow normal ERC721 transfers without restrictions
# No code prevents transfers even when attachedToArtCommissionHub is true
#
