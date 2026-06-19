import os
import sys
import platform
import urllib.request
import zipfile
import tarfile
import subprocess
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def install_binary(url, output_path, extract_member=None, archive_type=None):
    """
    Helper function to download and install binaries.
    Can extract specific files from zip or tar.gz archives.
    """
    print(f"Downloading {url}...")
    try:
        temp_file, _ = urllib.request.urlretrieve(url)
        if archive_type == "zip":
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                member_data = zip_ref.read(extract_member)
                with open(output_path, 'wb') as f:
                    f.write(member_data)
        elif archive_type == "tar.gz":
            with tarfile.open(temp_file, "r:gz") as tar_ref:
                member = tar_ref.extractfile(extract_member)
                with open(output_path, 'wb') as f:
                    f.write(member.read())
        else:
            shutil.copy(temp_file, output_path)
        os.chmod(output_path, 0o755)
        print(f"Successfully installed to {output_path}")
    except Exception as e:
        print(f"Failed to download/install: {e}")

def setup_venv():
    print("--> Setting up Python Virtual Environment (.venv)...")
    try:
        # Run using current python executable
        subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=PROJECT_ROOT, check=True)
        
        # Determine pip executable path
        if platform.system().lower() == "windows":
            pip_path = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "pip")
        else:
            pip_path = os.path.join(PROJECT_ROOT, ".venv", "bin", "pip")
            
        # Upgrade pip
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        print("--> Virtual environment setup successfully and pip upgraded!")
        
        # Install requirements if they exist
        req_file = os.path.join(PROJECT_ROOT, "requirements.txt")
        if os.path.exists(req_file):
            print("--> Found requirements.txt. Installing dependencies...")
            subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    except Exception as e:
        print(f"Error creating virtual environment: {e}")
        print("Please ensure you have python3-venv installed on your system.")

def main():
    system = platform.system().lower()
    print(f"Initializing development environment for OS: {system}")
    
    # 1. Create .bin directory for local tool binaries
    bin_dir = os.path.join(PROJECT_ROOT, ".bin")
    os.makedirs(bin_dir, exist_ok=True)
    print(f"--> Created local binary directory at: {bin_dir}")
    
    # 2. Setup Python Venv
    setup_venv()
    
    # 3. Pluggable Section for custom binaries/tooling setup
    # Developers can uncomment/add custom platform tool installation logic here.
    #
    # Example (Installing kubectl):
    # if "windows" in system:
    #     kubectl_url = "https://dl.k8s.io/release/v1.30.0/bin/windows/amd64/kubectl.exe"
    #     install_binary(kubectl_url, os.path.join(bin_dir, "kubectl.exe"))
    # else:
    #     kubectl_url = "https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl"
    #     install_binary(kubectl_url, os.path.join(bin_dir, "kubectl"))
    
    print("\n--> Environment setup complete!")
    print(f"Local binaries directory: {bin_dir}")
    print("If you installed custom binaries, make sure to add this directory to your system PATH.")

if __name__ == "__main__":
    main()
