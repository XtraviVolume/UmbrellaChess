import subprocess
import sys

def force_fix_numpy():
    print("Uninstalling numpy...")
    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "numpy"])
    
    print("Installing numpy<2.0.0...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy<2.0.0"])
    
    print("Verifying...")
    try:
        import numpy
        print(f"NumPy version: {numpy.__version__}")
        if int(numpy.__version__.split('.')[0]) >= 2:
            print("ERROR: NumPy 2.x is still installed!")
        else:
            print("SUCCESS: NumPy version is compatible (<2).")
    except ImportError:
        print("ERROR: NumPy not installed properly.")

if __name__ == "__main__":
    force_fix_numpy()
