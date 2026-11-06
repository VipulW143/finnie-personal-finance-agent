"""Submission allowlist and manifest checks without reading any real secrets."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import os
import subprocess
import sys
import venv
from zipfile import ZipFile

from scripts.build_submission import ROOT_FILES, build_submission, collect_files
from scripts.validate_submission import verify_archive, require_virtualenv


class SubmissionTests(unittest.TestCase):
    def fixture(self,root):
        for name in ROOT_FILES:
            (root/name).write_text('example')
        (root/'src/finnie').mkdir(parents=True)
        (root/'src/finnie/app.py').write_text('print("example")')

    def test_package_excludes_local_state_and_hashes_every_included_file(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            self.fixture(root)
            for path in ('.env','AGENTS.md','docs/demo-video.md','.venv/secret.txt','.finnie/index.json','reports/private.json','src/finnie/__pycache__/app.pyc','reference.docx'):
                target=root/path
                target.parent.mkdir(exist_ok=True,parents=True)
                target.write_text('dummy local state')
            output=build_submission(root)
            with ZipFile(output) as archive:
                names=archive.namelist()
                for bad in ('.env','AGENTS.md','docs/demo-video.md','.venv/secret.txt','.finnie/index.json','reports/private.json','reference.docx'):
                    self.assertNotIn('finnie-submission/'+bad,names)
                manifest=json.loads(archive.read('finnie-submission/MANIFEST.json'))
                self.assertEqual(len(names),len(manifest['files'])+1)
                for entry in manifest['files']:
                    data=archive.read('finnie-submission/'+entry['path'])
                    self.assertEqual(sha256(data).hexdigest(),entry['sha256'])
            self.assertEqual(len(verify_archive(output)["files"]),len(manifest["files"]))
            self.assertTrue(output.with_suffix('.zip.sha256').exists())

    def test_linked_or_missing_required_files_are_rejected(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ValueError):
                collect_files(root)
            self.fixture(root)
            (root/'src/finnie/link.py').symlink_to(root/'README.md')
            with self.assertRaisesRegex(ValueError,'Linked'):
                collect_files(root)

    def test_modified_content_is_detected_by_manifest(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            self.fixture(root)
            output=build_submission(root)
            altered=root/'altered.zip'
            with ZipFile(output) as original, ZipFile(altered,'w') as changed:
                for name in original.namelist():
                    changed.writestr(name,b'changed content' if name.endswith('/README.md') else original.read(name))
            with self.assertRaisesRegex(ValueError,'Manifest mismatch'):
                verify_archive(altered)

    def test_unexpected_paths_are_rejected(self):
        with TemporaryDirectory() as directory:
            archive=Path(directory)/'bad.zip'
            with ZipFile(archive,'w') as zipped:
                zipped.writestr('../outside.txt','not allowed')
            with self.assertRaisesRegex(ValueError,'unexpected path'):
                verify_archive(archive)

    def test_verifier_preserves_symlinked_venv_and_refuses_base_python(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)/'venv'
            venv.EnvBuilder(with_pip=False,symlinks=True).create(root)
            python=root/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            self.assertEqual(require_virtualenv(python),python.absolute())
            with self.assertRaises(subprocess.CalledProcessError):
                require_virtualenv(sys._base_executable)

    def test_credential_like_literals_are_not_packaged(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            self.fixture(root)
            # Construct the dummy pattern so the test source itself is safe to package.
            (root/'README.md').write_text('sk-'+'a'*25)
            with self.assertRaisesRegex(ValueError,'Credential-like'):
                build_submission(root)


if __name__=='__main__':
    unittest.main()
