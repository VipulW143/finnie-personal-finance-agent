"""Verify/extract a source ZIP; optionally install and test it in a fresh venv."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import socket
import subprocess
import sys
from tempfile import mkdtemp
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import urlopen
import venv
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]


def verify_archive(path):
    with ZipFile(path) as archive:
        names=archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError('Archive has duplicate entries')
        for name in names:
            parts=PurePosixPath(name).parts
            if not parts or parts[0] != 'finnie-submission' or '..' in parts or '\\' in name:
                raise ValueError('Archive contains an unexpected path')
            if any(p in {'.env','.venv','.finnie','__pycache__','reports'} for p in parts):
                raise ValueError('Archive contains excluded local state')
        manifest=json.loads(archive.read('finnie-submission/MANIFEST.json'))
        expected={'finnie-submission/MANIFEST.json'}
        for record in manifest['files']:
            name='finnie-submission/'+record['path']
            expected.add(name)
            data=archive.read(name)
            if len(data) != record['bytes'] or sha256(data).hexdigest() != record['sha256']:
                raise ValueError(f"Manifest mismatch: {record['path']}")
        if expected != set(names):
            raise ValueError('Archive entries and manifest differ')
        if archive.testzip() is not None:
            raise ValueError('Archive CRC check failed')
        return manifest


def require_virtualenv(python, env=None):
    """Refuse base interpreters before any pip mutation; preserve symlink paths."""
    python=Path(os.path.abspath(python))
    subprocess.run([str(python),'-c',
                    "import sys; assert sys.prefix != sys.base_prefix, 'Use a disposable virtual environment, not base Python'"],
                   env=env,check=True,capture_output=True,text=True)
    return python


def check_server(python,source,env):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0))
        port=probe.getsockname()[1]
    process=subprocess.Popen([str(python),'-m','streamlit','run','src/finnie/ui.py',
                              '--server.headless=true','--server.address=127.0.0.1',
                              f'--server.port={port}','--browser.gatherUsageStats=false'],
                             cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        deadline=monotonic()+25
        while monotonic()<deadline:
            if process.poll() is not None:
                raise RuntimeError('Headless Streamlit exited before becoming healthy')
            try:
                with urlopen(f'http://127.0.0.1:{port}/_stcore/health',timeout=1) as response:
                    if response.read().strip()==b'ok':
                        return 'passed: loopback health endpoint returned ok; app paths also exercised by AppTest'
            except (URLError,TimeoutError):
                pass
            sleep(.1)
        raise RuntimeError('Headless Streamlit did not become healthy within 25 seconds')
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',nargs='?',type=Path,default=ROOT/'dist/finnie-submission.zip')
    parser.add_argument('--install',action='store_true',help='Download dependencies and test the extracted project')
    parser.add_argument('--python',type=Path,help='Use an existing disposable venv interpreter for --install')
    args=parser.parse_args()
    archive=args.archive.resolve()
    manifest=verify_archive(archive)
    report=dict(archive=archive.name,archive_sha256=sha256(archive.read_bytes()).hexdigest(),files=len(manifest['files']),manifest='passed')
    if args.install:
        work=Path(mkdtemp(prefix='finnie-verified-'))
        with ZipFile(archive) as zipped:
            zipped.extractall(work)
        source=work/'finnie-submission'
        if args.python:
            # Preserve the venv executable path: resolve() can follow it into base Python.
            python=Path(os.path.abspath(args.python))
        else:
            venv.EnvBuilder(with_pip=True).create(work/'venv')
            python=work/('venv/Scripts/python.exe' if os.name=='nt' else 'venv/bin/python')
        env=dict(os.environ)
        for name in ('PYTHONPATH','OPENAI_API_KEY','APCA_API_KEY_ID','APCA_API_SECRET_KEY','FINNIE_MODEL','OPENAI_EMBEDDING_MODEL'):
            env.pop(name,None)
        env['LANGSMITH_TRACING']='false'
        env['LANGCHAIN_TRACING_V2']='false'
        python=require_virtualenv(python,env)
        def run(*arguments,input=None):
            return subprocess.run([str(python),*arguments],cwd=source,env=env,check=True,text=True,input=input)
        run('-m','pip','install','-r','requirements-lock.txt')
        run('-m','pip','install','-e','.[dev]')
        run('-m','pip','check')
        run('-c',"from pathlib import Path; import finnie; from finnie.knowledge import load_sources; from finnie.goals import project_goal; import json; assert Path(finnie.__file__).resolve().is_relative_to(Path.cwd()/'src'); assert len(load_sources())==50; assert not Path('.env').exists(); assert not Path('.finnie').exists(); assert project_goal(json.loads(Path('samples/goal.json').read_text()))['monthly_contribution']==199.74; print('Extracted source/resource/sample checks passed')")
        run('scripts/check_quality.py')
        run('scripts/evaluate_project.py')
        run('-m','finnie.app',input='quit\n')
        report.update(installation='passed in disposable venv',dependency_check='passed',
                      source_resources='passed: extracted code, 50 sources, no .env or prebuilt cache',
                      quality_gate='passed; see extracted reports',offline_benchmarks='passed; FAISS correctly unavailable without cache',
                      cli='passed: startup and quit without credentials',streamlit=check_server(python,source,env),
                      python=str(python),extracted_source=str(source))
    target=ROOT/'reports'
    target.mkdir(exist_ok=True)
    (target/'package_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
