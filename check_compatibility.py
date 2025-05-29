#!/usr/bin/env python3
"""
Python and Dependency Compatibility Checker for DiarizationScoring
This script checks if your Python version and environment are compatible.
"""

import sys
import subprocess
from packaging import version

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Python Version Check")
    print("=" * 30)
    
    python_version = version.parse(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"Current Python version: {python_version}")
    
    # Check for compatibility
    if python_version >= version.parse("3.12.0"):
        print("⚠️  WARNING: Python 3.12+ detected!")
        print("   This version may have compatibility issues with PyTorch dependencies.")
        print("   Recommended: Python 3.10 or 3.11")
        return False
    elif python_version >= version.parse("3.8.0"):
        print("✅ Python version is compatible!")
        return True
    else:
        print("❌ Python version too old! Minimum required: 3.8")
        return False

def check_critical_packages():
    """Check if critical packages can be imported."""
    print("\n📦 Critical Package Check")
    print("=" * 30)
    
    critical_packages = [
        ('torch', 'PyTorch'),
        ('flask', 'Flask'),
        ('librosa', 'Librosa'),
        ('transformers', 'Transformers'),
        ('numpy', 'NumPy')
    ]
    
    success_count = 0
    
    for package, display_name in critical_packages:
        try:
            __import__(package)
            print(f"✅ {display_name}: OK")
            success_count += 1
        except ImportError as e:
            print(f"❌ {display_name}: NOT FOUND ({e})")
        except Exception as e:
            print(f"⚠️  {display_name}: ERROR ({e})")
    
    print(f"\nPackages working: {success_count}/{len(critical_packages)}")
    return success_count == len(critical_packages)

def check_torch_compile():
    """Check if torch.compile is available."""
    print("\n🔥 Torch Compile Check")
    print("=" * 30)
    
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        
        # Try to use torch.compile
        @torch.compile
        def simple_function(x):
            return x * 2
        
        result = simple_function(torch.tensor([1.0, 2.0, 3.0]))
        print("✅ torch.compile is working!")
        return True
        
    except Exception as e:
        print(f"❌ torch.compile error: {e}")
        print("   This is expected on Python 3.12+ with PyTorch < 2.4")
        return False

def main():
    """Main compatibility check."""
    print("DiarizationScoring Compatibility Checker")
    print("=" * 50)
    
    python_ok = check_python_version()
    packages_ok = check_critical_packages()
    torch_compile_ok = check_torch_compile()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    if python_ok and packages_ok:
        print("✅ Your environment appears to be compatible!")
        if not torch_compile_ok:
            print("⚠️  Note: torch.compile may not work (this is okay for basic functionality)")
    else:
        print("❌ Compatibility issues detected!")
        print("\n🔧 Recommended fixes:")
        if not python_ok:
            print("   • Use Python 3.10 or 3.11")
            print("   • Run: ./setup_python.sh")
        if not packages_ok:
            print("   • Install dependencies: pip install -r requirements.txt")
            print("   • Create virtual environment: ./setup_venv.sh")
    
    return 0 if (python_ok and packages_ok) else 1

if __name__ == "__main__":
    sys.exit(main()) 