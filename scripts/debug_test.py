#!/usr/bin/env python3

import ape
from ape import accounts, project

def main():
    try:
        print("Starting debug test...")
        
        # Get test accounts
        deployer = accounts.test_accounts[0]
        user = accounts.test_accounts[1]
        
        print(f"Deployer: {deployer.address}")
        print(f"User: {user.address}")
        
        # Deploy templates
        print("Deploying Profile template...")
        profile_template = project.Profile.deploy(sender=deployer)
        print(f"Profile template deployed at: {profile_template.address}")
        
        print("Deploying ProfileSocial template...")
        profile_social_template = project.ProfileSocial.deploy(sender=deployer)
        print(f"ProfileSocial template deployed at: {profile_social_template.address}")
        
        print("Deploying ArtCommissionHub template...")
        commission_hub_template = project.ArtCommissionHub.deploy(sender=deployer)
        print(f"ArtCommissionHub template deployed at: {commission_hub_template.address}")
        
        print("Deploying ArtPiece template...")
        art_piece_template = project.ArtPiece.deploy(sender=deployer)
        print(f"ArtPiece template deployed at: {art_piece_template.address}")
        
        # Deploy ProfileFactoryAndRegistry
        print("Deploying ProfileFactoryAndRegistry...")
        profile_factory = project.ProfileFactoryAndRegistry.deploy(
            profile_template.address,
            profile_social_template.address,
            commission_hub_template.address,
            sender=deployer
        )
        print(f"ProfileFactoryAndRegistry deployed at: {profile_factory.address}")
        
        # Deploy ArtCommissionHubOwners
        print("Deploying ArtCommissionHubOwners...")
        art_commission_hub_owners = project.ArtCommissionHubOwners.deploy(
            deployer.address,  # L2OwnershipRelay
            commission_hub_template.address,
            art_piece_template.address,
            sender=deployer
        )
        print(f"ArtCommissionHubOwners deployed at: {art_commission_hub_owners.address}")
        
        # Link contracts
        print("Linking ProfileFactoryAndRegistry and ArtCommissionHubOwners...")
        profile_factory.linkArtCommissionHubOwnersContract(art_commission_hub_owners.address, sender=deployer)
        art_commission_hub_owners.linkProfileFactoryAndRegistry(profile_factory.address, sender=deployer)
        
        # Verify linking
        linked_hub_owners = profile_factory.artCommissionHubOwners()
        linked_profile_factory = art_commission_hub_owners.profileFactoryAndRegistry()
        print(f"Profile factory linked to hub owners: {linked_hub_owners}")
        print(f"Hub owners linked to profile factory: {linked_profile_factory}")
        
        # Test createGenericCommissionHub step by step
        print("Testing createGenericCommissionHub...")
        print(f"Calling createGenericCommissionHub with user: {user.address}")
        print(f"Caller (user): {user.address}")
        
        # Check pre-conditions
        print("Checking pre-conditions...")
        
        # Check if profile factory is set
        profile_factory_address = art_commission_hub_owners.profileFactoryAndRegistry()
        print(f"Profile factory address: {profile_factory_address}")
        
        # Check if hub already exists
        existing_hub = art_commission_hub_owners.getArtCommissionHubByOwner(1, "0x1000000000000000000000000000000000000001", int(user.address, 16))
        print(f"Existing hub for user: {existing_hub}")
        
        # Check if user has profile
        has_profile = profile_factory.hasProfile(user.address)
        print(f"User has profile: {has_profile}")
        
        # Now try the actual call
        try:
            result = art_commission_hub_owners.createGenericCommissionHub(user.address, sender=user)
            print(f"SUCCESS! Transaction result: {result}")
            print(f"Transaction hash: {result.txn_hash}")
            
            # Check if hub was created
            hub_count = art_commission_hub_owners.getCommissionHubCountByOwner(user.address)
            print(f"Hub count for user: {hub_count}")
            
            if hub_count > 0:
                hubs = art_commission_hub_owners.getCommissionHubsByOwnerWithOffset(user.address, 0, 1, False)
                print(f"Created hub address: {hubs[0] if hubs else 'None'}")
        except Exception as create_error:
            print(f"ERROR in createGenericCommissionHub: {create_error}")
            
            # Try to create a profile manually first
            print("Trying to create profile manually...")
            try:
                profile_result = profile_factory.createProfile(user.address, sender=deployer)
                print(f"Profile creation result: {profile_result}")
                
                # Now try creating the hub again
                print("Trying createGenericCommissionHub again after manual profile creation...")
                result = art_commission_hub_owners.createGenericCommissionHub(user.address, sender=user)
                print(f"SUCCESS after manual profile! Result: {result}")
            except Exception as profile_error:
                print(f"ERROR in manual profile creation: {profile_error}")
                
                # Let's try creating a hub using deployer (owner) permission
                print("Trying createGenericCommissionHub with deployer as sender...")
                try:
                    result = art_commission_hub_owners.createGenericCommissionHub(user.address, sender=deployer)
                    print(f"SUCCESS with deployer! Result: {result}")
                except Exception as deployer_error:
                    print(f"ERROR even with deployer: {deployer_error}")
                    raise deployer_error

    except Exception as e:
        print(f"ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 