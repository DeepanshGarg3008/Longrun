#!/bin/bash

INPUT_FILE="/home/ubuntu/longrun/symbols.txt"
BASE_URL="https://images.dhan.co/symbol/"
OUTPUT_DIR="/home/ubuntu/longrun/images"

mkdir -p "$OUTPUT_DIR"

while IFS= read -r symbol; do
  URL="${BASE_URL}${symbol}.png"
  OUTPUT_FILE="${OUTPUT_DIR}/${symbol}.png"
  echo "Downloading $symbol to $OUTPUT_FILE"
  wget -q "$URL" -O "$OUTPUT_FILE"
  sleep 1
done < "$INPUT_FILE"