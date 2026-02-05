import os
import urllib.request
import zipfile
import shutil
import re
import subprocess
import sys
import time

def uninstall_bad_packages():
    print("Uninstalling conflicting packages...")
    packages = ["maia2", "numpy", "scipy"]
    for pkg in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", pkg])
        except Exception:
            pass

def install_maia_patched():
    print("Downloading Maia 2...")
    url = "https://github.com/CSSLab/maia2/archive/refs/heads/main.zip"
    zip_path = "maia2_main.zip"
    extract_path = "maia2_install_temp"

    # Download
    try:
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:
        print(f"Failed to download: {e}")
        return

    # Extract
    print("Extracting...")
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    # Find extracted folder
    content_dir = os.path.join(extract_path, os.listdir(extract_path)[0])
    
    # Patch pyproject.toml
    toml_path = os.path.join(content_dir, "pyproject.toml")
    if os.path.exists(toml_path):
        print("Patching pyproject.toml...")
        with open(toml_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove strict versioning
        new_content = re.sub(r'numpy==[\d\.]+', 'numpy', content)
        new_content = re.sub(r'numpy>=[\d\.]+', 'numpy', new_content)
        new_content = re.sub(r'torch==[\d\.]+', 'torch', new_content)
        new_content = re.sub(r'pyzstd==[\d\.]+', 'pyzstd', new_content)
        
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    
    # Patch requirements.txt
    req_path = os.path.join(content_dir, "requirements.txt")
    if os.path.exists(req_path):
         print("Patching requirements.txt inside package...")
         with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()
         new_content = re.sub(r'numpy==[\d\.]+', 'numpy', content)
         new_content = re.sub(r'torch==[\d\.]+', 'torch', new_content)
         new_content = re.sub(r'pyzstd==[\d\.]+', 'pyzstd', new_content)
         with open(req_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    # Install
    print("Installing patched Maia 2...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", content_dir])
    
    # Cleanup
    print("Cleaning up...")
    try:
        os.remove(zip_path)
        shutil.rmtree(extract_path)
    except:
        pass

def reinstall_deps():
    print("Reinstalling correct dependencies...")
    # Allow latest numpy/scipy for Python 3.13 compatibility
    # maia2 might have issues with numpy 2.0, but we'll patch/fix them if they occur
    # rather than failing installation.
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "scipy"])
    # Install other deps from requirements.txt
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

if __name__ == "__main__":
    uninstall_bad_packages()
    reinstall_deps()
    install_maia_patched()
    print("\nDONE! You can now run the bot.")
