#!/bin/bash

# Check if at least one argument was provided
if [ "$#" -lt 1 ]; then
    echo "Error: Directory path is required."
    echo "Usage: $0 <directory> [extension1] [extension2] ..."
    exit 1
fi

# First argument is the directory that will be cleaned
directory="$1"

# Remove the first argument from the argument list
shift

# Check if the directory exists
if [ ! -d "$directory" ]; then
    echo "Error: Directory '$directory' does not exist."
    exit 1
fi

# If no extensions were specified, use .tmp by default
if [ "$#" -eq 0 ]; then
    extensions=(".tmp")
else
    extensions=("$@")
fi

deleted_count=0

# Process every specified extension
for extension in "${extensions[@]}"; do

    # Add a dot if the user entered tmp instead of .tmp
    if [[ "$extension" != .* ]]; then
        extension=".$extension"
    fi

    # Find and delete matching files
    while IFS= read -r -d '' file; do
        if rm "$file"; then
            echo "Deleted: $file"
            deleted_count=$((deleted_count + 1))
        fi
    done < <(find "$directory" -type f -name "*$extension" -print0)

done

echo "Deleted files: $deleted_count"
