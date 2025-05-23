# ProfileFactoryAndRegistry User Guide

## Creating a Profile with Art in One Transaction

The CommissionArt platform allows you to create a profile and upload your first art piece in a single transaction, making the onboarding process seamless and efficient.

### How It Works

When you upload your first art piece to the platform, we automatically:

1. Create a new profile for you
2. Associate the uploaded art piece with your new profile
3. Configure all necessary permissions and relationships

This saves gas costs and simplifies the user experience by eliminating the need for multiple transactions.

### Usage Scenarios

#### First-Time User Uploading Art

If you're a new user wanting to upload your artwork:

1. Simply upload your art through the platform interface
2. The system will detect you don't have a profile and create one for you
3. Your art piece will be immediately available on your new profile

#### Commissioning Art (as a Commissioner)

If you're commissioning art for the first time:

1. Create a new commission request
2. Specify the artist you wish to commission
3. A profile will be created for you along with the commission record

#### Artist Creating a Portfolio

Artists can upload their first portfolio piece and create their profile simultaneously:

1. Upload your artwork
2. Set yourself as an artist
3. Your profile will be created with your first portfolio piece

### Technical Details

Under the hood, this functionality uses the `createNewArtPieceAndRegisterProfileAndAttachToHub` method on the ProfileFactoryAndRegistry contract, which:

- Verifies you don't already have a profile
- Creates a new Profile contract instance for you
- Sets up the initial Profile state
- Creates and initializes the ArtPiece contract for your artwork
- Links the ArtPiece to your profile
- Emits events for both the profile creation and art piece creation

### Benefits

- **Gas Efficiency**: Save on transaction costs by combining two operations
- **Simplified Onboarding**: Create your entire presence on the platform in one step
- **Immediate Functionality**: Start using all platform features right away
- **Reduced Friction**: No need to understand the two-step process of creating a profile first, then uploading art

### Limitations

- This method can only be used if you don't already have a profile
- If you already have a profile, you'll need to use the regular art creation process

### For Developers

The `createNewArtPieceAndRegisterProfileAndAttachToHub` function in the ProfileFactoryAndRegistry contract accepts these parameters:

```solidity
function createNewArtPieceAndRegisterProfileAndAttachToHub(
    address _art_piece_template,
    bytes _image_data,
    string _title,
    bytes _description,
    bool _is_artist,
    address _other_party,
    address _commission_hub,
    bool _ai_generated
) external returns (address, address)
```

This returns a tuple of the new profile address and the new art piece address. 



1. Profile: Core Behaviors
A. What a Profile Can Do
Upload Art: Profiles (users) can upload ArtPieces. These are initially owned by the profile.
Tag as Commission: Art can be tagged as a commission, either as the artist or as a curator/commissioner.
Put Art for Sale: Both artists and curators should be able to put their art up for sale.
Sales Profile/Contract: Eventually, all sales (especially ERC1155) will be handled by a dedicated sales contract/profile.
Verification Flows: Art can move between "unverified" and "verified" states, depending on actions by artists/commissioners.
NFT Linking: Art can be linked to an NFT collection (ArtCommissionHub), at which point ownership and sale logic may change.
2. Variables & Methods: What to Keep, What to Strip
A. Variables to Keep
My Art: List of ArtPiece addresses uploaded by this profile.
Commissions: List of ArtPiece addresses tagged as commissions (could be split into "as artist" and "as curator").
Unverified/Verified Art: Lists for art in each state.
For Sale: List of ArtPiece addresses currently up for sale (or a mapping for quick lookup).
Profile Metadata: User address, isArtist flag, profile image, etc.
Linked ERC1155s: If the profile can own ERC1155 tokens directly (for future sales).
B. Variables to Strip/Move
Direct Sale Logic: Any logic/variables for handling ERC1155 sales should be moved to the sales contract/profile.
Collector/Other Profiles: If you have variables for tracking other users' art or collections, consider if these are needed in Profile or should be in a separate registry/contract.
Legacy/Redundant Lists: If you have both "myArt" and "myCommissions" and they're always in sync, you may only need one with a tag/flag.
Direct Ownership of Art After Linking: Once art is linked to an ArtCommissionHub, the profile should not track ownership directly—ownership is determined by the hub.
C. Methods to Keep
Upload Art
Tag as Commission
Put Art for Sale
Remove Art from Sale
Move Art Between Verified/Unverified
Link Art to NFT/CommissionHub
Profile Metadata Management
D. Methods to Strip/Move
Direct ERC1155 Sale/Transfer: Move to sales contract/profile.
Ownership Transfer Logic for Linked Art: Should be handled by the ArtCommissionHub and ArtCommissionHubOwners, not Profile.
Complex Removal Methods: If you have many similar "removeX" methods, consider a single generic method with an enum/int parameter (as you noted in your drawio comment).
3. Profile: Clear Behavior Flow
A. Uploading Art
User uploads art → ArtPiece contract is created → Added to myArt in Profile.
B. Tagging as Commission
User (artist or curator) tags art as a commission → ArtPiece is added to commissions (or similar) in Profile.
C. Verification
Art can be moved between unverifiedArt and verifiedArt by the relevant party (artist/curator).
D. Putting Art for Sale
User marks art as "for sale" → ArtPiece is added to forSale list/mapping.
(Eventually) Sale is handled by a dedicated ERC1155 sales contract/profile.
E. Linking to NFT/CommissionHub
Art is linked to an ArtCommissionHub (NFT collection).
Ownership and sale logic for the art is now managed by the hub and not the profile.
F. Ownership Propagation
If the NFT is sold/transferred, the ArtCommissionHubOwners and ArtCommissionHub update the owner for all linked art.
4. Are You Missing Anything?
Sale Approval/Permissions: Make sure both artist and curator can put art for sale, but only if they have the right (e.g., original uploader or current owner).
Event Emissions: For all state changes (upload, tag, sale, verification), emit events for off-chain tracking.
Profile Expansion: If you want to allow for future features, keep a generic profileExpansion address/slot.
Efficient Removal: As you noted, use a single removal method with a parameter to select which list to remove from, to save contract size.
Security: Ensure only the profile owner can modify their profile/art, and only the current owner can put art for sale.