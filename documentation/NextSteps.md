
i need to create a mechanism to register art commission hubs in what is currently called the 'ownerregistry'. 
At the end of the day, the 'OwnerRegsitry'  also gets cross chain messages from the L2 and updates the correct owner of a artcommissionhubs on the L3.  This registry also is the focal point to lookup all different commissioned works which are registered, via their ArtCommissionHubs.  So if i want to update the owner of an art piece, i can call a method on the L1 which will propagate all the way down and relay to the 'ArtCommissionHubOwners' which will update the owner of that artCommissionHub. this way an ArtCommissionHub can always have the latest owner for ALL the commissioned works under a single contract/update.


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

