
i need to create a mechanism to register art commission hubs in what is currently called the 'ownerregistry'. 
At the end of the day, the 'OwnerRegsitry'  also gets cross chain messages from the L2 and updates the correct owner of a artcommissionhubs on the L3.  This registry also is the focal point to lookup all different commissioned works which are registered, via their ArtCommissionHubs.  So if i want to update the owner of an art piece, i can call a method on the L1 which will propagate all the way down and relay to the 'OwnerRegistry' which will update the owner of that artCommissionHub. this way an ArtCommissionHub can always have the latest owner for ALL the commissioned works under a single contract/update.


When a user uploads a piece they have the option of saying that its a commission:
- if a collector uploads an art piece, they upload it as a collector (commissioner)
- if an artist uploads an art piece, they upload it as the artist (artist)

TODO: I need a simple 
TODO: There probably needs to be a method which allows the uploader to flag (upload as art I created, or uploade as a commission i got from someone else) just in case the rolls need to change for an upload or two.

TODO: figure out...
I need to grow the functionality here to handle both group commissions.  A group commission is a single artist who creates a single work what a group of people tagged in their work.  this will generally be saved as a myArt piece under a person, or perhaps create a artCommissionHub for an artist.  Does the code already handle that?

TODO: I need (after i figure out the answers to the above issues) to document that

TODO:
I need lastly to create a mechanism where on creating a profile, the user can also give the address of an ArtCommissionHub OR another user.  
I need a single transaction for any user interaction. 
User creates art piece on existing profile
User creates art piece on new profile, creating the profile and registering it
User create profile art piece and their profile
User creating an art piece with an associated profile who made the work (so it would be a commissioned work for the uploader but a unverified art piece for the artist).
 - Note: This would have to create a new profile for the artist as well if it doesn't exist
User creates commissioned work on a new profile.  This will create their profile, create a ArtCommissionHub for that work, register the Art as unverified to the ArtCommissionHub.



 registering the profile in the profile hub, registering the SECOND profile if the user destination address doesn't have a profile and you are registering a piece on someone else's profile, 

TODO: 
Last and finally i need a way for any number of ArtCommissionHubs to be associated with a profile.  When the ArtCommissionHub updates to a new user, i need that users profile to show all the recent art.  I also need the ArtCommissionHub of the previous owner to be unregistered as they no longer are the owner of the ACH work.  


To clarify contract purposes, I suggest the following renames:
OwnerRegistry → NFTOwnershipRegistry
Reflects its role in managing NFT ownership and hub registration across chains.

ArtCommissionHub → CommissionCollection
Indicates it’s a collection of commissioned works tied to an NFT or artist.

Profile → UserProfile
Clearly denotes it as a user’s profile with art and social features.

ProfileHub → ProfileRegistry
Emphasizes its role as the central registry for profiles.

ArtPiece → ArtWork
Simplifies and clarifies that it represents individual art pieces.


1. it should automatically unlink the hub as the hub links to the new owner's profile.
2. if the profile doesnt exist, i need to create the profile.  anyone can create a profile for anyone, but the profile account address remains the owner of that profile.  the profile will always be registered to the profile hub on creation.  also yes create the profile.
3. A group commission is actually a single commission done without a NFT-based ArtCommissionHub but a more generic ArtCommissionHub.  in reality a group commission is a single artist making an ArtPiece.  that artPiece has a bunch of tagged individuals.
There also is the need for a ArtCommissionHub which is owned by a 3rd party wallet , multisig, single account and chainId and not specifically attached to an NFT collection.  This needs to be addressed.
4. Yes, every time an ArtCommissionHub is created, it needs to be Registered.

5.  Also from a user and website standpoint, i need it so that you can see the latest commissions from your most recent NFT-associated ArtCommissionHub, so that when you buy a NFT, and update the owner in the owner registry and associated art CommissionHub, you can immediately query for the latest ArtCommissionHub which is attached to that Profile (and then grab the underlying art pieces)

Also I need to handle designing a page which is going to be most beneficial for users where every time the artist or user refreshes, it can grab a new block of art from across multiple ArtCommissionHubs.  This may be something like ->  Get Random 5 ArtCommissionHubs registered to me, grab 5-50 art pieces from each of those hubs (there are likely fewer than 5 for almost all hubs, so 5-50 is a very aggressive number), then grab the artPieces for each of those  

Also i need a way to see latest commissions both confirmed and unverified so that the homepage can show new art all the time.  