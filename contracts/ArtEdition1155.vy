# @version 0.4.1

# Copyright (c) 2025 Andrew Theiss
# This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
# 
# Permission is hereby granted to use, share, and modify this code for non-commercial purposes only,
# provided that appropriate credit is given to the original author.
# For commercial use, please contact the author for permission.

# ArtEdition1155: ERC1155 implementation for art piece editions
# Enhanced with flexible sale management and phased pricing
# SIMPLIFIED: Each contract handles exactly ONE token (ID 1) representing one art piece edition

from ethereum.ercs import IERC165

implements: IERC165

# ERC1155 Events
event TransferSingle:
    operator: indexed(address)
    sender: indexed(address)
    receiver: indexed(address)
    id: uint256
    value: uint256

event TransferBatch:
    operator: indexed(address)
    sender: indexed(address)
    receiver: indexed(address)
    ids: DynArray[uint256, 100]
    values: DynArray[uint256, 100]

event ApprovalForAll:
    owner: indexed(address)
    operator: indexed(address)
    approved: bool

event URI:
    value: String[2500]
    id: indexed(uint256)

# Custom Events
event EditionMinted:
    minter: indexed(address)
    amount: uint256
    payment: uint256

event PriceUpdated:
    oldPrice: uint256
    newPrice: uint256

event SaleStarted:
    saleType: uint256

event SalePaused:
    paused: bool

event SaleResumed:
    resumed: bool

event PhaseChanged:
    newPhase: uint256
    newPrice: uint256

# State Variables
initialized: public(bool)
artSales1155: public(address)
artPiece: public(address)
owner: public(address)
proceedsAddress: public(address)
paymentCurrency: public(address)

# Token metadata
name: public(String[100])
symbol: public(String[10])

# ERC1155 Storage - only for token ID 1
balances: public(HashMap[address, uint256])  # Simplified: owner -> balance (only token ID 1)
operatorApprovals: public(HashMap[address, HashMap[address, bool]])

# Edition Configuration - single token only
currentPrice: public(uint256)
basePrice: public(uint256)
maxSupply: public(uint256)
currentSupply: public(uint256)
isPaused: public(bool)
royaltyPercent: public(uint256)
saleType: public(uint256)
saleStartTime: public(uint256)
phases: public(DynArray[PhaseConfig, 5])
currentPhase: public(uint256)

# Sale Types
SALE_TYPE_FOREVER: constant(uint256) = 0      # No deadline, mint forever
SALE_TYPE_CAPPED: constant(uint256) = 1       # Stop after maxSupply reached
SALE_TYPE_QUANTITY_PHASES: constant(uint256) = 2  # Price increases based on quantity sold
SALE_TYPE_TIME_PHASES: constant(uint256) = 3      # Price increases based on time

# Phase Configuration
struct PhaseConfig:
    threshold: uint256  # Quantity threshold for QUANTITY_PHASES, timestamp for TIME_PHASES
    price: uint256

# Constants
MAX_ROYALTY_PERCENT: constant(uint256) = 10000  # Allow up to 100.00% (10000 basis points)
MAX_PHASES: constant(uint256) = 5
TOKEN_ID: constant(uint256) = 1  # Always use token ID 1

# Interfaces
interface IERC20:
    def transfer(_to: address, _value: uint256) -> bool: nonpayable
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable
    def balanceOf(_owner: address) -> uint256: view
    def allowance(_owner: address, _spender: address) -> uint256: view

interface IERC20Permit:
    def permit(_owner: address, _spender: address, _value: uint256, _deadline: uint256, _v: uint8, _r: bytes32, _s: bytes32): nonpayable
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable

interface ArtPiece:
    def getTokenURIData() -> Bytes[45000]: view
    def getTitle() -> String[100]: view
    def getDescription() -> String[400]: view
    def getArtist() -> address: view
    def getCommissioner() -> address: view
    def tokenURI(_tokenId: uint256) -> String[2500]: view
    def tokenURI_data_format() -> String[10]: view

interface ArtSales1155:
    def owner() -> address: view
    def artistProceedsAddress() -> address: view

@deploy
def __init__():
    pass

