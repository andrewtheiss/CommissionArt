from ape import accounts
from ape_accounts import import_account_from_private_key
from dotenv import load_dotenv
import os

load_dotenv()
private_key = os.environ.get("PRIVATE_KEY")
passphrase = os.environ.get("DEPLOYER_PASSPHRASE")
if not private_key or not passphrase:
    raise ValueError("PRIVATE_KEY and DEPLOYER_PASSPHRASE must be set in .env")
deployer = import_account_from_private_key("deployer", passphrase, private_key)
print(f"Account imported: {deployer.address}")
