import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

def get_vyper_contracts(contracts_dir="../contracts") -> List[Path]:
    """Get all Vyper contract files from the contracts directory."""
    contracts_dir_path = Path(__file__).parent / contracts_dir
    return list(contracts_dir_path.glob("*.vy"))

def compile_contracts() -> bool:
    """Compile all contracts using ape compile."""
    try:
        print(f"[{datetime.now()}] Compiling contracts...")
        result = subprocess.run(["ape", "compile"], check=True, capture_output=True, text=True)
        print(f"[{datetime.now()}] Compilation successful.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] Error compiling contracts: {e}")
        print(f"[{datetime.now()}] stdout: {e.stdout}")
        print(f"[{datetime.now()}] stderr: {e.stderr}")
        return False

def extract_abis_to_folder(build_file="../.build/__local__.json", output_dir="../src/assets/abis") -> Dict[str, str]:
    """Extract ABIs from the build file and save them as JSON files to the output directory.
    Returns a dictionary of contract names to file paths."""
    # Get absolute paths relative to the script location
    script_dir = Path(__file__).parent
    build_file_abs = (script_dir / build_file).resolve()
    output_dir_abs = (script_dir / output_dir).resolve()
    
    # Check if the build file exists
    if not os.path.exists(build_file_abs):
        raise FileNotFoundError(f"Build file '{build_file_abs}' not found. Ensure 'ape compile' ran successfully.")

    # Create the output directory if it doesn't exist
    output_dir_abs.mkdir(parents=True, exist_ok=True)

    # Dictionary to store contract name to file path mappings
    contract_files = {}

    # Load the JSON data from the build file
    try:
        with open(build_file_abs, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[{datetime.now()}] Error parsing JSON in {build_file_abs}: {e}")
        raise

    # Access the 'contractTypes' dictionary, default to empty dict if missing
    contract_types = data.get("contractTypes", {})
    
    # Iterate over each contract in 'contractTypes'
    for contract_name, contract_data in contract_types.items():
        # Get the ABI, default to None if not present
        abi = contract_data.get("abi")
        if abi:
            # Define the output file path with .json extension
            output_file = output_dir_abs / f"{contract_name}.json"
            # Write the ABI to a JSON file with indentation for readability
            with open(output_file, "w") as abi_file:
                json.dump(abi, abi_file, indent=2)
            print(f"[{datetime.now()}] Saved ABI for '{contract_name}' to '{output_file}'")
            # Store the relative path for abiLoader.ts
            contract_files[contract_name] = f"../assets/abis/{contract_name}.json"
        else:
            print(f"[{datetime.now()}] No ABI found for '{contract_name}' in {build_file_abs}")
    
    return contract_files

def update_abi_loader(contract_files: Dict[str, str], abi_loader_path="../src/utils/abiLoader.ts"):
    """Update the abiLoader.ts file with the latest contract imports and mappings."""
    script_dir = Path(__file__).parent
    abi_loader_abs = (script_dir / abi_loader_path).resolve()
    
    if not os.path.exists(abi_loader_abs):
        print(f"[{datetime.now()}] abiLoader.ts file not found at '{abi_loader_abs}'")
        return
    
    # Read the current file
    with open(abi_loader_abs, "r") as f:
        content = f.read()
    
    # Create new imports and mapping
    import_lines = []
    mapping_lines = []
    
    for contract_name, file_path in sorted(contract_files.items()):
        import_var = f"{contract_name}ABI"
        import_lines.append(f"import {import_var} from '{file_path}';")
        mapping_lines.append(f"  '{contract_name}': {import_var},")
    
    # Build the new content
    imports_block = "\n".join(import_lines)
    mapping_block = "\n".join(mapping_lines)
    
    # Create the new file content
    new_content = f"""// Import ABIs statically to make them available in the app
{imports_block}

// Map of ABI names to their actual content
const abiMap: {{ [key: string]: any }} = {{
{mapping_block}
}};

/**
 * Get the list of available ABI names
 * @returns Array of available ABI names
 */
export const getAvailableABIs = (): string[] => {{
  return Object.keys(abiMap);
}};

/**
 * Load an ABI by name
 * @param abiName Name of the ABI to load
 * @returns The ABI object or null if not found
 */
export const loadABI = (abiName: string): any => {{
  if (!abiName || !abiMap[abiName]) {{
    console.error(`ABI '${{abiName}}' not found`);
    return null;
  }}
  
  return abiMap[abiName];
}};

/**
 * Get the human-readable method names from an ABI
 * @param abiName Name of the ABI to analyze
 * @returns Array of method names
 */
export const getMethodNames = (abiName: string): string[] => {{
  const abi = loadABI(abiName);
  if (!abi) return [];
  
  return abi
    .filter((item: any) => item.type === 'function')
    .map((item: any) => item.name);
}};

/**
 * Find ABIs that have a specific method
 * @param methodName Method name to search for
 * @returns Array of ABI names that contain the method
 */
export const findABIsWithMethod = (methodName: string): string[] => {{
  return Object.keys(abiMap).filter(abiName => {{
    const abi = abiMap[abiName];
    return abi.some((item: any) => 
      item.type === 'function' && item.name === methodName
    );
  }});
}};

export default {{
  getAvailableABIs,
  loadABI,
  getMethodNames,
  findABIsWithMethod
}}; 
"""
    
    # Write the new content to the file
    with open(abi_loader_abs, "w") as f:
        f.write(new_content)
    
    print(f"[{datetime.now()}] Updated abiLoader.ts with {len(contract_files)} contracts")

def main():
    """Main function to run the ABI extraction process."""
    
    # 1. Get all Vyper contracts
    contracts = get_vyper_contracts()
    contract_names = [c.stem for c in contracts]
    print(f"[{datetime.now()}] Found {len(contracts)} Vyper contracts: {', '.join(contract_names)}")
    
    if not contracts:
        print(f"[{datetime.now()}] No Vyper contracts found to compile, aborting.")
        return
    
    # 2. Compile all contracts
    if not compile_contracts():
        print(f"[{datetime.now()}] Compilation failed, aborting.")
        return
    
    # 3. Extract ABIs to the abis folder
    try:
        contract_files = extract_abis_to_folder()
        if not contract_files:
            print(f"[{datetime.now()}] No ABIs were extracted, aborting.")
            return
    except Exception as e:
        print(f"[{datetime.now()}] Error extracting ABIs: {e}")
        return
    
    # 4. Update abiLoader.ts with the latest contracts
    try:
        update_abi_loader(contract_files)
    except Exception as e:
        print(f"[{datetime.now()}] Error updating abiLoader.ts: {e}")
        return
    
    # 5. Print a summary
    print(f"[{datetime.now()}] ABI extraction and loader update complete!")
    print(f"[{datetime.now()}] Generated {len(contract_files)} ABI files.")
    print(f"[{datetime.now()}] Found contracts: {', '.join(sorted(contract_files.keys()))}")
    
    # Check for any discrepancies
    missing_contracts = [name for name in contract_names if name not in contract_files]
    if missing_contracts:
        print(f"[{datetime.now()}] WARNING: The following contracts were found but their ABIs were not extracted: {', '.join(missing_contracts)}")
        print(f"[{datetime.now()}] This could be due to compilation errors or other issues.")

if __name__ == "__main__":
    main()