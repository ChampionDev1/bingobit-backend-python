#!/bin/bash
# Generate Python code from proto files

echo "Generating Python code from proto files..."

# Create proto directory if it doesn't exist
mkdir -p proto

# Generate onchain proto
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    --pyi_out=./proto \
    proto/onchain.proto

# Generate systemwallet proto
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    --pyi_out=./proto \
    proto/systemwallet.proto

echo "Proto files generated successfully!"
echo ""
echo "Generated files:"
echo "  - proto/onchain_pb2.py"
echo "  - proto/onchain_pb2_grpc.py"
echo "  - proto/systemwallet_pb2.py"
echo "  - proto/systemwallet_pb2_grpc.py"
