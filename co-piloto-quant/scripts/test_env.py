import sys

print("--- Python Environment Info ---")
print(f"Executable: {sys.executable}")
print("\n--- sys.path ---")
for p in sys.path:
    print(p)
print("\n--- Testing Import ---")
try:
    import co_piloto_quant
    print("Successfully imported 'co_piloto_quant'")
    print(f"Location: {co_piloto_quant.__file__}")
except ImportError as e:
    print(f"Failed to import 'co_piloto_quant': {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
