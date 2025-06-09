// Import ABIs statically to make them available in the app
import AnimeTokenL2ToL3MessageSenderABI from '../assets/abis/AnimeTokenL2ToL3MessageSender.json';
import ArrayManagerABI from '../assets/abis/ArrayManager.json';
import ArtCommissionHubABI from '../assets/abis/ArtCommissionHub.json';
import ArtCommissionHubOwnersABI from '../assets/abis/ArtCommissionHubOwners.json';
import ArtEdition1155ABI from '../assets/abis/ArtEdition1155.json';
import ArtPieceABI from '../assets/abis/ArtPiece.json';
import ArtPieceLicenseABI from '../assets/abis/ArtPieceLicense.json';
import ArtSales1155ABI from '../assets/abis/ArtSales1155.json';
import L1QueryOwnershipABI from '../assets/abis/L1QueryOwnership.json';
import L2OwnershipRelayABI from '../assets/abis/L2OwnershipRelay.json';
import ProfileABI from '../assets/abis/Profile.json';
import ProfileFactoryAndRegistryABI from '../assets/abis/ProfileFactoryAndRegistry.json';
import ProfileSocialABI from '../assets/abis/ProfileSocial.json';
import SimpleERC721ABI from '../assets/abis/SimpleERC721.json';
import ZZ_CompleteL2ToL3MessageSenderABI from '../assets/abis/ZZ_CompleteL2ToL3MessageSender.json';
import ZZ_TestL3ReceiveMessageABI from '../assets/abis/ZZ_TestL3ReceiveMessage.json';

// Map of ABI names to their actual content
const abiMap: { [key: string]: any } = {
  'AnimeTokenL2ToL3MessageSender': AnimeTokenL2ToL3MessageSenderABI,
  'ArrayManager': ArrayManagerABI,
  'ArtCommissionHub': ArtCommissionHubABI,
  'ArtCommissionHubOwners': ArtCommissionHubOwnersABI,
  'ArtEdition1155': ArtEdition1155ABI,
  'ArtPiece': ArtPieceABI,
  'ArtPieceLicense': ArtPieceLicenseABI,
  'ArtSales1155': ArtSales1155ABI,
  'L1QueryOwnership': L1QueryOwnershipABI,
  'L2OwnershipRelay': L2OwnershipRelayABI,
  'Profile': ProfileABI,
  'ProfileFactoryAndRegistry': ProfileFactoryAndRegistryABI,
  'ProfileSocial': ProfileSocialABI,
  'SimpleERC721': SimpleERC721ABI,
  'ZZ_CompleteL2ToL3MessageSender': ZZ_CompleteL2ToL3MessageSenderABI,
  'ZZ_TestL3ReceiveMessage': ZZ_TestL3ReceiveMessageABI,
};

/**
 * Get the list of available ABI names
 * @returns Array of available ABI names
 */
export const getAvailableABIs = (): string[] => {
  return Object.keys(abiMap);
};

/**
 * Load an ABI by name
 * @param abiName Name of the ABI to load
 * @returns The ABI object or null if not found
 */
export const loadABI = (abiName: string): any => {
  if (!abiName || !abiMap[abiName]) {
    console.error(`ABI '${abiName}' not found`);
    return null;
  }
  
  return abiMap[abiName];
};

/**
 * Get the human-readable method names from an ABI
 * @param abiName Name of the ABI to analyze
 * @returns Array of method names
 */
export const getMethodNames = (abiName: string): string[] => {
  const abi = loadABI(abiName);
  if (!abi) return [];
  
  return abi
    .filter((item: any) => item.type === 'function')
    .map((item: any) => item.name);
};

/**
 * Find ABIs that have a specific method
 * @param methodName Method name to search for
 * @returns Array of ABI names that contain the method
 */
export const findABIsWithMethod = (methodName: string): string[] => {
  return Object.keys(abiMap).filter(abiName => {
    const abi = abiMap[abiName];
    return abi.some((item: any) => 
      item.type === 'function' && item.name === methodName
    );
  });
};

export default {
  getAvailableABIs,
  loadABI,
  getMethodNames,
  findABIsWithMethod
}; 
