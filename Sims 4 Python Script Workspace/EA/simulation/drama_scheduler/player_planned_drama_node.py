from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *from date_and_time import TimeSpanfrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom drama_scheduler.drama_node import BaseDramaNode, DramaNodeRunOutcomefrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import DoubleSimResolverfrom sims.sim_info import SimInfofrom sims4.tuning.instances import lock_instance_tunables, HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableList, TunableReference, OptionalTunable, TunableTuplefrom sims4.utils import classpropertyfrom situations.situation_serialization import SituationSeed, SeedPurposefrom situations.situation_types import SituationCallbackOptionfrom tunable_time import TunableTimeSpanfrom ui.ui_dialog import UiDialogOkCancel, ButtonTypeimport itertoolsimport servicesimport sims4.logfrom ui.ui_dialog_notification import UiDialogNotificationlogger = sims4.log.Logger('PlayerPlannedDramaNode', default_owner='bosee')
class PlayerPlannedDramaNode(BaseDramaNode):
    INVALID_EVENT_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        The notification that gets shown when the situation could not be started due to the\n        zone becoming invalid when the drama node tries to run.\n        ')
    INSTANCE_TUNABLES = {'advance_notice_time': TunableTimeSpan(description='\n            The number of time between the alert and the start of the event.\n            ', default_hours=1, locked_args={'days': 0, 'minutes': 0}), 'dialog': UiDialogOkCancel.TunableFactory(description='\n            The ok cancel dialog that will display to the user.\n            '), 'dialog_cancel_loots': OptionalTunable(description='\n            When enabled, loots that are applied on dialog cancellation.\n            ', tunable=TunableTuple(dialog_cancel_loot_list=TunableList(description='\n                    A list of loots that will be applied when the player responds cancel to the dialog if actor(s) and\n                    target(s) are found from Loot Actor Jobs and Loot Target Jobs. All actors will get each loot with\n                    all targets.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), loot_actor_jobs=TunableList(description="\n                    If a Sim in the situation's player planned drama node matches a job from this list, then that Sim\n                    will be an Actor Sim for the Dialog Cancel Loot List. Minimum one Sim must be found here for loots\n                    to be applied and all Sims found in these jobs will be used.\n                    ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), pack_safe=True)), loot_target_jobs=TunableList(description="\n                    If a Sim in the situation's player planned drama node matches a job from this list, then that Sim\n                    will be a Target Sim for the Dialog Cancel Loot List. Minimum one Sim must be found here for loots\n                    to be applied and all Sims found in these jobs will be used.\n                    ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), pack_safe=True))))}

    @classproperty
    def persist_when_active(cls):
        return True

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.PLAYER_PLANNED

    def __init__(self, *args, uid=None, situation_seed=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._situation_seed = situation_seed

    def get_situation_seed(self):
        return self._situation_seed

    def _validate_venue(self):
        if self._situation_seed.situation_type.is_venue_location_valid(self._situation_seed.zone_id):
            return True
        if not any(venue_tuning.is_residential for venue_tuning in self._situation_seed.situation_type.compatible_venues):
            return False
        host_sim_info = self._situation_seed.guest_list.host_sim_info
        if host_sim_info is not None and self._situation_seed.zone_id == host_sim_info.household.home_zone_id:
            return True
        sim_info_manager = services.sim_info_manager()
        for guest_info in self._situation_seed.guest_list.guest_info_gen():
            sim_info = sim_info_manager.get(guest_info.sim_id)
            if sim_info is None:
                pass
            else:
                if self._situation_seed.zone_id == sim_info.household.home_zone_id:
                    return True
                travel_group = sim_info.travel_group
                if travel_group is not None and self._situation_seed.zone_id == travel_group.zone_id:
                    return True
        return False

    def _run(self):
        situation_seed = self._situation_seed
        if situation_seed is None:
            return DramaNodeRunOutcome.FAILURE
        delay_result = self.try_do_travel_dialog_delay()
        if delay_result is not None:
            return delay_result
        if not self._validate_venue():
            zone_data = services.get_persistence_service().get_zone_proto_buff(self._situation_seed.zone_id)
            notification = self.INVALID_EVENT_NOTIFICATION(services.active_sim_info(), None)
            notification.show_dialog(additional_tokens=(zone_data.name, self._situation_seed.situation_type.display_name))
            return DramaNodeRunOutcome.FAILURE
        situation_manager = services.get_zone_situation_manager()
        dialog = self.dialog(self._receiver_sim_info, resolver=self._get_resolver())

        def _get_job_sim_infos(jobs:'Tuple[HashedTunedInstanceMetaclass]') -> 'Optional[List[SimInfo]]':
            found_sim_infos = []
            for job in jobs:
                guest_infos = situation_seed.guest_list.get_guest_infos_for_job(job)
                for guest_info in guest_infos:
                    found_sim_infos.append(services.sim_info_manager().get(guest_info.sim_id))
            if found_sim_infos:
                return found_sim_infos

        def response(dialog):
            cleanup_node = True
            if dialog.response is not None:
                if dialog.response == ButtonType.DIALOG_RESPONSE_OK:
                    cleanup_node = False
                    if situation_seed.zone_id == services.current_zone_id():
                        situation_id = situation_manager.create_situation_from_seed(situation_seed)
                        if situation_id is not None:
                            situation_manager.register_for_callback(situation_seed.situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_planned_drama_node_ended)
                        else:
                            cleanup_node = True
                    else:
                        situation_seed.purpose = SeedPurpose.TRAVEL
                        situation_manager.travel_seed(situation_seed)
                elif dialog.response == ButtonType.DIALOG_RESPONSE_CANCEL:
                    dialog_cancel_loots = self.dialog_cancel_loots
                    if dialog_cancel_loots is not None:
                        dialog_cancel_loot_list = dialog_cancel_loots.dialog_cancel_loot_list
                        if dialog_cancel_loot_list:
                            actor_sim_infos = _get_job_sim_infos(dialog_cancel_loots.loot_actor_jobs)
                            target_sim_infos = _get_job_sim_infos(dialog_cancel_loots.loot_target_jobs)
                            if actor_sim_infos is None or target_sim_infos is None:
                                logger.error('Actor Sim Info(s) {} and/or Target Sim Info(s) {} not found in situation {} using Actor/Target Override Jobs from Dialog Cancel Loots in {}.', actor_sim_infos, target_sim_infos, situation_seed, self)
                            else:
                                for (actor_sim_info, target_sim_info) in itertools.product(actor_sim_infos, target_sim_infos):
                                    resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
                                    for loot in dialog_cancel_loot_list:
                                        loot.apply_to_resolver(resolver)
                        else:
                            logger.error('Dialog Cancel Loots enabled but no loots found in Dialog Cancel Loot List in {}.', self)
            if cleanup_node:
                services.drama_scheduler_service().complete_node(self.uid)

        dialog.show_dialog(on_response=response, additional_tokens=(situation_seed.situation_type.display_name,))
        return DramaNodeRunOutcome.SUCCESS_NODE_INCOMPLETE

    def _on_planned_drama_node_ended(self, situation_id, callback_option, _):
        services.drama_scheduler_service().complete_node(self.uid)

    def on_situation_creation_during_zone_spin_up(self) -> 'None':
        if self._situation_seed.situation_id not in services.get_zone_situation_manager():
            services.drama_scheduler_service().complete_node(self.uid)
            return
        services.get_zone_situation_manager().register_for_callback(self._situation_seed.situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_planned_drama_node_ended)

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO):
        success = super().schedule(resolver, specific_time=specific_time, time_modifier=time_modifier)
        if success:
            services.calendar_service().mark_on_calendar(self, advance_notice_time=self.advance_notice_time())
        return success

    def cleanup(self, from_service_stop=False):
        services.calendar_service().remove_on_calendar(self.uid)
        self.try_move_special_object_from_hidden()
        super().cleanup(from_service_stop=from_service_stop)

    def get_calendar_sims(self):
        return tuple(self._situation_seed.invited_sim_infos_gen())

    def create_calendar_entry(self):
        calendar_entry = super().create_calendar_entry()
        situation_type = self._situation_seed.situation_type
        calendar_entry.zone_id = self._situation_seed.zone_id
        build_icon_info_msg(IconInfoData(icon_resource=situation_type.calendar_icon), situation_type.display_name, calendar_entry.icon_info)
        calendar_entry.scoring_enabled = self._situation_seed.scoring_enabled
        return calendar_entry

    def create_calendar_alert(self):
        calendar_alert = super().create_calendar_alert()
        situation_type = self._situation_seed.situation_type
        calendar_alert.zone_id = self._situation_seed.zone_id
        if self._situation_seed.situation_type.calendar_alert_description is not None:
            calendar_alert.description = situation_type.calendar_alert_description
        build_icon_info_msg(IconInfoData(icon_resource=situation_type.calendar_icon), situation_type.display_name, calendar_alert.calendar_icon)
        calendar_alert.show_go_to_button = True
        return calendar_alert

    def save(self, drama_node_proto):
        super().save(drama_node_proto)
        self._situation_seed.serialize_to_proto(drama_node_proto.stored_situation)

    def load(self, drama_node_proto, schedule_alarm=True):
        super_success = super().load(drama_node_proto, schedule_alarm=schedule_alarm)
        if not super_success:
            return False
        self._situation_seed = SituationSeed.deserialize_from_proto(drama_node_proto.stored_situation)
        if self._situation_seed is None:
            return False
        if not self.get_sender_sim_info().is_npc:
            services.calendar_service().mark_on_calendar(self, advance_notice_time=self.advance_notice_time())
        return True

    def try_move_special_object_from_hidden(self):
        situation_seed = self.get_situation_seed()
        if situation_seed is None or not (situation_seed.special_object_definition_id and situation_seed.host_sim_id):
            return
        host_sim_info = services.sim_info_manager().get(situation_seed.host_sim_id)
        host_sim = host_sim_info.get_sim_instance() if host_sim_info is not None else None
        if host_sim is None:
            logger.warn(f'Host sim not found for situation {situation_seed.situation_id}.')
            return
        special_object_def = services.definition_manager().get(situation_seed.special_object_definition_id)
        if special_object_def is None:
            logger.error(f'Special object definition id {situation_seed.special_object_definition_id} was not found.')
            return
        special_object = host_sim.inventory_component.get_item_with_definition(special_object_def)
        if special_object is not None:
            host_sim.inventory_component.try_move_hidden_object_to_inventory(special_object)
lock_instance_tunables(PlayerPlannedDramaNode, ui_display_data=None)