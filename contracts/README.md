| Layer | Contract Role                                      | Messaging Function                     | Notes                                      |
|-------|----------------------------------------------------|----------------------------------------|--------------------------------------------|
| L1    | Queries NFT owner, sends result to L2 via Inbox    | `createRetryableTicket`                | Uses Inbox at [0x4dbd4fc535...](https://etherscan.io/address/0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f) |
| L2    | Relays L3 requests to L1, forwards results to L3   | `sendTxToL1`, Assumed `sendTxToOrbit`  | Needs `orbit_messenger` address for L3     |
| L3    | Initiates request, updates owner based on response | Assumed Orbit messaging system          | User-triggered, updates `currentOwner`     |

https://sepolia.etherscan.io/address/0xaAe29B0366299461418F5324a79Afc425BE5ae21#writeProxyContract
https://docs.arbitrum.io/build-decentralized-apps/reference/contract-addresses