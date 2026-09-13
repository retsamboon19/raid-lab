"""Private, durable snapshots of complete recommendation runs."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import uuid


MODE_NAMES = {
    'solo': 'Solo Raid', 'museum': 'Solo Raid Museum',
    'special': 'Special Interception', 'anomaly': 'Anomaly Interception',
    'campaign': 'Campaign · non-boss stage', 'practice': 'Practice · one team',
}
ID_PATTERN = re.compile(r'[a-f0-9]{32}\Z')
FILTER_PATTERN = re.compile(r'[a-zA-Z0-9_-]{1,100}\Z')


def timestamp(value=None):
    instant = datetime.now(timezone.utc) if value is None else datetime.fromtimestamp(value, timezone.utc)
    return instant.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def summarize(report, ident, created_at, kind, catalog):
    settings = report.get('settings') or {}
    encounter = settings.get('encounter') or {}
    boss = settings.get('boss_id') or encounter.get('id') or 'training'
    mode = settings.get('content_mode')
    if not mode:
        mode = ('solo' if encounter.get('raid') or re.fullmatch(r'sr\d+', boss) else
                'museum' if boss.startswith('museum-') else
                next((key for key in ('special', 'anomaly', 'campaign') if boss.startswith(key)), 'practice'))
    completion = report.get('completion') or {}
    teams = []
    for index, team in enumerate(report['teams'], 1):
        members = []
        for member in team.get('members', []):
            ident_member = member.get('id', member.get('name', 'Unknown')) if isinstance(member, dict) else member
            details = catalog.get(ident_member, {})
            if isinstance(member, dict):
                details = {**details, **member}
            members.append(dict(id=ident_member, name=details.get('name', ident_member),
                                element=details.get('element', 'Unknown'), burst=str(details.get('burst', '?')),
                                weapon=details.get('weapon', 'Unknown')))
        teams.append(dict(index=index, damage=team.get('damage'), bursts=team.get('bursts'), members=members))
    summary = dict(id=ident, created_at=created_at, kind=kind, mode=mode, boss_id=boss,
                   boss_name=encounter.get('name') or settings.get('boss_name') or boss,
                   museum_mode=settings.get('museum_mode') if mode == 'museum' else None,
                   duration=settings.get('duration'), total=None if mode == 'campaign' else report.get('total'),
                   budget=settings.get('budget'), playstyle=settings.get('playstyle'), simulations=report.get('simulations'),
                   requested_teams=completion.get('requested_teams', len(teams) if kind == 'manual' else settings.get('teams', len(teams))),
                   completion_reason=completion.get('reason', 'completed'),
                   model_revision=encounter.get('model_revision'), teams=teams)
    if report['teams'] and all(t.get('damage_accounting') for t in report['teams']):
        summary['damage_basis']='boss_direct'
    critical = (report.get('selection') or {}).get('critical_parts') or {}
    if critical.get('enabled'):
        summary['critical_parts'] = {key: critical.get(key) for key in ('passed_teams', 'total_teams', 'fallback')}
    return summary


class ReportHistory:
    def __init__(self, private_dir, catalog=None):
        self.private_dir = Path(private_dir)
        self.path = self.private_dir / 'recommendation-history.sqlite3'
        self.catalog = catalog or {}

    @contextmanager
    def connection(self):
        self.private_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        try:
            # Each process owns its connection. Transactions serialize initialization,
            # migration and writes, including simultaneous worker and HTTP requests.
            connection.execute('PRAGMA busy_timeout = 30000')
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, '
                               'kind TEXT NOT NULL, mode TEXT NOT NULL, boss_id TEXT NOT NULL, '
                               'summary_json TEXT NOT NULL, report_json TEXT NOT NULL)')
            connection.execute('CREATE INDEX IF NOT EXISTS runs_lookup ON runs(mode,boss_id,created_at DESC,id DESC)')
            connection.execute('CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY)')
            self._migrate(connection)
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _insert(self, connection, report, kind, created_at):
        if kind not in ('search', 'manual', 'legacy'):
            raise ValueError('Invalid recommendation kind.')
        if not isinstance(report, dict) or not isinstance(report.get('teams'), list) or not report['teams']:
            raise ValueError('Only recommendations with completed squads can be saved.')
        if not all(isinstance(team, dict) and isinstance(team.get('members'), list) and team['members'] for team in report['teams']):
            raise ValueError('Invalid recommendation squads.')
        ident = uuid.uuid4().hex
        summary = summarize(report, ident, created_at, kind, self.catalog)
        connection.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?)',
                           (ident, created_at, kind, summary['mode'], summary['boss_id'],
                            json.dumps(summary, ensure_ascii=False, allow_nan=False),
                            json.dumps(report, ensure_ascii=False, allow_nan=False)))
        return dict(id=ident, created_at=created_at)

    def _migrate(self, connection):
        name = 'legacy-report-json-v1'
        if connection.execute('SELECT 1 FROM migrations WHERE name=?', (name,)).fetchone():
            return
        source = self.private_dir / 'report.json'
        if source.is_file():
            try:
                report = json.loads(source.read_text(encoding='utf-8'))
                self._insert(connection, report, 'legacy', timestamp(source.stat().st_mtime))
            except (ValueError, TypeError, KeyError, AttributeError):
                # An old, malformed report must not prevent saving future runs.
                pass
        connection.execute('INSERT INTO migrations VALUES (?)', (name,))

    def save(self, report, kind='search'):
        with self.connection() as connection:
            return self._insert(connection, report, kind, timestamp())

    def get(self, ident):
        if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident):
            raise ValueError('Invalid history ID.')
        with self.connection() as connection:
            row = connection.execute('SELECT created_at,kind,report_json,summary_json FROM runs WHERE id=?', (ident,)).fetchone()
        return dict(id=ident, created_at=row[0], kind=row[1], report=json.loads(row[2]), summary=json.loads(row[3])) if row else None

    def list(self, mode=None, boss=None, offset=0, limit=10):
        for value in (mode, boss):
            if value is not None and (not isinstance(value, str) or not FILTER_PATTERN.fullmatch(value)):
                raise ValueError('Invalid history filter.')
        if isinstance(offset, bool) or isinstance(limit, bool):
            raise ValueError('Invalid history page.')
        try:
            offset, limit = int(offset), int(limit)
        except (ValueError, TypeError):
            raise ValueError('Invalid history page.') from None
        if not 0 <= offset <= 1_000_000 or not 1 <= limit <= 50:
            raise ValueError('History pages require an offset from 0 to 1000000 and a limit from 1 to 50.')
        with self.connection() as connection:
            rows = connection.execute('SELECT mode,boss_id,COUNT(*),'
                                      '(SELECT summary_json FROM runs newest WHERE newest.mode=runs.mode AND newest.boss_id=runs.boss_id '
                                      'ORDER BY created_at DESC,id DESC LIMIT 1) FROM runs GROUP BY mode,boss_id').fetchall()
            modes = {}
            for row in rows:
                group = modes.setdefault(row[0], dict(id=row[0], name=MODE_NAMES.get(row[0], row[0]), bosses=[]))
                group['bosses'].append(dict(id=row[1], name=json.loads(row[3])['boss_name'], count=row[2]))
            for group in modes.values():
                group['bosses'].sort(key=lambda boss: boss['name'].casefold())
            result = dict(modes=sorted(modes.values(), key=lambda mode: list(MODE_NAMES).index(mode['id']) if mode['id'] in MODE_NAMES else len(MODE_NAMES)),
                          runs=[], total=0, offset=offset, limit=limit, has_more=False)
            if mode and boss:
                result['total'] = connection.execute('SELECT COUNT(*) FROM runs WHERE mode=? AND boss_id=?', (mode, boss)).fetchone()[0]
                rows = connection.execute('SELECT summary_json FROM runs WHERE mode=? AND boss_id=? ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?',
                                          (mode, boss, limit, offset)).fetchall()
                result['runs'] = [json.loads(row[0]) for row in rows]
                result['has_more'] = offset + len(rows) < result['total']
            return result
