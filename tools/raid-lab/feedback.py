"""Explicit feedback uploads. No cookies, browser profiles or account exports are read."""
import base64
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
MAX_IMAGE = 2_000_000


def config():
    path = ROOT / 'private' / 'feedback-config.json'
    if not path.exists():
        path = ROOT / 'web' / 'feedback-config.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    endpoint = data.get('endpoint', '')
    enabled = isinstance(endpoint, str) and bool(re.fullmatch(r'https://script\.google\.com/macros/s/[\w-]+/exec', endpoint))
    return {'enabled': enabled, 'endpoint': endpoint if enabled else ''}


def image_bytes(image):
    if not isinstance(image, dict) or set(image) != {'data', 'type'}:
        raise ValueError('Attach one PNG or JPEG Battle Records image.')
    try:
        raw = base64.b64decode(image['data'], validate=True)
    except Exception:
        raise ValueError('The image could not be read.') from None
    if not 0 < len(raw) <= MAX_IMAGE:
        raise ValueError('The image must be no larger than 2 MB.')
    if not ((image['type'] == 'image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or
            (image['type'] == 'image/jpeg' and raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'))):
        raise ValueError('Only PNG and JPEG images are accepted.')
    return raw


def validate(body):
    if not isinstance(body, dict) or set(body) != {'id', 'message', 'profile_url', 'recommendation', 'owned_units', 'ownership_basis', 'squad', 'image'}:
        raise ValueError('Invalid feedback fields.')
    if not re.fullmatch(r'[a-f0-9]{32}', str(body['id'])):
        raise ValueError('Invalid submission ID.')
    if not isinstance(body['message'], str) or not 5 <= len(body['message'].strip()) <= 2000:
        raise ValueError('Write between 5 and 2,000 characters of feedback.')
    if not isinstance(body['profile_url'], str) or not re.fullmatch(r'https://(?:www\.)?blablalink\.com/shiftyspad\?uid=[A-Za-z0-9%_=-]{1,300}', body['profile_url']):
        raise ValueError('Paste your BlaBlaLink shared ShiftyPad profile link.')
    report = body['recommendation']
    if not isinstance(report, dict) or not isinstance(report.get('teams'), list) or not 1 <= len(report['teams']) <= 5:
        raise ValueError('A recommendation is required.')
    if type(body['squad']) is not int or not 0 <= body['squad'] < len(report['teams']):
        raise ValueError('Choose the squad you tried.')
    if not isinstance(body['owned_units'], list) or not 1 <= len(body['owned_units']) <= 1000:
        raise ValueError('The owned-unit snapshot is missing.')
    if body['ownership_basis'] not in ('recommendation-time', 'current-roster; historical ownership unavailable'):
        raise ValueError('Invalid ownership snapshot label.')
    if len(json.dumps({k: v for k, v in body.items() if k != 'image'})) > 900_000:
        raise ValueError('Feedback details are too large.')
    image_bytes(body['image'])


def submit(body):
    validate(body)
    destination = config()
    if not destination['enabled']:
        raise ValueError('Feedback uploads are not configured yet. Your feedback has not been sent.')
    request = Request(destination['endpoint'], data=json.dumps(body, allow_nan=False).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=45) as response:
            result = json.loads(response.read(8192))
    except Exception:
        raise ValueError('Upload confirmation was not received. Retry with the same form; duplicate submissions are detected.') from None
    if not isinstance(result, dict):
        raise ValueError('The upload service did not confirm receipt.')
    if result.get('ok') is not True or result.get('id') != body['id']:
        raise ValueError(result.get('error', 'The upload service did not confirm receipt.'))
    return {'ok': True, 'id': body['id']}
