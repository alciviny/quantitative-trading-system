import subprocess
import sys

result = subprocess.run([
    sys.executable, 
    r'c:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-quant\scripts\walk_forward_optimized.py'
], capture_output=False)

sys.exit(result.returncode)
