import { ethers } from 'ethers';
import ethersService from './ethers-service';

// Demo ABI - a simple storage contract
const demoABI = [
  {
    "inputs": [],
    "name": "retrieve",
    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "uint256", "name": "num", "type": "uint256"}],
    "name": "store",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  }
];

export const getDemoContract = (contractAddress: string) => {
  const provider = ethersService.getProvider();
  if (!provider) {
    throw new Error("Provider not connected");
  }
  
  return new ethers.Contract(contractAddress, demoABI, provider);
};

export const getDemoContractWithSigner = async (contractAddress: string) => {
  const signer = await ethersService.getSigner();
  if (!signer) {
    throw new Error("Wallet not connected");
  }
  
  return new ethers.Contract(contractAddress, demoABI, signer);
};

// Example function to interact with contract
export const storeValue = async (contractAddress: string, value: number) => {
  try {
    const contract = await getDemoContractWithSigner(contractAddress);
    const tx = await contract.store(value);
    return await tx.wait();
  } catch (error) {
    console.error("Error storing value:", error);
    throw error;
  }
};

// Example function to read from contract
export const retrieveValue = async (contractAddress: string) => {
  try {
    const contract = getDemoContract(contractAddress);
    return await contract.retrieve();
  } catch (error) {
    console.error("Error retrieving value:", error);
    throw error;
  }
}; 