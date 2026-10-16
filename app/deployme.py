"""Publish using a named rsconnect server registered in your own terminal.

No credentials are stored here. Instructions live in the root README.
"""
from pathlib import Path
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-name', default='course', help='Locally registered rsconnect server name')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    if not (here / 'manifest.json').exists():
        raise SystemExit('First run: python app/manifestme.py')
    executable = Path(sys.executable).parent / ('rsconnect.exe' if sys.platform == 'win32' else 'rsconnect')
    subprocess.run([str(executable), 'deploy', 'manifest', str(here / 'manifest.json'),
                    '--name', args.server_name], check=True)


if __name__ == '__main__': main()
