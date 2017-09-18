#!/bin/bash

cd templates
echo "Re-compiling changed templates in $(pwd)"
make all
cd ..

echo "Starting controller.py on port 8080"
python controller.py 8080
