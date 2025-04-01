
import ape
from ape import accounts, project

def main():
    account = accounts.load("deployer")
    registry = project.Registry.deploy(sender=account)
    print("REGISTRY_ADDRESS=", registry.address)
