import os

from dotenv import load_dotenv

load_dotenv()

# Path to the IT / Home Lab markdown note
NOTE_PATH = os.getenv(
    "NOTE_PATH",
    os.path.expanduser("~/Notes/Information Technology/README.md"),
)

# kubectl context to use for the prod cluster
K3S_CONTEXT = os.getenv("K3S_CONTEXT", "k3s-prod")

# Proxmox node to SSH into for ZFS pool data (pve15 has the storage pools)
PVE_STORAGE_HOST = os.getenv("PVE_STORAGE_HOST", "pve15")

# SSH user for Proxmox nodes (root)
PVE_SSH_USER = os.getenv("PVE_SSH_USER", "root")

# SSH key to use (defaults to system default, i.e. ~/.ssh/id_rsa or ssh-agent)
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", "")

# SSH connection timeout in seconds
SSH_TIMEOUT = int(os.getenv("SSH_TIMEOUT", "10"))
