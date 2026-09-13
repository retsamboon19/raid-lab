"""Local search priors. No network access or article content is used at runtime.

Weights influence proposal order only; simulated damage still selects winners.
An absent recommendation is neutral, never an exclusion.
"""
import json
import math
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_data():
    return json.loads(Path(__file__).with_name('pairing-data.json').read_text(encoding='utf-8'))


class SearchGuidance:
    def __init__(self, roster, catalog, settings, weights, data=None):
        self.data = load_data() if data is None else data
        self.roster, self.catalog, self.settings, self.weights = roster, catalog, settings, weights
        self.units = self.data['units']
        self.edges = []
        for rule in self.data['pairs']:
            anchor, *partners = rule['units']
            for partner in partners:
                a, b = self.resolve(anchor), self.resolve(partner)
                if a and b and a != b:
                    self.edges.append((a, b, rule['weight'], rule))
        self.templates = []
        self.template_roles = {}
        for template in self.data['teams']:
            if not self.context(template):
                continue
            members = [self.resolve(slot['unit'], slot.get('favorite_min', 0))
                       for slot in template['slots'] if slot['unit']]
            if any(n is None for n in members):continue
            members = list(dict.fromkeys(members))
            if len(members) >= 2:
                self.templates.append(members)
                self.template_roles[tuple(members)]=[slot['role'] for slot in template['slots'] if not slot['unit']]
        self.kits=None

    def resolve(self, slug, minimum=0):
        unit = self.units.get(slug, {})
        n = unit.get('unit_id')
        if n not in self.roster:
            return None
        phase = self.roster[n]['build'].get('favorite_stage', 0)
        return n if phase >= max(minimum, unit.get('favorite_min', 0)) else None

    def context(self, rule):
        mode = rule.get('mode', '').lower()
        campaign = self.settings.get('content_mode') == 'campaign'
        if mode:
            if mode in ('campaign', 'tribe tower', 'surface'):
                if not campaign: return False
            elif mode in ('bossing', 'union / solo raids'):
                if campaign: return False
            elif mode.startswith('anomaly - '):
                expected='anomaly-'+mode.split(' - ')[1].replace(' ', '-')
                if campaign or self.settings.get('boss_id')!=expected: return False
            elif mode.startswith('museum - '):
                # Museum examples apply only to their named Museum boss.
                normalize=lambda value:''.join(c for c in value.lower() if c.isalnum())
                boss=self.settings.get('encounter',{})
                if self.settings.get('content_mode')!='museum': return False
                if normalize(mode.split(' - ',1)[1])!=normalize(boss.get('name','')): return False
            else:
                return False  # PVP examples are not generic boss priors.
        element = rule.get('element', 'All')
        weak = {'Fire':'Water', 'Water':'Electric', 'Electric':'Iron', 'Iron':'Wind', 'Wind':'Fire'}
        selected = self.settings.get('element', 'Any')
        target = weak.get(self.settings.get('enemy_element'))
        if element not in ('All', 'Any') and element != (target or selected): return False
        if rule.get('core') and not self.settings.get('core_px', 0): return False
        if rule.get('assisted') and self.settings.get('playstyle') != 'assisted': return False
        for slug, phase in rule.get('favorite_min', {}).items():
            if not self.resolve(slug, phase): return False
        for slug, phase in rule.get('favorite_max', {}).items():
            n = self.resolve(slug)
            if not n or self.roster[n]['build'].get('favorite_stage', 0) > phase: return False
        return True

    def applies(self, rule, team):
        if not self.context(rule): return False
        if any(not self.resolve(slug) or self.resolve(slug) not in team for slug in rule.get('requires', [])): return False
        any_of = rule.get('requires_any', [])
        return not any_of or any(self.resolve(slug) in team for slug in any_of)

    def pair_values(self, team):
        values = {}
        for a, b, weight, rule in self.edges:
            if a in team and b in team and self.applies(rule, team):
                key = tuple(sorted((a,b)))
                # Repeated reviews cannot inflate the same relationship.
                if key not in values or abs(weight) > abs(values[key]): values[key] = weight
        for members in self.templates:
            # A team example is a package, not proof of every possible pair.
            if not set(members)<=set(team) or not self.template_fits(members,team):continue
            for i,a in enumerate(members):
                for b in members[i+1:]:values.setdefault(tuple(sorted((a,b))),.18)
        return values

    def template_fits(self,members,team):
        roles=self.template_roles.get(tuple(members),[])
        available=[n for n in team if n not in members]
        def match(remaining,pool):
            if not remaining:return True
            role=remaining[0]
            for n in pool:
                c=self.catalog[n]
                fits=(role=='FLEX' or role in ('B1','B2','B3') and c['burst']==role[1:]
                      or role=='B1-CDR' and c['burst']=='1' and 'CDR' in c['tags'])
                if fits and match(remaining[1:],[x for x in pool if x!=n]):return True
            return False
        return match(roles,available)

    def bonus(self, n, team):
        return max(-2., min(2., sum(v for pair,v in self.pair_values([*team,n]).items() if n in pair)))

    def priority(self, n, team):
        return math.log(max(self.weights[n], 1)) + self.bonus(n, team)

    def alternatives(self, options, team, iteration=0):
        ranked = sorted(options, key=lambda n:self.priority(n,team), reverse=True)
        recommended = [n for n in ranked if self.bonus(n,team)>0]
        # Reserve four recommended choices even when low personal support damage
        # would push them below unrelated attackers. Investment sorts each group.
        chosen = list(dict.fromkeys(recommended[:4] + ranked[:4]))
        tail = [n for n in ranked if n not in chosen]
        if tail: chosen += tail[(iteration*2)%len(tail):][:2]
        return chosen

    def score(self, team):
        bonus = sum(self.pair_values(team).values()) / 3
        for rule in self.data['dependencies']:
            if self.resolve(rule['unit']) in team and not any(self.resolve(s) in team for s in rule['any_of']):
                bonus -= .6
        return sum(self.weights[n] for n in team) * math.exp(max(-1., min(1.5, bonus)))

    def order_score(self, team):
        score = 0.
        for rule in self.data['orders']:
            if not self.applies(rule, team): continue
            for field in ('before', 'position_before'):
                pair = [self.resolve(x) for x in rule.get(field, [])]
                if len(pair) == 2 and all(n in team for n in pair):
                    score += 5 if team.index(pair[0]) < team.index(pair[1]) else -5
            first = self.resolve(rule.get('position_first'))
            if first in team: score += 8 if team[0] == first else -8
            for slug in rule.get('offburst', []):
                n = self.resolve(slug)
                if n not in team: continue
                same = [x for x in team if self.catalog[x]['burst'] == self.catalog[n]['burst']]
                score += 3 * same.index(n)
            for field, desired in (('first', 0), ('second', 1)):
                n = self.resolve(rule.get(field))
                if n in team:
                    same = [x for x in team if self.catalog[x]['burst'] == self.catalog[n]['burst']]
                    if same.index(n) == desired: score += 3
        return score

    def orders(self, orders):
        # Keep every legal alternative, merely test the recommended order first.
        return sorted(orders, key=self.order_score, reverse=True)

    def cycle_rules(self):
        rules=[]
        for rule in self.data['orders']:
            if not rule.get('b2_cycle') or not self.context(rule):continue
            required=[self.resolve(n) for n in rule.get('requires',[])]
            cycle=[self.resolve(n) for n in rule['b2_cycle']]
            if all(required+cycle):rules.append({'requires':required,'cycle':cycle})
        return rules

    def report(self, team):
        pairs = []
        seen = set()
        for a,b,weight,rule in self.edges:
            if a in team and b in team and self.applies(rule, team):
                key = tuple(sorted((a,b)))
                if key in seen: continue
                seen.add(key)
                pairs.append({'members':[a,b], 'weight':weight, 'reason':rule['reason']})
        return {'kind':'local_search_preferences', 'pairs':pairs,
                'burst_priority':{stage:[n for n in team if self.catalog[n]['burst']==stage] for stage in ('1','2','3','A')},
                'notes':[r['reason'] for r in self.data['orders'] if self.applies(r,team)
                         and any(self.resolve(x) in team for x in r.get('offburst', []) + r.get('requires', []) + [r.get('first'),r.get('second')])],
                'scope':'Local proposal preferences; final order and team are verified by simulation.'}