@external
def initialize(
    _art_sales_1155: address,
    _art_piece: address,
    _name: String[100],
    _symbol: String[10],
    _payment_currency: address = empty(address)
):
    assert not self.initialized, "Already initialized"
    assert _art_sales_1155 != empty(address), "Invalid ArtSales1155"
    assert _art_piece != empty(address), "Invalid ArtPiece"
    
    self.initialized = True
    self.artSales1155 = _art_sales_1155
    self.artPiece = _art_piece
    self.paymentCurrency = _payment_currency
    
    sales_contract: ArtSales1155 = ArtSales1155(_art_sales_1155)
    self.owner = staticcall sales_contract.owner()
    self.proceedsAddress = staticcall sales_contract.artistProceedsAddress()
    
    self.name = _name
    self.symbol = _symbol

@external
def createEdition(
    _initial_price: uint256,
    _max_supply: uint256,
    _royalty_percent: uint256,
    _sale_type: uint256 = SALE_TYPE_CAPPED,
    _phases: DynArray[PhaseConfig, 5] = []
):
    """Create the single edition for this contract with sale configuration"""
    assert msg.sender == self.owner or msg.sender == self.artSales1155, "Only owner or ArtSales1155"
    assert self.basePrice == 0, "Edition already created"  # Can only create once
    assert _royalty_percent <= MAX_ROYALTY_PERCENT, "Royalty too high"
    assert _sale_type <= SALE_TYPE_TIME_PHASES, "Invalid sale type"
    
    # Validate phases if provided
    if len(_phases) > 0:
        assert _sale_type == SALE_TYPE_QUANTITY_PHASES or _sale_type == SALE_TYPE_TIME_PHASES, "Phases only for phased sales"
        assert len(_phases) <= MAX_PHASES, "Too many phases"
        
        # Validate phase ordering
        for i: uint256 in range(len(_phases), bound=MAX_PHASES):
            if i > 0:
                assert _phases[i].threshold > _phases[i-1].threshold, "Phases must be in ascending order"
    
    # Set edition configuration
    self.currentPrice = _initial_price
    self.basePrice = _initial_price
    self.maxSupply = _max_supply if _sale_type == SALE_TYPE_CAPPED else max_value(uint256)
    self.currentSupply = 0
    self.isPaused = True  # Start paused, must explicitly start sale
    self.royaltyPercent = _royalty_percent
    self.saleType = _sale_type
    self.saleStartTime = 0
    self.phases = _phases
    self.currentPhase = 0
    
    # Emit URI event
    art_piece_contract: ArtPiece = ArtPiece(self.artPiece)
    uri_value: String[2500] = staticcall art_piece_contract.tokenURI(1)
    log URI(value=uri_value, id=TOKEN_ID)

@external
def startSale():
    """Start the sale for this edition"""
    assert msg.sender == self.owner or msg.sender == self.artSales1155, "Only owner or ArtSales1155"
    assert self.basePrice > 0, "Edition does not exist"
    assert self.isPaused, "Sale already active"
    
    self.isPaused = False
    self.saleStartTime = block.timestamp
    
    log SaleStarted(saleType=self.saleType)

@external
def pauseSale():
    """Pause the sale for this edition"""
    assert msg.sender == self.owner or msg.sender == self.artSales1155, "Only owner or ArtSales1155"
    assert self.basePrice > 0, "Edition does not exist"
    assert not self.isPaused, "Sale already paused"
    
    self.isPaused = True
    log SalePaused(paused=True)

@external
def resumeSale():
    """Resume a paused sale"""
    assert msg.sender == self.owner or msg.sender == self.artSales1155, "Only owner or ArtSales1155"
    assert self.basePrice > 0, "Edition does not exist"
    assert self.isPaused, "Sale not paused"
    
    self.isPaused = False
    log SaleResumed(resumed=True)

