"""Freeze two exact current153 Intercept entry bodies; no represented/native call."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
PROCESS = '38011bccaf2f41fcf9e95b42b2974c45949432c7313d4e4e5b25dd709650bc77'
ENCOUNTER = 'c33edc642e1840ec116ccbc5f8405a406ce2efa99107789b2109aa9d5421fded'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    metadata = HERE.parents[1] / 'metadata/current153-kraken-process1/mechanics-metadata.json'
    encounter = HERE.parent / 'kraken153-encounter-source.json'
    if sha(metadata) != PROCESS or sha(encounter) != ENCOUNTER:
        raise ValueError('Exact original current153 process/table evidence required')
    md = json.loads(metadata.read_text(encoding='utf8'))
    if md['clientSha256'] != CLIENT or md['missingRoots']:
        raise ValueError('Complete exact current153 process metadata required')
    sources = [metadata, encounter]
    methods = []
    for name, filename, rva, size in [('.ctor', 'intercept-ctor-source.json', 0x0712D170, 425),
                                      ('CreateContext', 'intercept-context-source.json', 0x0712D080, 235)]:
        path = HERE / filename
        report = json.loads(path.read_text(encoding='utf8'))
        fragments = report['fragments']
        if report['clientSha256'] != CLIENT or report['metadataSha256'] != PROCESS or \
                report['class'] != 'NK.Spot.Context.Process.InterceptProcess' or \
                report['method']['name'] != name or report['primaryRva'] != rva or \
                report['nativeRunPerformed'] is not False or len(fragments) != 1:
            raise ValueError('Exact one-method original source differs')
        fragment = fragments[0]
        raw = bytes.fromhex(''.join(row['bytes'] for row in fragment['instructions']))
        if fragment['startRva'] != rva or len(raw) != size or \
                fragment['endRva'] - fragment['startRva'] != size or hashlib.sha256(raw).hexdigest() != fragment['sha256']:
            raise ValueError('Complete source-bound entry body differs')
        methods.append({'name': name, 'rva': rva, 'fragments': [
            {'rva': rva, 'byteLength': size, 'bytes': raw.hex(), 'sha256': fragment['sha256']}]})
        sources.append(path)
    result = {'schemaVersion': 1, 'clientSha256': CLIENT, 'processMetadataSha256': PROCESS,
              'encounterSourceSha256': ENCOUNTER,
              'scope': 'Original Intercept ctor and override CreateContext only; actual Kraken inputs required',
              'methods': methods, 'nativeRunPerformed': False,
              'actualOriginalCaptureRequired': True, 'runtimeIntegrated': False,
              'sources': [{'path': str(path), 'sha256': sha(path)} for path in sources]}
    output = HERE / 'kraken-mode-binding153.json'
    with output.open('x', encoding='utf8', newline='\n') as sink:
        json.dump(result, sink, indent=2)
        sink.write('\n')
    print(json.dumps({'path': str(output), 'sha256': sha(output), 'nativeRunPerformed': False}))


if __name__ == '__main__':
    build()
