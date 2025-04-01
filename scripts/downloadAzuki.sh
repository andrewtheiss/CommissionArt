#!/bin/bash

# Directory to save the images
OUTPUT_DIR="./azuki_images"
mkdir -p "$OUTPUT_DIR"

# Base URL
BASE_URL="https://ipfs.io/ipfs/QmYDvPAXtiJg7s8JdRBSLWdgSphQdac8j1YuQNNxcGE1hg"

# Loop from 0 to 9999
for i in {5471..9999}; do
    # Construct the full URL
    URL="$BASE_URL/$i.png"
    # Output file path
    FILE="$OUTPUT_DIR/$i.png"
    
    echo "Downloading $URL to $FILE..."
    curl -s -o "$FILE" "$URL" --fail
    
    # Check if the download was successful
    if [ $? -eq 0 ]; then
        echo "Successfully downloaded $i.png"
    else
        echo "Failed to download $i.png"
        # Optionally remove failed download
        rm -f "$FILE"
    fi
    
    # Optional: Add a small delay to avoid overwhelming the server
    sleep 0.1
done

echo "Download complete!"