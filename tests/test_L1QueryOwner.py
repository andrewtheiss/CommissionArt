import pytest
from ape import accounts, project

@pytest.fixture(scope="module")
def l1_contract():
    deployer = accounts.add("0x...your_private_key...")
    return deployer.deploy(project.L1QueryOwner)

def test_query_nft_owner(l1_contract):
    # Test logic here
    pass