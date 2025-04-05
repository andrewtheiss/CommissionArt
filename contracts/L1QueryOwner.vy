# @version 0.3.7
interface IERC721:
    def ownerOf(tokenId: uint256) -> address: view

interface Inbox:
    def createRetryableTicket(to: address, l2CallValue: uint256, maxGas: uint256, gasPriceBid: uint256, data: bytes) -> uint256: payable

INBOX_ADDRESS: constant(address) = 0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f

@external
def queryNFTAndSendBack(nftContract: address, tokenId: uint256, l2Receiver: address):
    nftContract = IERC721(nftContract)
    owner: address = nftContract.ownerOf(tokenId)
    data: bytes = abi.encode(owner)
    maxGas: uint256 = 1000000  # Example value
    gasPriceBid: uint256 = 0   # Example value
    value_to_send: uint256 = 1e18  # Example value in wei
    Inbox(INBOX_ADDRESS).createRetryableTicket(l2Receiver, 0, maxGas, gasPriceBid, data, value=value_to_send)
