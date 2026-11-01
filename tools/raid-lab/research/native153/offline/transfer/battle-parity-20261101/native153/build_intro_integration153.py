"""Freeze source/mock checks only for original intro restoration plus strict RNG gates."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE/'practice-intro-rng-integration3.json'
    if output.exists():
        raise FileExistsError('Preserve immutable reviewed integration proof')
    names = ['practice_geometry.js', 'practice_probe.js', 'practice_rng_state_verifier.js',
             'archive_practice153.py', 'test_practice_cutscene_boundary.js', 'test_practice_intro_boundary.js',
             'test_practice_rng_probe_boundary.js', 'test_practice_rng_state_verifier.js',
             'test_practice_packet_writer.js', 'test_stage_cutscene_resources.py',
             'rng-state/archive_gate.py', 'rng-state/test_archive_gate.py',
             'practice-cutscene-control-binding.json', 'practice-cutscene-control-source.json',
             'practice-cutscene-private-builtins1.json']
    before = {name: sha(HERE/name) for name in names}
    commands = [['node', '--check', str(HERE/'practice_geometry.js')],
                ['node', '--check', str(HERE/'practice_probe.js')],
                ['node', str(HERE/'test_practice_cutscene_boundary.js')],
                ['node', str(HERE/'test_practice_intro_boundary.js')],
                ['node', str(HERE/'test_practice_rng_probe_boundary.js')],
                ['node', str(HERE/'test_practice_packet_writer.js')],
                [sys.executable, '-m', 'unittest', 'discover', '-s', str(HERE), '-p', 'test_stage_cutscene_resources.py', '-v'],
                [sys.executable, '-m', 'unittest', 'discover', '-s', str(HERE/'rng-state'), '-p', 'test_archive_gate.py', '-v']]
    results = []
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        results.append({'argv': command, 'exitCode': result.returncode,
                        'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            raise RuntimeError(json.dumps(results[-1]))
    if before != {name: sha(HERE/name) for name in names}:
        raise ValueError('Source changed while checking current integration')
    old = HERE/'practice-full-rng-gate-integration2.json'
    report = {'schemaVersion': 1,
              'scope': 'Original serialized intro controller role16 and read-only OnStart intro/RNG gates; source/mock/builtin checks only',
              'sourceHashes': before, 'commands': results, 'inputsUnchanged': True,
              'nativeRunPerformed': False, 'candidateFrozen': False,
              'priorEvidencePreserved': {'path': str(old), 'sha256': sha(old), 'rewritten': False},
              'unchangedRngReaderControls': {'sourceSha256': before['practice_rng_state_verifier.js'],
                   'testSourceSha256': before['test_practice_rng_state_verifier.js'],
                   'priorPassingReceipt': 'practice-full-rng-gate-integration2.json'},
              'behavior': 'Original CutSceneControl.OnLoading writes its own serialized director duration. No host duration/clock/RNG writes; full56-element RNG state guards remain strict.',
              'stagerNote': 'Final stager source is bound independently by reviewed candidate plan; omitted from this receipt to avoid a receipt-hash/source-hash cycle.'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'path': str(output), 'sha256': sha(output), 'commandsPassed': len(results),
                      'nativeRunPerformed': False, 'candidateFrozen': False}))


if __name__ == '__main__':
    main()