@internal
def _updatePriceForPhases():
    """Update price based on current phase"""
    if self.saleType == SALE_TYPE_QUANTITY_PHASES:
        # Find the highest applicable phase based on quantity
        new_phase: uint256 = 0  # 0 = using base price, 1+ = using phases[new_phase-1]
        for i: uint256 in range(len(self.phases), bound=MAX_PHASES):
            if self.currentSupply >= self.phases[i].threshold:
                new_phase = i + 1  # Convert to 1-based indexing
        
        # Update if we've moved to a new phase
        if new_phase != self.currentPhase:
            old_phase: uint256 = self.currentPhase
            old_price: uint256 = self.currentPrice
            self.currentPhase = new_phase
            if new_phase == 0:
                self.currentPrice = self.basePrice
            else:
                self.currentPrice = self.phases[new_phase - 1].price
            log PhaseChanged(newPhase=new_phase, newPrice=self.currentPrice)
            log PriceUpdated(oldPrice=old_price, newPrice=self.currentPrice)
                
    elif self.saleType == SALE_TYPE_TIME_PHASES:
        # Find the highest applicable phase based on time
        current_time: uint256 = block.timestamp
        new_phase: uint256 = 0  # 0 = using base price, 1+ = using phases[new_phase-1]
        for i: uint256 in range(len(self.phases), bound=MAX_PHASES):
            if current_time >= self.phases[i].threshold:
                new_phase = i + 1  # Convert to 1-based indexing
        
        # Update if we've moved to a new phase
        if new_phase != self.currentPhase:
            old_phase: uint256 = self.currentPhase
            old_price: uint256 = self.currentPrice
            self.currentPhase = new_phase
            if new_phase == 0:
                self.currentPrice = self.basePrice
            else:
                self.currentPrice = self.phases[new_phase - 1].price
            log PhaseChanged(newPhase=new_phase, newPrice=self.currentPrice)
            log PriceUpdated(oldPrice=old_price, newPrice=self.currentPrice)

@view
@internal
def _getCurrentPrice() -> uint256:
    """Get current price, checking for phase updates"""
    if len(self.phases) == 0:
        return self.currentPrice
    
    # For time-based phases, check if price should update
    if self.saleType == SALE_TYPE_TIME_PHASES:
        current_time: uint256 = block.timestamp
        for i: uint256 in range(len(self.phases), bound=MAX_PHASES):
            phase_index: uint256 = len(self.phases) - 1 - i
            if current_time >= self.phases[phase_index].threshold:
                return self.phases[phase_index].price
        return self.basePrice
    
    # For quantity-based phases
    elif self.saleType == SALE_TYPE_QUANTITY_PHASES:
        for i: uint256 in range(len(self.phases), bound=MAX_PHASES):
            phase_index: uint256 = len(self.phases) - 1 - i
            if self.currentSupply >= self.phases[phase_index].threshold:
                return self.phases[phase_index].price
        return self.basePrice
    
    return self.currentPrice

@external
@payable
def mint(_amount: uint256):
    """Mint tokens using native ETH payment"""
    assert self.paymentCurrency == empty(address), "This edition only accepts native ETH"
    assert self.basePrice > 0, "Edition does not exist"
    assert not self.isPaused, "Sale is paused"
    
    # Check supply limit for capped sales
    if self.saleType == SALE_TYPE_CAPPED:
        assert self.currentSupply + _amount <= self.maxSupply, "Exceeds max supply"
    
    # Update price for phased sales before calculating cost
    self._updatePriceForPhases()
    
    # Get current price (may have been updated)
    current_price: uint256 = self._getCurrentPrice()
    total_cost: uint256 = current_price * _amount
    assert msg.value >= total_cost, "Insufficient ETH payment"
    
    # Send proceeds to artist
    if msg.value > 0:
        raw_call(self.proceedsAddress, b"", value=msg.value) 
        # Note: raw_call will revert on failure, so no need to check success
    
    # Update supply
    self.currentSupply += _amount
    
    # Mint tokens
    self.balances[msg.sender] += _amount
    
    log TransferSingle(operator=msg.sender, sender=empty(address), receiver=msg.sender, id=TOKEN_ID, value=_amount)
    log EditionMinted(minter=msg.sender, amount=_amount, payment=total_cost)

