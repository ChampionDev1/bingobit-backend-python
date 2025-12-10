"""
Generate Python code from proto files
Cross-platform proto generation script
"""
import subprocess
import sys
import os
import re

def fix_grpc_imports(filepath):
    """Fix import statements in generated gRPC files"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix imports: "import xxx_pb2" -> "from . import xxx_pb2"
    content = re.sub(
        r'^import (\w+_pb2) as',
        r'from . import \1 as',
        content,
        flags=re.MULTILINE
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def generate_proto_files():
    """Generate Python code from .proto files"""
    
    print("Generating Python code from proto files...")
    print("-" * 60)
    
    proto_files = [
        "proto/onchain.proto",
        "proto/systemwallet.proto"
    ]
    
    for proto_file in proto_files:
        if not os.path.exists(proto_file):
            print(f"ERROR: {proto_file} not found!")
            sys.exit(1)
        
        print(f"\nProcessing: {proto_file}")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "grpc_tools.protoc",
                "-I./proto",
                "--python_out=./proto",
                "--grpc_python_out=./proto",
                "--pyi_out=./proto",
                proto_file
            ], check=True, capture_output=True, text=True)
            
            print(f"✓ Generated successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to generate from {proto_file}")
            print(f"Error: {e.stderr}")
            sys.exit(1)
        except FileNotFoundError:
            print("\nERROR: grpc_tools not found!")
            print("Please install: pip install grpcio-tools")
            sys.exit(1)
    
    # Fix imports in generated gRPC files
    print("\nFixing import statements...")
    grpc_files = [
        "proto/onchain_pb2_grpc.py",
        "proto/systemwallet_pb2_grpc.py"
    ]
    
    for grpc_file in grpc_files:
        if os.path.exists(grpc_file):
            fix_grpc_imports(grpc_file)
            print(f"✓ Fixed imports in {grpc_file}")
    
    print("\n" + "-" * 60)
    print("✓ All proto files generated successfully!")
    print("\nGenerated files:")
    
    generated_files = [
        "proto/onchain_pb2.py",
        "proto/onchain_pb2_grpc.py",
        "proto/onchain_pb2.pyi",
        "proto/systemwallet_pb2.py",
        "proto/systemwallet_pb2_grpc.py",
        "proto/systemwallet_pb2.pyi"
    ]
    
    for f in generated_files:
        if os.path.exists(f):
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} (not found)")
    
    print("-" * 60)

if __name__ == "__main__":
    generate_proto_files()
