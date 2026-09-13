"""Concise EX play guidance; separate from recovered numeric records."""
CHECKED='2026-09-14'
GUIDES={
 'alteisen':dict(required_tags=[],preferred_tags=['Shield','AoE'],
    summary='Break the right missile launcher, then its turrets. Switch to the left weapons afterward.',
    cover_policy='Use protection against weapon fire. Cover is finite; green missiles cannot be shot down.',
    qte_tip='After the weapons break and in phase two, prioritize red circles, then missiles. Keep ammunition ready.',
    survival_tip='This is a demanding early gear check. Improving your reward stage is useful progress even before stage 9.'),
 'gravedigger':dict(required_tags=[],preferred_tags=['CDR'],
    summary='Keep Full Burst and ammunition ready for the moving red circles. Shotguns can help; the actual damage check decides.',
    cover_policy='Shoot down drill missiles. Cover can absorb early drill hits, but the phase-three drill pierces it.',
    qte_tip='Clear every circle in each set. The first missed set in phase three is dangerous; later, two consecutive misses trigger the drill.',
    survival_tip='Prioritize interruptions over body damage. Healing cannot substitute for the final-phase check.'),
 'blacksmith':dict(required_tags=['Healing'],preferred_tags=['Cover repair','AoE'],
    summary='Bring a healer. Clear bombs, then aim at the core instead of spending the fight breaking the guns.',
    cover_policy='Share rifle damage between HP and cover; repeated targeting can exhaust either.',
    qte_tip='Destroy the red circles when the charged attack or capture check appears. A stunned unit cannot help shoot.',
    survival_tip='Use an area attack for bombs when available. Check which unit dies and whether healing actually activates.'),
 'chatterbox':dict(required_tags=[],preferred_tags=['Shield','Healing'],
    summary='Keep the head core intact. Break one shoulder launcher and preserve the other under the safe plan.',
    cover_policy='Protect the middle slot from the opening punch. Shields help prevent damage and corrosion stacks.',
    qte_tip='Break both red circles before the attack completes. Shoot down missiles between checks.',
    survival_tip='Breaking the head triggers the dangerous squad punch. Repeated corrosion stacks can kill a unit regardless of remaining HP.'),
 'modernia':dict(required_tags=[],preferred_tags=['Healing','CDR','AoE'],
    summary='Focus the core first to stop the laser. Then preserve at least one wing to avoid repeated teleporting.',
    cover_policy='Cover the laser while the core is alive. Clear bombs and use healing for sustained gunfire.',
    qte_tip='Circle checks belong to the teleport route. A completed safe route can correctly report no circles encountered.',
    survival_tip='If the core survives too long, inspect its break deadline and improve opening damage or burst timing.'),
}
for key,g in GUIDES.items():
    slug='alteisen-train' if key=='alteisen' else key
    g.update(source=f'https://nikke.gg/special-interception-{slug}/',source_name='Nikke.gg · Special Interception guide',
        checked_at=CHECKED,confidence='Guide-informed play policy. Numeric EX records drive the model; spatial timing and complete fights need gameplay validation.')