@external
def mintERC20(_amount: uint256):
    """Mint tokens using ERC20 payment"""
    assert self.paymentCurrency != empty(address), "This edition only accepts ERC20 tokens"
    assert self.basePrice > 0, "Edition does not exist"
    assert not self.isPaused, "Sale is paused"
    
    # Check supply limit for capped sales
    if self.saleType == SALE_TYPE_CAPPED:
        assert self.currentSupply + _amount <= self.maxSupply, "Exceeds max supply"
    
    # Update price for phased sales before calculating cost
    self._updatePriceForPhases()
    
    # Get current price (may have been updated)
    current_price: uint256 = self._getCurrentPrice()
    total_cost: uint256 = current_price * _amount
    
    # Transfer ERC20 tokens
    token: IERC20 = IERC20(self.paymentCurrency)
    success: bool = extcall token.transferFrom(msg.sender, self.proceedsAddress, total_cost)
    assert success, "ERC20 transfer failed"
    
    # Update supply
    self.currentSupply += _amount
    
    # Mint tokens
    self.balances[msg.sender] += _amount
    
    log TransferSingle(operator=msg.sender, sender=empty(address), receiver=msg.sender, id=TOKEN_ID, value=_amount)
    log EditionMinted(minter=msg.sender, amount=_amount, payment=total_cost)

@external
def mintWithPermit(
    _amount: uint256,
    _deadline: uint256,
    _v: uint8,
    _r: bytes32,
    _s: bytes32
):
    """Mint tokens using EIP-2612 permit"""
    assert self.paymentCurrency != empty(address), "Permit only works with ERC20"
    assert self.basePrice > 0, "Edition does not exist"
    assert not self.isPaused, "Sale is paused"
    
    # Check supply limit for capped sales
    if self.saleType == SALE_TYPE_CAPPED:
        assert self.currentSupply + _amount <= self.maxSupply, "Exceeds max supply"
    
    # Update price for phased sales before calculating cost
    self._updatePriceForPhases()
    
    # Get current price (may have been updated)
    current_price: uint256 = self._getCurrentPrice()
    total_cost: uint256 = current_price * _amount
    
    # Use permit
    permit_token: IERC20Permit = IERC20Permit(self.paymentCurrency)
    extcall permit_token.permit(msg.sender, self, total_cost, _deadline, _v, _r, _s)
    
    # Transfer tokens
    success: bool = extcall permit_token.transferFrom(msg.sender, self.proceedsAddress, total_cost)
    assert success, "ERC20 permit transfer failed"
    
    # Update supply
    self.currentSupply += _amount
    
    # Mint tokens
    self.balances[msg.sender] += _amount
    
    log TransferSingle(operator=msg.sender, sender=empty(address), receiver=msg.sender, id=TOKEN_ID, value=_amount)
    log EditionMinted(minter=msg.sender, amount=_amount, payment=total_cost)

@external
def setCurrentPrice(_new_price: uint256):
    """Manually set price (only for non-phased sales)"""
    assert msg.sender == self.owner, "Only owner"
    assert self.saleType == SALE_TYPE_FOREVER or self.saleType == SALE_TYPE_CAPPED, "Cannot manually set price for phased sales"
    
    old_price: uint256 = self.currentPrice
    self.currentPrice = _new_price
    log PriceUpdated(oldPrice=old_price, newPrice=_new_price)

@external
def updateProceedsAddress(_new_address: address):
    assert msg.sender == self.owner, "Only owner"
    assert _new_address != empty(address), "Invalid address"
    self.proceedsAddress = _new_address

# View functions for sale info
@view
@external
def getSaleInfo() -> (uint256, uint256, uint256, uint256, bool, uint256):
    """Returns (saleType, currentPrice, currentSupply, maxSupply, isPaused, currentPhase)"""
    current_price: uint256 = self._getCurrentPrice()
    return (self.saleType, current_price, self.currentSupply, self.maxSupply, self.isPaused, self.currentPhase)

@view
@external
def getPhases() -> DynArray[PhaseConfig, 5]:
    """Get all phases for this edition"""
    return self.phases

# ERC1155 Standard Functions (simplified for single token)

@external
def safeTransferFrom(
    _from: address,
    _to: address,
    _id: uint256,
    _value: uint256,
    _data: Bytes[1024]
):
    assert _id == TOKEN_ID, "Invalid token ID"
    assert _from == msg.sender or self.operatorApprovals[_from][msg.sender], "Not authorized"
    assert _to != empty(address), "Invalid recipient"
    assert self.balances[_from] >= _value, "Insufficient balance"
    
    self.balances[_from] -= _value
    self.balances[_to] += _value
    
    log TransferSingle(operator=msg.sender, sender=_from, receiver=_to, id=_id, value=_value)

