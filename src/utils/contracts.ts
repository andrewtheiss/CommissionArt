// Contract information and ABIs
export const contracts = {
  CommissionedArt: {
    name: "CommissionedArt",
    abi: [
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "from_owner",
            "type": "address"
          },
          {
            "indexed": true,
            "name": "to_owner",
            "type": "address"
          }
        ],
        "name": "OwnershipTransferred",
        "type": "event"
      },
      {
        "inputs": [],
        "name": "get_image_data",
        "outputs": [
          {
            "name": "",
            "type": "bytes"
          }
        ],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "inputs": [],
        "name": "get_owner",
        "outputs": [
          {
            "name": "",
            "type": "address"
          }
        ],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "inputs": [],
        "name": "get_artist",
        "outputs": [
          {
            "name": "",
            "type": "address"
          }
        ],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "inputs": [
          {
            "name": "new_owner",
            "type": "address"
          }
        ],
        "name": "transferOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
      },
      {
        "inputs": [
          {
            "name": "image_data_input",
            "type": "bytes"
          },
          {
            "name": "owner_input",
            "type": "address"
          },
          {
            "name": "artist_input",
            "type": "address"
          }
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
      }
    ],
    addresses: {
      // AnimeChain L3
      "69000": "0x7c47F6bd686A243Be2c8fAB828ceC5E3014871d7"
    },
    networks: {
      "69000": {
        name: "AnimeChain",
        rpcUrl: "https://rpc-animechain-39xf6m45e3.t.conduit.xyz",
        currency: "anime"
      }
    }
  }
};

export const defaultNetwork = {
  chainId: "69000",
  name: "AnimeChain",
  rpcUrl: "https://rpc-animechain-39xf6m45e3.t.conduit.xyz",
  currency: "anime"
};

export const defaultContract = {
  name: "CommissionedArt",
  address: "0x7c47F6bd686A243Be2c8fAB828ceC5E3014871d7"
}; 