#!/bin/bash
echo "Received arguments: $*"

for i in {1..10}; do
    echo "Mock output $i"
    if [ $i -eq 5 ]; then
        echo "Mock error" 1>&2
    fi
    sleep 1
done
