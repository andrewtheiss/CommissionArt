# @version 0.3.7
interface ArbSys:
    def sendTxToL1(destination: address, calldataForL1: bytes) -> uint256: payable

interface OrbitMessenger:
    def sendTxToOrbit(destination: address, calldataForOrbit: bytes) -> uint256: payable

arbsys: constant(address) = 0x0000000000000000000000000000000000000064
orbit_messenger: constant(address) = 0x...  # Placeholder, needs actual address
l1HelperContract: constant(address) = 0x...  # Address of L1 contract
l3Contract: constant(address) = 0x...  # Address of L3 contract on L2

@external
def requestNFTOwner(nftContract: address, tokenId: uint256):
    data: bytes = abi.encode(nftContract, tokenId)
    unique_id: uint256 = ArbSys(arbsys).sendTxToL1(l1HelperContract, data, value=some_value)
    pass

@external
def receiveResultFromL1(data: bytes):
    owner: address = abi.decode(data, [address])
    l3_data: bytes = abi.encode(owner)
    orbit_unique_id: uint256 = OrbitMessenger(orbit_messenger).sendTxToOrbit(l3Contract, l3_data, value=some_value)
    