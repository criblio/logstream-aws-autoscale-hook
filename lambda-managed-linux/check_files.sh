#!/bin/bash
# Simple script for checking if any files exist in queue directories, and exiting with an exit value if so.

dirs=$QUEUES
if [ -z "$dirs" ]; then

  echo "No Directories Specified"
  exit 126
fi
IFS=',' read -a dirs <<< "$QUEUES"

for dir in ${dirs[@]}; do
  echo "Checking $dir"
  numfiles=$(find $dir -type f | wc -l)
  if [ $numfiles -gt 0 ]; then
    echo "Files in $dir - Cancelling Termination"
    exit 255
  fi
done

