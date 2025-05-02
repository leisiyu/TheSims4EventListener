from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from business.business_rule import BusinessRule
    from Business_pb2 import BusinessSaveDatafrom protocolbuffers import GameplaySaveData_pb2from business.business_manager import TELEMETRY_GROUP_BUSINESS, TELEMETRY_HOOK_BUSINESS_TYPEfrom singletons import DEFAULTfrom business.business_rule_enums import BusinessRuleStatefrom distributor.rollback import ProtocolBufferRollbackimport telemetry_helperimport sims4import servicesbusiness_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_BUSINESS)TELEMETRY_HOOK_BUSINESS_RULE_BROKEN = 'BURB'TELEMETRY_RULE_ID = 'ruid'logger = sims4.log.Logger('BusinessRuleManager', default_owner='bzhu')
class BusinessRuleManagerMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._household_id = None
        self.active_rules = {}
        self._available_rules = {}
        for rule in self.tuning_data.available_rules:
            self._available_rules[rule.guid64] = rule

    @property
    def household_id(self) -> 'int':
        if self._household_id is None:
            self._household_id = services.get_persistence_service().get_household_id_from_zone_id(self.business_zone_id)
        return self._household_id

    @property
    def has_rules(self) -> 'bool':
        return True

    def reset_rules(self, default_state:'BusinessRuleState'=BusinessRuleState.ENABLED) -> 'None':
        for rule_id in list(self.active_rules.keys()):
            self.set_rule_state(rule_id, default_state, override_rule_cooldown_time=0)

    def set_rule_state(self, rule_id:'int', state:'BusinessRuleState', override_rule_cooldown_time:'int'=DEFAULT) -> 'None':
        if rule_id not in self.active_rules:
            if state == BusinessRuleState.DISABLED:
                logger.error("Trying to disable rule {} that doesn't exist in business's active rules", rule_id)
                return
            if rule_id not in self._available_rules:
                logger.error("Trying to set rule {} that doesn't exist in the business's available rules", rule_id)
                return
            rule_class = self._available_rules[rule_id]
            new_rule = rule_class(zone_id=self.business_zone_id, state_change_callback=self.handle_rule_state_change)
            self.active_rules[rule_id] = new_rule
        self.active_rules[rule_id].set_state(state, override_rule_cooldown_time=override_rule_cooldown_time)

    def get_rules_by_states(self, *states) -> 'List[BusinessRule]':
        out_list = []
        if len(states) == 0:
            return out_list
        for rule in self.active_rules.values():
            if rule.rule_state in states:
                out_list.append(rule)
        return out_list

    def on_loading_screen_animation_finished(self) -> 'None':
        super().on_loading_screen_animation_finished()
        for rule in self.active_rules.values():
            rule.on_loading_screen_finished()

    def load_venue_business_data_proto(self, venue_business_data_proto:'GameplaySaveData_pb2.VenueBusinessData') -> 'None':
        super().load_venue_business_data_proto(venue_business_data_proto)
        for business_rule in venue_business_data_proto.business_rules:
            rule_class = self._available_rules.get(business_rule.rule_id)
            if rule_class is not None:
                new_rule = rule_class(zone_id=self.business_zone_id, state_change_callback=self.handle_rule_state_change)
                new_rule.load_business_rule_proto(business_rule)
                self.active_rules[business_rule.rule_id] = new_rule

    def create_venue_business_data_proto(self) -> 'GameplaySaveData_pb2.VenueBusinessData':
        venue_business_data_proto = super().create_venue_business_data_proto()
        if venue_business_data_proto is None:
            venue_business_data_proto = GameplaySaveData_pb2.VenueBusinessData()
        for rule in self.active_rules.values():
            with ProtocolBufferRollback(venue_business_data_proto.business_rules) as business_rule_msg:
                rule.update_business_rule_proto(business_rule_msg)
        return venue_business_data_proto

    def handle_rule_state_change(self, rule:'BusinessRule', rule_state:'BusinessRuleState'):
        if rule_state == BusinessRuleState.DISABLED:
            self.active_rules.pop(rule.guid64, None)
        self._send_rule_update_telemetry(rule, rule_state)
        self.send_venue_business_data_update_message()

    def _send_rule_update_telemetry(self, rule:'BusinessRule', new_state:'BusinessRuleState') -> 'None':
        household = services.household_manager().get(self.household_id)
        if new_state == BusinessRuleState.BROKEN:
            sim_info = household.sim_infos[0]
            with telemetry_helper.begin_hook(business_telemetry_writer, TELEMETRY_HOOK_BUSINESS_RULE_BROKEN, sim_info=sim_info) as hook:
                hook.write_enum(TELEMETRY_HOOK_BUSINESS_TYPE, self.business_type)
                hook.write_guid(TELEMETRY_RULE_ID, rule.guid64)
