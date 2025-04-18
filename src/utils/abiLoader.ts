// Import ABIs statically to make them available in the app
import L1QueryOwnerABI from '../assets/abis/L1QueryOwner.json';
import L2RelayABI from '../assets/abis/L2Relay.json';
import CommissionRegistryABI from '../assets/abis/CommissionRegistry.json';
import CommissionedArtABI from '../assets/abis/CommissionedArt.json';
import RegistryABI from '../assets/abis/Registry.json';
import SimpleERC721ABI from '../assets/abis/SimpleERC721.json';
import OwnerRegistryABI from '../assets/abis/OwnerRegistry.json';

// Map of ABI names to their actual content
const abiMap: { [key: string]: any } = {
  'L1QueryOwner': L1QueryOwnerABI,
  'L2Relay': L2RelayABI,
  'CommissionRegistry': CommissionRegistryABI,
  'CommissionedArt': CommissionedArtABI,
  'Registry': RegistryABI,
  'SimpleERC721': SimpleERC721ABI,
  'OwnerRegistry': OwnerRegistryABI
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