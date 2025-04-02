#!/bin/bash

# Directory to save the images
OUTPUT_DIR="./azuki_images"
mkdir -p "$OUTPUT_DIR"

# Base URL
BASE_URL="https://ipfs.io/ipfs/QmYDvPAXtiJg7s8JdRBSLWdgSphQdac8j1YuQNNxcGE1hg"

# Loop from 0 to 9999
for i in {0..9999}; do
    # Output file path
    FILE="$OUTPUT_DIR/$i.png"
    
    # Check if file already exists
    if [ -f "$FILE" ]; then
        echo "File $i.png already exists, skipping..."
        continue
    fi
    
    # Construct the full URL
    URL="$BASE_URL/$i.png"
    
    echo "Downloading $URL to $FILE..."
    curl -s -o "$FILE" "$URL" --fail
    
    # Check if the download was successful
    if [ $? -eq 0 ]; then
        echo "Successfully downloaded $i.png"
    else
        echo "Failed to download $i.png"
        # Remove failed download
        rm -f "$FILE"
    fi
    
    # Optional: Add a small delay to avoid overwhelming the server
    sleep 0.5
done

echo "Download complete!"