# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# ArtPieceLicense contract - handles licensing and rights management for ArtPiece
# This contract can override ownership determination for rights management purposes

# State variables
artPiece: public(address)  # The ArtPiece this license is attached to
licenseOwner: public(address)  # The owner according to the license
initialized: public(bool)

@deploy
def __init__():
    pass

@external
def initialize(_art_piece: address, _license_owner: address):
    """
    @notice Initialize the ArtPieceLicense contract
    @param _art_piece The ArtPiece contract this license is for
    @param _license_owner The owner according to the license
    """
    assert not self.initialized, "Already initialized"
    assert _art_piece != empty(address), "Invalid ArtPiece address"
    assert _license_owner != empty(address), "Invalid license owner"
    
    self.artPiece = _art_piece
    self.licenseOwner = _license_owner
    self.initialized = True

@external
@view
def getOwner() -> address:
    """
    @notice Get the owner according to the license
    @return The license owner address
    """
    return self.licenseOwner

@external
def setLicenseOwner(_new_owner: address):
    """
    @notice Set a new license owner
    @param _new_owner The new license owner
    """
    assert self.initialized, "Not initialized"
    assert _new_owner != empty(address), "Invalid owner address"
    assert msg.sender == self.licenseOwner, "Only current license owner can change ownership"
    
    self.licenseOwner = _new_owner
