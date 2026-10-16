"""One-command local start: py app/testme.py (Windows), python app/testme.py elsewhere."""
from pathlib import Path
import importlib.metadata
import os
import subprocess
import sys
import venv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main():
    if sys.prefix == sys.base_prefix:
        environment = ROOT / '.venv'
        executable = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not executable.exists():
            print('Creating a local Python environment...', flush=True)
            venv.create(environment, with_pip=True)
        raise SystemExit(subprocess.call([str(executable), str(HERE / 'testme.py')]))
    missing = []
    for requirement in (HERE / 'requirements.txt').read_text().splitlines():
        if not requirement.strip() or requirement.startswith('#'): continue
        name, version = requirement.split('==')
        try: installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: installed = None
        if installed != version: missing.append(requirement)
    if missing:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(HERE / 'requirements.txt')], check=True)
    from shiny import run_app
    print('Open http://127.0.0.1:8000 · Stop with Ctrl+C', flush=True)
    run_app('dashboard:app', app_dir=str(HERE), port=8000, host='127.0.0.1', launch_browser=False)


if __name__ == '__main__': main()
