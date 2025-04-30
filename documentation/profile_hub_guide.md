# ProfileHub User Guide

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

Under the hood, this functionality uses the `createNewArtPieceAndRegisterProfile` method on the ProfileHub contract, which:

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

The `createNewArtPieceAndRegisterProfile` function in the ProfileHub contract accepts these parameters:

```solidity
function createNewArtPieceAndRegisterProfile(
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