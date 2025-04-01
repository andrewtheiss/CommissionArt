import json
import os
from datetime import datetime
from pathlib import Path

def extract_abis_to_folder(build_file="../.build/__local__.json", output_dir="../src/assets/abis"):
    """Extract ABIs from the build file and save them as JSON files to the output directory."""
    # Get absolute paths relative to the script location
    script_dir = Path(__file__).parent
    build_file_abs = (script_dir / build_file).resolve()
    output_dir_abs = (script_dir / output_dir).resolve()
    
    # Check if the build file exists
    if not os.path.exists(build_file_abs):
        raise FileNotFoundError(f"Build file '{build_file_abs}' not found. Ensure 'ape compile' ran successfully.")

    # Create the output directory if it doesn't exist
    output_dir_abs.mkdir(parents=True, exist_ok=True)

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
        else:
            print(f"[{datetime.now()}] No ABI found for '{contract_name}' in {build_file_abs}")

# Example usage
if __name__ == "__main__":
    extract_abis_to_folder()