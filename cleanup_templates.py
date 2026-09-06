import os
import shutil

# Define paths to clean
TARGET_DIRS = [
    os.path.join("static", "adminlte"),
    os.path.join("staticfiles", "adminlte")
]

def clean_unlinked_adminlte():
    deleted_count = 0
    for target in TARGET_DIRS:
        if os.path.exists(target):
            try:
                shutil.rmtree(target)
                print(f"[DELETED FOLDER] {target}")
                deleted_count += 1
            except Exception as e:
                print(f"[ERROR] Could not delete {target}: {e}")
        else:
            print(f"[NOT FOUND] {target}")

    print(f"\nCleanup completed. Removed {deleted_count} vendor template directories.")

if __name__ == "__main__":
    clean_unlinked_adminlte()