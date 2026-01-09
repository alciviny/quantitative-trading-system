
import os
from pathlib import Path

def check_scripts():
    scripts_dir = Path('co-piloto-quant/scripts')
    files_to_check = list(scripts_dir.glob('*.py'))
    
    missing_modification = []
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "sys.path.append(str(Path(__file__).resolve().parent.parent))" not in content:
                missing_modification.append(file_path.name)
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")

    if not missing_modification:
        print("All script files have the sys.path modification.")
    else:
        print("The following files are missing the sys.path modification:")
        for file_name in missing_modification:
            print(file_name)

if __name__ == '__main__':
    check_scripts()
