// Import ABIs statically to make them available in the app
import ArrayManagerABI from '../assets/abis/ArrayManager.json';
import ArtPieceABI from '../assets/abis/ArtPiece.json';
import ArtPieceOffChainABI from '../assets/abis/ArtPieceOffChain.json';
import ArtCommissionHubABI from '../assets/abis/ArtCommissionHub.json';
import L1QueryOwnerABI from '../assets/abis/L1QueryOwner.json';
import L2RelayABI from '../assets/abis/L2Relay.json';
import OwnerRegistryABI from '../assets/abis/OwnerRegistry.json';
import ProfileABI from '../assets/abis/Profile.json';
import ProfileFactoryAndRegistryABI from '../assets/abis/ProfileFactoryAndRegistry.json';
import SimpleERC721ABI from '../assets/abis/SimpleERC721.json';

// Map of ABI names to their actual content
const abiMap: { [key: string]: any } = {
  'ArrayManager': ArrayManagerABI,
  'ArtPiece': ArtPieceABI,
  'ArtPieceOffChain': ArtPieceOffChainABI,
  'ArtCommissionHub': ArtCommissionHubABI,
  'L1QueryOwner': L1QueryOwnerABI,
  'L2Relay': L2RelayABI,
  'OwnerRegistry': OwnerRegistryABI,
  'Profile': ProfileABI,
  'ProfileFactoryAndRegistry': ProfileFactoryAndRegistryABI,
  'SimpleERC721': SimpleERC721ABI,
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
