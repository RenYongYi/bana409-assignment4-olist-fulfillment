"""Execute a notebook using this exact Python environment, in the project directory."""
from pathlib import Path
import os
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

root = Path(__file__).resolve().parents[1]
path = root / sys.argv[1]
os.environ.setdefault("MPLCONFIGDIR", "/tmp/bana409-mpl")
os.environ.setdefault("IPYTHONDIR", "/tmp/bana409-ipython")
nb = nbformat.read(path, as_version=4)
manager = KernelManager(kernel_name="python3")
manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
client = NotebookClient(nb, km=manager, timeout=900, resources={"metadata": {"path": str(root)}}, allow_errors=False)
client.execute()
nbformat.write(nb, path)
print("Executed:", path)
print("Code cells:", sum(c.cell_type == "code" for c in nb.cells))
print("Error outputs:", sum(o.output_type == "error" for c in nb.cells if c.cell_type == "code" for o in c.outputs))
