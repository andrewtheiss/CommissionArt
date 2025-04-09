#pragma version 0.4.1

struct Commission:
    art_contract: address
    nft_contract: address
    nft_token_id: uint256
    artist: address
    commissioner: address
    is_active: bool

commissions: DynArray[Commission, 1_000_000]
art_contract_to_index: HashMap[address, uint256]

event CommissionRegistered:
    index: indexed(uint256)
    art_contract: address
    nft_contract: address
    nft_token_id: uint256
    artist: address
    commissioner: address

@external
def register_commission(
    art_contract: address,
    nft_contract: address,
    nft_token_id: uint256,
    artist: address,
    commissioner: address
):
    assert art_contract != empty(address), "Invalid art contract address"
    assert self.art_contract_to_index[art_contract] == 0, "Commission already registered"
    new_commission: Commission = Commission(
        art_contract=art_contract,
        nft_contract=nft_contract,
        nft_token_id=nft_token_id,
        artist=artist,
        commissioner=commissioner,
        is_active=True
    )
    index: uint256 = len(self.commissions)
    self.commissions.append(new_commission)
    self.art_contract_to_index[art_contract] = index + 1
    log CommissionRegistered(index=index, art_contract=art_contract, nft_contract=nft_contract, nft_token_id=nft_token_id, artist=artist, commissioner=commissioner)
@external
@view
def get_commission(index: uint256) -> Commission:
    assert index < len(self.commissions), "Index out of bounds"
    return self.commissions[index]

@external
@view
def get_commission_count() -> uint256:
    return len(self.commissions)

# New function: Get a range of commissions
@external
@view
def get_commissions_range(start: uint256, size: uint256) -> DynArray[Commission, 100]:
    assert start < len(self.commissions), "Start index out of bounds"
    assert start < len(self.commissions), "Start index out of bounds"
    result: DynArray[Commission, 100] = empty(DynArray[Commission, 100])
    for j: uint256 in range(100):
        if start + j >= len(self.commissions) or j >= size:
            break
        result.append(self.commissions[start + j])
    return result

@external
def deactivate_commission(art_contract: address):
    index_plus_one: uint256 = self.art_contract_to_index[art_contract]
    assert index_plus_one > 0, "Commission not found"
    index: uint256 = index_plus_one - 1
    self.commissions[index].is_active = False