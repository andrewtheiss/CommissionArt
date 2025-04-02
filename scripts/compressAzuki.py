import os
import json
from PIL import Image
from io import BytesIO

# Define the input and output folders
input_folder = 'azuki_images'
output_folder = 'azuki_images_avif_1000x1000'

# Create the output folder if it doesn’t exist
os.makedirs(output_folder, exist_ok=True)

# Initialize a dictionary to store compression levels
compression_levels = {}

# Process each PNG file in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith('.png'):
        # Define the output filename
        output_filename = os.path.join(output_folder, filename.replace('.png', '.avif'))
        
        # Check if the AVIF file already exists
        if os.path.exists(output_filename):
            print(f"File {output_filename} already exists, skipping...")
            continue
        
        # Open the PNG image
        img = Image.open(os.path.join(input_folder, filename))
        
        # Resize the image to 1000x1000 using LANCZOS for high-quality downsampling
        img = img.resize((1000, 1000), Image.LANCZOS)
        
        # Convert to 'RGBA' if the image has an alpha channel, otherwise to 'RGB'
        if 'A' in img.getbands():
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
        
        # Binary search to find the highest quality under 43KB
        low = 1
        high = 100
        while low < high:
            mid = (low + high + 1) // 2  # Bias towards higher quality
            buffer = BytesIO()  # In-memory buffer to test file size
            img.save(buffer, format='AVIF', quality=mid)
            size = buffer.tell()  # Get size in bytes
            if size <= 43 * 1024:  # 43KB = 43 * 1024 bytes
                low = mid  # Size is acceptable, try higher quality
            else:
                high = mid - 1  # Size is too large, try lower quality
        
        # Save the image with the optimal quality
        img.save(output_filename, format='AVIF', quality=low)
        
        # Record the compression level (quality) for this image
        compression_levels[os.path.basename(output_filename)] = low
        
        # Verify the saved file size and warn if it exceeds 43KB
        if os.path.getsize(output_filename) > 43 * 1024:
            print(f"Warning: {output_filename} exceeds 43KB")

# Save the compression levels to a JSON file in the base directory
with open('compressedSizes_avif_1000x1000.json', 'w') as json_file:
    json.dump(compression_levels, json_file, indent=4)