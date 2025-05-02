from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim import Sim
    from interactions.base.interaction import Interactionfrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizershorse_reins_animation_archive_schema = GsiGridSchema(label='Horse Reins Animation Archive', sim_specific=True)horse_reins_animation_archive_schema.add_field('sim_id', label='simID', type=GsiFieldVisualizers.INT, hidden=True)horse_reins_animation_archive_schema.add_field('reins_state', label='Are Reins Up', width=1)horse_reins_animation_archive_schema.add_field('source_interaction', label='Source Interaction', width=2)archiver = GameplayArchiver('horse_reins_animation_archive', horse_reins_animation_archive_schema)
def log_horse_reins_animation_archive_data(sim:'Sim', reins_state:'bool', source_interaction:'Interaction') -> 'None':
    entry = {}
    entry['sim_id'] = sim.id
    entry['reins_state'] = reins_state
    entry['source_interaction'] = str(source_interaction)
    archiver.archive(data=entry, object_id=sim.id)
