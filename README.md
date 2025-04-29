# Azuki Image Backup on AnimeChain L3

This project stores Azuki NFT images as on-chain data on AnimeChain L3 using Vyper smart contracts, creating an immutable backup that links to the L1 NFT contract.

## Components

- **Registry.vy**: Main contract that maps Azuki IDs to their respective image contracts
- **CommissionedArt.vy**: Contract for storing a single image's data on-chain
- **Deployment scripts**: Scripts for deploying contracts and uploading images

## Setup

1. Clone this repository
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Create a `.env` file based on `.env.example`:
```
cp .env.example .env
```
4. Edit `.env` and add your private key and configuration

## Using the Contracts

### Registry Contract

The Registry contract maps Azuki IDs to their corresponding image data contracts. It can:
- Register new image contracts for specific Azuki IDs
- Link to the L1 NFT contract for verification
- Rescind ownership once all images are deployed to make the registry immutable

### CommissionedArt Contract

Each CommissionedArt contract stores:
- The image data for a single Azuki NFT
- Zero addresses for owner and artist (since this is a backup)

## Scripts

### Compile and Extract ABIs

Before deployment, compile contracts and extract ABIs:

```
ape compile
python scripts/compile_and_extract_abis.py
```

This generates ABI files in `src/assets/abis/` for frontend integration.

### Deploy Registry and Images

Deploy the contracts with:

```
python scripts/deploy_registry_and_images.py
python scripts/
```

This script:
1. Deploys the Registry contract
2. Sets the L1 contract address (if provided)
3. Deploys CommissionedArt contracts for each image
4. Registers each image contract in the Registry
5. Optionally rescinds ownership after all deployments

### Tests

Run tests with:

```
ape test
```

## Configuration

The `.env` file controls deployment parameters:
- `PRIVATE_KEY`: Private key for deployment
- `L1_CONTRACT_ADDRESS`: Address of the L1 Azuki contract
- `NETWORK`: Network to deploy to (default: animechain:custom)
- `RESCIND_OWNERSHIP`: Set to "true" to permanently rescind ownership after deployment

## Deployment
The deployment process creates:
1. One Registry contract
2. Multiple CommissionedArt contracts (one per image)

Once ownership is rescinded, no more images can be added to the Registry.


### Ape developing --
# https://docs.apeworx.io/ape/stable/userguides/quickstart.html
# pip install pipx
# pipx install eth-ape  (pipx installs everything in a venv system wide!)
# Install plugins
pip install eth-ape
ape plugins install .
pip install --upgrade eth-ape
# (ape plugins install vyper alchemy -y)

# add private key to the ape 'deployer' account
ape accounts import deployer
# Enter pkey from .env when prompted
ape accounts list

## Ignore pythonwarnings in your profile
# export PYTHONWARNINGS="ignore::Warning:urllib3"

## Running tests:
ape test tests/deploy_L1_L2.py --verbose
ape test tests/test_L1QueryOwner_testnet.py

# Plans for ROADMAP
- Create a way for artists to offer commissions to artists

## Windows installation (Power Shell)
After installing 
pip install -r ./requirements.txt
Get-Command pip
python -m site
 (this shows the path of python)

 ## Temp solution:
 $env:Path += ";C:\Users\andyComp\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p1\LocalCache\local-packages\Python311\Scripts"

 # Add C:\Users\andyComp\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p1\LocalCache\local-packages\Python311\Scripts to your path
 

 # Decrypt the .env password file on mac
 Using p7zip installed via brew (brew install p7zip)
 7z x -p1234 .env.7zencoded -o/tmp/env_temp && mv /tmp/env_temp/.env .env && rm -rf /tmp/env_temp

 # Reacrhive the file after its been modified
 7z l -p"$PASSWORD" .env.7zencoded




# Deployment
As of commit e84f4ff you can compile the contract code and get the back end linked by:
1. ape compile --force
2. ape run deploy_L1_L2
 - Choose testnet
 - L2 Contract will not update, this needs to be done manually
3. ape run compile_and_extract_abis
 - At this point you should see the contract_config.json file updated with the new contract addresses

** Checkpoint
4. npm run dev
5. Scroll down and verify L1 information under BridgeTest:
 FORWARD:
 - NFTs can be checked on the L1OwnerQuery contract. When the L1->L2 cross chain call is made, the incoming
     addressed does NOT match the L1 sending address.  Instead it is aliased by adding 
     0x11111000000...00000000011111 to the end.
   If the address of the L1 contract is 0xDdc84E4CF833b5AE92A2aA7F4edc59bdcB4b6F0F
      the aliased contract of the L1 is 0xeed94e4cf833b5ae92a2aa7f4edc59bdcb4b8020

 - Verify L1 Contract Settings match the contract_config.json settings
   -  (Note: This should be updated and show all the L1,L2,L3 contracts under this section)
 - Verify L3 OwnerRegistry Contract settings match the contract_config.json settings
   -  (Note: This should be updated and show all the L1,L2,L3 contracts under this section)

 - UPDATE L2 Contract Settings:
   - The L2 Links to L1 and the L3
- Please register the L1QueryOwner ALIASED address to whitelist its abiliaty to update NFT contract owners
    on the L1.  The aliased address for the above example is:
     0xED5AF388653567Af2F388E6224dC7C4b3241C544 and chain ID 1 (to be testnet)
- Please register the L3 contract address so that the L2 knows how to Relay the owners to the L3
       
- Now that everything is linked, lookup the owners of a few NFTs on the L1 via the button:
    Send Request(Safe Parameters) which queries the owner with the provided form values.
- Modify the Token ID to #1 and send again


6. Be patient.  You need to verify calls on the L1, L2 and L3.  
    - Metamask should have the signed messages to the L1 calls
    - After ~5 minutes on the L2, you should see the relay contract:
        i.e. https://sepolia.arbiscan.io/address/0x233be9576A524299bf9E4633c845ea28FF0868a4
    - After 10 more seconds you should see the L3 contract call.
        TODO: Eventually this will require ANOTHER cross-chain message


# REMIXD Setup
remixd -s <absolute-path-to-the-shared-folder> --remix-ide https://remix.ethereum.org
remixd -s C:\Users\andre\Documents\Git\CommissionArt --remix-ide https://remix.ethereum.org



Test and dev plans
- Create test for ArtPiece creation
- Create test for Profile creation along with Art Piece
- Support for ERC721 as ArtPiece.  May need to have extended data use different address for URI
- SUpport for ERC 998 if necesary for created Art Piece