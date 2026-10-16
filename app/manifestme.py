"""Copy the public synthetic fixtures and generate a real Connect manifest locally."""
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    source = HERE.parent / 'data'
    if source.exists():
        shutil.copytree(source, HERE / 'data', dirs_exist_ok=True)
    # Match the repository's LF checkout rules before calculating file hashes.
    for path in HERE.rglob('*'):
        if path.is_file() and 'starter_reference' not in path.parts and path.suffix in {'.py', '.txt', '.md', '.csv', '.json'}:
            content = path.read_bytes()
            if b'\r\n' in content:
                path.write_bytes(content.replace(b'\r\n', b'\n'))
    executable = Path(sys.executable).parent / ('rsconnect.exe' if sys.platform == 'win32' else 'rsconnect')
    if not executable.exists():
        raise SystemExit('Install publishing tools first: python -m pip install -r app/requirements-deploy.txt')
    subprocess.run([str(executable), 'write-manifest', 'shiny', str(HERE), '--entrypoint', 'dashboard:app',
                    '--overwrite', '--exclude', 'starter_reference/**', '--exclude', '__pycache__/**',
                    '--exclude', 'browser_check.py', '--exclude', '*.png'], check=True)


if __name__ == '__main__': main()
