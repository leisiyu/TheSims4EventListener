from __future__ import annotationsfrom event_testing.resolver import SingleSimResolverfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from sims.sim_info import SimInfo
    from typing import Optional
    from typing import Tuple
    from protocolbuffers.FileSerialization_pb2 import SaveGameDatafrom protocolbuffers import GameplaySaveData_pb2import randomimport servicesimport sims4from persistence_error_types import ErrorCodesfrom sims.secrets.tunable_sim_secret import SimSecretfrom sims.sim_info_types import Agefrom sims4.common import Packfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableRangefrom sims4.utils import classpropertyimport sims4.telemetryimport telemetry_helperTELEMETRY_GROUP_SCRT = 'SCRT'TELEMETRY_HOOK_SUCC = 'SUCC'TELEMETRY_TARGET_SIM_ID = 'tsid'TELEMETRY_SECRET_ID = 'seid'sim_secret_service_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SCRT)logger = sims4.log.Logger('Secrets Service', default_owner='cparrish')
class SimSecretsService(Service):
    COOLDOWN_ON_SECRET_RECYCLE = TunableRange(description="\n        The number of secrets to find before it's possible for any one secret to appear again.\n        ", tunable_type=int, default=15, minimum=0)
    MAXIMUM_SECRET_COUNT_PER_TARGET = TunableRange(description='\n        The maximum number of secrets one sim can find out about another sim.\n        ', tunable_type=int, default=8, minimum=0)

    def __init__(self):
        self._unavailable_secrets = []

    @classproperty
    def required_packs(cls) -> 'Tuple[Pack]':
        return (Pack.EP15,)

    @classproperty
    def save_error_code(cls) -> 'ErrorCodes':
        return ErrorCodes.SERVICE_SAVE_FAILED_SIM_SECRETS_SERVICE

    def save(self, save_slot_data:'SaveGameData'=None, **__) -> 'None':
        if save_slot_data is None or len(self._unavailable_secrets) == 0:
            return
        sim_secret_service_proto = GameplaySaveData_pb2.PersistableSimSecretsService()
        for secret in self._unavailable_secrets:
            sim_secret_service_proto.unavailable_secrets.append(secret.guid64)
        save_slot_data.gameplay_data.sim_secrets_service = sim_secret_service_proto

    def load(self, **__) -> 'None':
        save_slot_data = services.get_persistence_service().get_save_slot_proto_buff()
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        for secret_guid in save_slot_data.gameplay_data.sim_secrets_service.unavailable_secrets:
            secret = snippet_manager.get(secret_guid)
            if secret:
                self._unavailable_secrets.append(secret)

    def _update_secret_availability(self, secret:'SimSecret') -> 'None':
        self._unavailable_secrets.append(secret)
        if len(self._unavailable_secrets) > self.COOLDOWN_ON_SECRET_RECYCLE:
            self._unavailable_secrets.pop(0)

    def generate_secret_for_target_sim(self, source_sim:'SimInfo', target_sim_id:'int') -> 'Optional[SimSecret]':
        available_secrets = services.snippet_manager().get_ordered_types(only_subclasses_of=SimSecret)
        sim_knowledge = source_sim.relationship_tracker.get_knowledge(target_sim_id, initialize=True)
        target_sim_info = services.sim_info_manager().get(target_sim_id)
        if target_sim_info is None:
            logger.error('Cannot find target sim for secret.')
            return
        else:
            invalid_secrets = self._unavailable_secrets + sim_knowledge.get_all_secrets()
            valid_secrets = [secret for secret in available_secrets if secret not in invalid_secrets]
            if len(valid_secrets) > 0:
                resolver = SingleSimResolver(target_sim_info)
                weighted_pairs = [(secret.weight.get_multiplier(resolver), secret) for secret in valid_secrets]
                picked_secret = sims4.random.weighted_random_item(weighted_pairs)
                if picked_secret is not None:
                    self._update_secret_availability(picked_secret)
                    with telemetry_helper.begin_hook(sim_secret_service_telemetry_writer, TELEMETRY_HOOK_SUCC, sim_info=source_sim) as hook:
                        hook.write_guid(TELEMETRY_TARGET_SIM_ID, target_sim_id)
                        hook.write_guid(TELEMETRY_SECRET_ID, picked_secret.guid64)
                    return picked_secret()

    def determine_snooping_target(self, source_sim:'SimInfo', household_id:'int') -> 'Optional[SimInfo]':
        household = services.household_manager().get(household_id)
        valid_sims = [sim for sim in household.get_humans_gen() if sim.age >= Age.TEEN]
        while len(valid_sims) > 0:
            picked_sim = random.choice(valid_sims)
            sim_knowledge = source_sim.relationship_tracker.get_knowledge(target_sim_id=picked_sim.id, initialize=True)
            if sim_knowledge and (sim_knowledge.knows_unconfronted_secret or len(sim_knowledge.get_all_secrets()) >= self.MAXIMUM_SECRET_COUNT_PER_TARGET):
                valid_sims.remove(picked_sim)
            else:
                return picked_sim
