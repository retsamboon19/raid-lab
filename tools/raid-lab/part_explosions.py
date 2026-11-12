"""Sphere/capsule collateral contacts in the authored Ultra bind pose.

This is a spatial approximation, not an animated Unity collision replay.
Only the two recovered poison chamber capsules are available here.
"""
import json
import math
from pathlib import Path

GEOMETRY=json.loads(Path(__file__).with_name('anomaly-ultra-blast-geometry.json').read_text())


def capsule_overlap(center,radius,capsule):
    a,b=capsule['a'],capsule['b']
    direction=[y-x for x,y in zip(a,b)]
    length=sum(x*x for x in direction)
    fraction=max(0.,min(1.,sum((x-y)*v for x,y,v in zip(center,a,direction))/length)) if length else 0.
    nearest=[x+fraction*v for x,v in zip(a,direction)]
    return math.dist(center,nearest)<=radius+capsule['radius']


def explosion_parts(runtime,caster,weapon,hit_type,part):
    if runtime.key!='anomaly-ultra' or not hit_type.get('is_projectile_explosion'):return ()
    from anomaly_qte_shots import base_weapon_parameters,temporary_weapon_parameters
    parameters=base_weapon_parameters(caster)
    # Sticky grenades are a separate ChangeWeapon shot, even while the base
    # weapon remains MG. Do not borrow the MG's zero explosion radius.
    if not parameters or parameters['WeaponType']!=weapon or not parameters['explosion_radius']:
        parameters=temporary_weapon_parameters(caster,weapon)
    if not parameters:return ()
    radius=parameters['explosion_radius']*max(0,1+runtime.active_stat(caster,'explosion_range')/100)
    if radius<=0:return ()
    center=GEOMETRY['core_center'] if part=='Weapon_01' else GEOMETRY['body_center']
    return tuple(c['part'] for c in GEOMETRY['capsules']
                 if runtime.world.parts.alive(c['part']) and capsule_overlap(center,radius,c))
