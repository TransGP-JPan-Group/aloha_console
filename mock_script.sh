#!/bin/bash
echo "Received arguments: $*"

for i in {1..10}; do
    echo "Mock output $i"
    sleep 1
done
