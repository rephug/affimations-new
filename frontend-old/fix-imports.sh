#!/bin/bash
# This script updates import paths in React components

echo "Fixing import paths in source files..."

# Find all JavaScript files in the src directory
FILES=$(find src -name "*.js")

for FILE in $FILES; do
  echo "Processing $FILE..."
  
  # Fix component imports
  sed -i 's|../components/|../../components/|g' $FILE
  
  # Fix relative path imports based on current directory depth
  DEPTH=$(echo $FILE | tr -cd '/' | wc -c)
  PARENT_PATH=$(printf '../%.0s' $(seq 1 $((DEPTH-1))))
  
  # Update specific imports
  sed -i "s|'../context/AuthContext'|'${PARENT_PATH}context/AuthContext'|g" $FILE
  sed -i "s|'../services/supabase'|'${PARENT_PATH}services/supabase'|g" $FILE
  sed -i "s|'../theme'|'${PARENT_PATH}theme'|g" $FILE
done

echo "Import paths fixed!"
