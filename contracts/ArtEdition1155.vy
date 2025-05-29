# @version 0.4.1

# ArtEdition1155: ERC1155 implementation for art piece editions
# This contract is cloned for each art piece that wants to offer editions

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
    value: String[256]
    id: indexed(uint256)

# Custom Events
event EditionMinted:
    minter: indexed(address)
    tokenId: indexed(uint256)
    amount: uint256
    payment: uint256

event PriceUpdated:
    tokenId: indexed(uint256)
    oldPrice: uint256
    newPrice: uint256

# State Variables
initialized: public(bool)
artSales1155: public(address)  # Parent ArtSales1155 contract
artPiece: public(address)      # Source ArtPiece contract
owner: public(address)         # Profile owner
proceedsAddress: public(address)

# Token metadata
name: public(String[100])
symbol: public(String[10])
baseURI: public(String[256])

# ERC1155 Storage
balances: public(HashMap[uint256, HashMap[address, uint256]])  # tokenId -> owner -> balance
operatorApprovals: public(HashMap[address, HashMap[address, bool]])  # owner -> operator -> approved

# Edition Configuration
tokenIdToConfig: public(HashMap[uint256, TokenConfig])
nextTokenId: public(uint256)

struct TokenConfig:
    mintPrice: uint256
    maxSupply: uint256
    currentSupply: uint256
    isPaused: bool
    royaltyPercent: uint256  # Basis points (100 = 1%)

# Constants
MAX_ROYALTY_PERCENT: constant(uint256) = 1000  # 10%

# Interface for ArtPiece
interface ArtPiece:
    def getTokenURIData() -> Bytes[45000]: view
    def getTitle() -> String[100]: view
    def getDescription() -> String[200]: view
    def getArtist() -> address: view
    def getCommissioner() -> address: view

# Interface for ArtSales1155
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
    _base_uri: String[256]
):
    assert not self.initialized, "Already initialized"
    assert _art_sales_1155 != empty(address), "Invalid ArtSales1155"
    assert _art_piece != empty(address), "Invalid ArtPiece"
    
    self.initialized = True
    self.artSales1155 = _art_sales_1155
    self.artPiece = _art_piece
    
    # Get owner and proceeds address from ArtSales1155
    sales_contract: ArtSales1155 = ArtSales1155(_art_sales_1155)
    self.owner = staticcall sales_contract.owner()
    self.proceedsAddress = staticcall sales_contract.artistProceedsAddress()
    
    self.name = _name
    self.symbol = _symbol
    self.baseURI = _base_uri
    self.nextTokenId = 1

@external
def createEdition(
    _mint_price: uint256,
    _max_supply: uint256,
    _royalty_percent: uint256
) -> uint256:
    """Create a new edition/token type"""
    assert msg.sender == self.owner, "Only owner can create editions"
    assert _royalty_percent <= MAX_ROYALTY_PERCENT, "Royalty too high"
    
    token_id: uint256 = self.nextTokenId
    self.nextTokenId += 1
    
    self.tokenIdToConfig[token_id] = TokenConfig({
        mintPrice: _mint_price,
        maxSupply: _max_supply,
        currentSupply: 0,
        isPaused: False,
        royaltyPercent: _royalty_percent
    })
    
    log URI(self.baseURI, token_id)
    return token_id

@external
@payable
def mint(_token_id: uint256, _amount: uint256):
    """Public minting function"""
    config: TokenConfig = self.tokenIdToConfig[_token_id]
    assert config.mintPrice > 0, "Edition does not exist"
    assert not config.isPaused, "Minting paused"
    assert config.currentSupply + _amount <= config.maxSupply, "Exceeds max supply"
    assert msg.value >= config.mintPrice * _amount, "Insufficient payment"
    
    # Update supply
    self.tokenIdToConfig[_token_id].currentSupply += _amount
    
    # Mint tokens
    self.balances[_token_id][msg.sender] += _amount
    
    # Send proceeds to artist
    if msg.value > 0:
        send(self.proceedsAddress, msg.value)
    
    log TransferSingle(msg.sender, empty(address), msg.sender, _token_id, _amount)
    log EditionMinted(msg.sender, _token_id, _amount, msg.value)

@external
def setMintPrice(_token_id: uint256, _new_price: uint256):
    assert msg.sender == self.owner, "Only owner"
    old_price: uint256 = self.tokenIdToConfig[_token_id].mintPrice
    self.tokenIdToConfig[_token_id].mintPrice = _new_price
    log PriceUpdated(_token_id, old_price, _new_price)

@external
def setPaused(_token_id: uint256, _paused: bool):
    assert msg.sender == self.owner, "Only owner"
    self.tokenIdToConfig[_token_id].isPaused = _paused

@external
def updateProceedsAddress(_new_address: address):
    assert msg.sender == self.owner, "Only owner"
    assert _new_address != empty(address), "Invalid address"
    self.proceedsAddress = _new_address

# ERC1155 Standard Functions
@external
def safeTransferFrom(
    _from: address,
    _to: address,
    _id: uint256,
    _value: uint256,
    _data: Bytes[1024]
):
    assert _from == msg.sender or self.operatorApprovals[_from][msg.sender], "Not authorized"
    assert _to != empty(address), "Invalid recipient"
    assert self.balances[_id][_from] >= _value, "Insufficient balance"
    
    self.balances[_id][_from] -= _value
    self.balances[_id][_to] += _value
    
    log TransferSingle(msg.sender, _from, _to, _id, _value)

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
        assert self.balances[_ids[i]][_from] >= _values[i], "Insufficient balance"
        self.balances[_ids[i]][_from] -= _values[i]
        self.balances[_ids[i]][_to] += _values[i]
    
    log TransferBatch(msg.sender, _from, _to, _ids, _values)

@external
def setApprovalForAll(_operator: address, _approved: bool):
    self.operatorApprovals[msg.sender][_operator] = _approved
    log ApprovalForAll(msg.sender, _operator, _approved)

@view
@external
def balanceOf(_owner: address, _id: uint256) -> uint256:
    return self.balances[_id][_owner]

@view
@external
def balanceOfBatch(
    _owners: DynArray[address, 100],
    _ids: DynArray[uint256, 100]
) -> DynArray[uint256, 100]:
    assert len(_owners) == len(_ids), "Length mismatch"
    result: DynArray[uint256, 100] = []
    for i: uint256 in range(len(_owners), bound=100):
        result.append(self.balances[_ids[i]][_owners[i]])
    return result

@view
@external
def isApprovedForAll(_owner: address, _operator: address) -> bool:
    return self.operatorApprovals[_owner][_operator]

@view
@external
def uri(_id: uint256) -> String[256]:
    return self.baseURI

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
def getEditionInfo(_token_id: uint256) -> (uint256, uint256, uint256, bool):
    """Returns (mintPrice, currentSupply, maxSupply, isPaused)"""
    config: TokenConfig = self.tokenIdToConfig[_token_id]
    return (config.mintPrice, config.currentSupply, config.maxSupply, config.isPaused)