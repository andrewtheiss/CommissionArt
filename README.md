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
# pipx install eth-ape  (pipx installs everything in a venv system wide!)
# Install plugins
pip install eth-ape
ape plugins install .
# (ape plugins install vyper alchemy -y)

# add private key to the ape 'deployer' account
ape accounts import deployer
# Enter pkey from .env when prompted
ape accounts list

## Ignore pythonwarnings in your profile
# export PYTHONWARNINGS="ignore::Warning:urllib3"

## Running tests:
ape test tests/deploy_L1_L2.py --verbose

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