@external
def safeBatchTransferFrom(
    _from: address,
    _to: address,
    _ids: DynArray[uint256, 100],
    _values: DynArray[uint256, 100],
    _data: Bytes[1024]
):
    assert _from == msg.sender or self.operatorApprovals[_from][msg.sender], "Not authorized"
    assert _to != empty(address), "Invalid recipient"
    assert len(_ids) == len(_values), "Length mismatch"
    
    for i: uint256 in range(len(_ids), bound=100):
        assert _ids[i] == TOKEN_ID, "Invalid token ID"
        assert self.balances[_from] >= _values[i], "Insufficient balance"
        self.balances[_from] -= _values[i]
        self.balances[_to] += _values[i]
    
    log TransferBatch(operator=msg.sender, sender=_from, receiver=_to, ids=_ids, values=_values)

@external
def setApprovalForAll(_operator: address, _approved: bool):
    self.operatorApprovals[msg.sender][_operator] = _approved
    log ApprovalForAll(owner=msg.sender, operator=_operator, approved=_approved)

@view
@external
def balanceOf(_owner: address, _id: uint256) -> uint256:
    assert _id == TOKEN_ID, "Invalid token ID"
    return self.balances[_owner]

@view
@external
def balanceOfBatch(
    _owners: DynArray[address, 100],
    _ids: DynArray[uint256, 100]
) -> DynArray[uint256, 100]:
    assert len(_owners) == len(_ids), "Length mismatch"
    result: DynArray[uint256, 100] = []
    for i: uint256 in range(len(_owners), bound=100):
        assert _ids[i] == TOKEN_ID, "Invalid token ID"
        result.append(self.balances[_owners[i]])
    return result

@view
@external
def isApprovedForAll(_owner: address, _operator: address) -> bool:
    return self.operatorApprovals[_owner][_operator]

@view
@external
def uri(_id: uint256) -> String[2500]:
    assert _id == TOKEN_ID, "Invalid token ID"
    assert self.basePrice > 0, "Token does not exist"
    
    art_piece_contract: ArtPiece = ArtPiece(self.artPiece)
    return staticcall art_piece_contract.tokenURI(1)

@view
@external
def getArtPieceData() -> (String[100], String[400], address, address):
    art_piece_contract: ArtPiece = ArtPiece(self.artPiece)
    title: String[100] = staticcall art_piece_contract.getTitle()
    description: String[400] = staticcall art_piece_contract.getDescription()
    artist: address = staticcall art_piece_contract.getArtist()
    commissioner: address = staticcall art_piece_contract.getCommissioner()
    return (title, description, artist, commissioner)

@view
@external
def getArtPieceImageData() -> Bytes[45000]:
    art_piece_contract: ArtPiece = ArtPiece(self.artPiece)
    return staticcall art_piece_contract.getTokenURIData()

@view
@external
def getArtPieceImageFormat() -> String[10]:
    art_piece_contract: ArtPiece = ArtPiece(self.artPiece)
    return staticcall art_piece_contract.tokenURI_data_format()

@view
@external
def supportsInterface(_interface_id: bytes4) -> bool:
    return _interface_id in [
        0x01ffc9a7,  # ERC165
        0xd9b67a26,  # ERC1155
        0x0e89341c   # ERC1155MetadataURI
    ]

@view
@external
def getEditionInfo() -> (uint256, uint256, uint256, bool):
    """Returns (currentPrice, currentSupply, maxSupply, isPaused)"""
    current_price: uint256 = self._getCurrentPrice()
    return (current_price, self.currentSupply, self.maxSupply, self.isPaused)

@view
@external
def getLinkedArtPiece() -> address:
    return self.artPiece

@view
@external
def isPaymentCurrencyValid() -> bool:
    return True

@view
@external
def getPaymentInfo() -> (address, String[20]):
    if self.paymentCurrency == empty(address):
        return (empty(address), "Native ETH")
    else:
        return (self.paymentCurrency, "ERC20 Token")

@external
def emergencyWithdraw():
    assert msg.sender == self.owner, "Only owner"
    
    if self.balance > 0:
        send(self.proceedsAddress, self.balance)
    
    if self.paymentCurrency != empty(address):
        token: IERC20 = IERC20(self.paymentCurrency)
        balance: uint256 = staticcall token.balanceOf(self)
        if balance > 0:
            success: bool = extcall token.transfer(self.proceedsAddress, balance)
            assert success, "Emergency ERC20 transfer failed"