from date_and_time import create_time_span, TimeSpanfrom drama_scheduler.drama_node import BaseDramaNode, DramaNodeRunOutcomefrom drama_scheduler.drama_node_types import DramaNodeTypefrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import classproperty, flexmethodfrom travel_group.travel_group_stayover import TravelGroupStayoverfrom ui.ui_dialog import UiDialogOk, UiDialogOkCancel, UiDialogResponse, ButtonTypefrom venues.venue_event_drama_node import VenueEventDramaNodeimport clockimport servicesimport sims4.logZONE_ID_TOKEN = 'zone_id'HOUSEHOLD_ID_TOKEN = 'household_id'DURATION_TOKEN = 'duration'GUEST_SIM_IDS_TOKEN = 'guest_sim_ids'BEHHAVIOR_SITUATION_ID_TOKEN = 'behavior_situation_id'logger = sims4.log.Logger('PlayerPlannedStayoverDramaNode', default_owner='nabaker')
class PlayerPlannedStayoverDramaNode(BaseDramaNode):
    RESPONSE_ID_GO_HOME = 0
    INSTANCE_TUNABLES = {'existing_travel_group_dialog': UiDialogOkCancel.TunableFactory(description='\n            The ok cancel dialog that will display to the user if there are any conflicting travel groups.  Reasons\n            for conflict will be a passed in bulleted list as first (scripted) token.  O.K. cancels the travel group(s) involved in any conflicts. and\n            starts the new stayover.  Cancel cancels the new stayover.\n            '), 'confirm_dialog': UiDialogOkCancel.TunableFactory(description='\n            The ok cancel dialog that will display to the user if there are no conflicts.\n            '), 'invalid_dialog': UiDialogOk.TunableFactory(description='\n            The ok dialog that will display to the user if it is no longer possible to start the stayover.  (e.g. too\n            many sims due to addition or somesuch.)\n            '), 'existing_household_vacation_error_text': TunableLocalizedStringFactory(description='\n            Bulletpoint if members of active household are already on a vacation.\n            '), 'existing_household_stayover_error_text': TunableLocalizedStringFactory(description='\n            Bulletpoint if stayover already in progress on active households zone.\n            '), 'existing_guest_vacation_error_text': TunableLocalizedStringFactory(description='\n            Bulletpoint for any guests household that is already on a vacation/stayover. \n            (Household name is first parameter).\n            '), 'existing_guest_stayover_error_text': TunableLocalizedStringFactory(description='\n            Bulletpoint for any guests household that is already involved in hosting a stayover.\n            (Household name is first parameter).\n            '), 'calendar_alert_description': TunableLocalizedStringFactory(description='\n            Description that shows in the calendar alert.\n            '), 'travel_home_text': TunableLocalizedStringFactory(description='\n            Button text for travel home button if off lot.\n            '), 'travel_home_disabled_text': TunableLocalizedStringFactory(description='\n            Tooltip text for travel home button if off lot but unable to travel.\n            ')}

    @classproperty
    def persist_when_active(cls):
        return True

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.STAYOVER

    def __init__(self, *args, uid=None, zone_id=None, household_id=None, duration=None, guest_sim_ids=[], behavior_situation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._zone_id = zone_id
        self._household_id = household_id
        self._duration = duration
        self._guest_sim_ids = guest_sim_ids
        self._behavior_situation = behavior_situation

    @property
    def duration(self):
        return self._duration

    @property
    def guest_sim_ids(self):
        return self._guest_sim_ids

    @property
    def _require_instanced_sim(self):
        return False

    def _validate_stayover(self):
        if self._zone_id is None or (self._household_id is None or self._duration is None) or self._guest_sim_ids and self._behavior_situation is None:
            return False
        household = services.household_manager().get(self._household_id)
        if household.home_zone_id != self._zone_id:
            return False
        total_count = len(household) + len(self._guest_sim_ids)
        roommate_service = services.get_roommate_service()
        if roommate_service is not None:
            total_count += roommate_service.get_roommate_count(household.home_zone_id)
        if total_count > TravelGroupStayover.HOUSEHOLD_AND_GUEST_MAXIMUM:
            return False
        sim_info_manager = services.sim_info_manager()
        for sim_id in self._guest_sim_ids:
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                return False
            if not sim_info.can_instantiate_sim:
                return False
            if sim_info.is_selectable:
                return False
        return True

    def on_situation_creation_during_zone_spin_up(self) -> None:
        result = services.drama_scheduler_service().schedule_node(self.__class__, self._get_resolver(), specific_time=services.time_service().sim_now, drama_inst=self)
        if result is None:
            services.drama_scheduler_service().complete_node(self.uid)

    def _run(self):
        delay_result = self.try_do_travel_dialog_delay()
        if delay_result is not None:
            return delay_result
        if services.ui_dialog_service().has_active_modal_dialogs():
            current_time = services.time_service().sim_now
            self._selected_time = current_time + create_time_span(minutes=5)
            if not self._schedule_alarm():
                return DramaNodeRunOutcome.FAILURE
            return DramaNodeRunOutcome.RESCHEDULED
        household = services.household_manager().get(self._household_id)
        if not self._validate_stayover():
            if household.is_active_household:
                fail_dialog = self.invalid_dialog(services.active_sim_info(), None)
                fail_dialog.show_dialog()
            return DramaNodeRunOutcome.FAILURE
        additional_responses = None
        if household.home_zone_id != services.current_zone_id():
            disabled_text = None
            if services.get_zone_situation_manager().is_incompatible_user_facing_situation_running():
                disabled_text = self.travel_home_disabled_text()
            go_home_response = UiDialogResponse(dialog_response_id=self.RESPONSE_ID_GO_HOME, text=self.travel_home_text, disabled_text=disabled_text)
            additional_responses = (go_home_response,)
        error_strings = []
        travel_group_manager = services.travel_group_manager()
        if household.get_travel_group() is not None:
            error_strings.append(self.existing_household_vacation_error_text())
        if travel_group_manager.get_travel_group_by_zone_id(self._zone_id) is not None:
            error_strings.append(self.existing_household_stayover_error_text())
        household_set = set()
        for sim_info in self._get_guest_sim_infos():
            household_set.add(sim_info.household)
        for guest_household in household_set:
            if guest_household.get_travel_group() is not None:
                error_strings.append(self.existing_guest_vacation_error_text(guest_household.name))
            if travel_group_manager.get_travel_group_by_zone_id(guest_household.home_zone_id) is not None:
                error_strings.append(self.existing_guest_stayover_error_text(guest_household.name))
        if error_strings:
            if not household.is_active_household:
                return DramaNodeRunOutcome.FAILURE
            error_bullets = LocalizationHelperTuning.get_bulleted_list((None,), error_strings)
            error_dialog = self.existing_travel_group_dialog(self._receiver_sim_info, resolver=self._get_resolver())
            if additional_responses:
                error_dialog.set_responses(additional_responses)

            def error_resposne(dialog):
                if dialog.response is None or dialog.response != ButtonType.DIALOG_RESPONSE_OK and dialog.response != self.RESPONSE_ID_GO_HOME:
                    services.drama_scheduler_service().complete_node(self.uid)
                    return
                travel_group = household.get_travel_group()
                if travel_group is not None:
                    travel_group.end_vacation()
                travel_group = travel_group_manager.get_travel_group_by_zone_id(self._zone_id)
                if travel_group is not None:
                    travel_group.end_vacation()
                for response_household in household_set:
                    travel_group = response_household.get_travel_group()
                    if travel_group is not None:
                        travel_group.end_vacation()
                    travel_group = travel_group_manager.get_travel_group_by_zone_id(response_household.home_zone_id)
                    if travel_group is not None:
                        travel_group.end_vacation()
                self._start_stayover()
                if dialog.response == self.RESPONSE_ID_GO_HOME:
                    self.travel_to_destination()
                services.drama_scheduler_service().complete_node(self.uid)

            error_dialog.show_dialog(on_response=error_resposne, additional_tokens=(error_bullets,))
            return DramaNodeRunOutcome.SUCCESS_NODE_INCOMPLETE
        if not household.is_active_household:
            self._start_stayover()
            return DramaNodeRunOutcome.SUCCESS_NODE_COMPLETE
        dialog = self.confirm_dialog(self._receiver_sim_info, resolver=self._get_resolver())
        if additional_responses:
            dialog.set_responses(additional_responses)

        def response(dialog):
            if dialog.response is not None:
                if dialog.response == ButtonType.DIALOG_RESPONSE_OK:
                    self._start_stayover()
                elif dialog.response == self.RESPONSE_ID_GO_HOME:
                    self._start_stayover()
                    self.travel_to_destination()
            services.drama_scheduler_service().complete_node(self.uid)

        dialog.show_dialog(on_response=response)
        return DramaNodeRunOutcome.SUCCESS_NODE_INCOMPLETE

    def _start_stayover(self):
        create_timestamp = self._selected_time
        end_timestamp = create_timestamp + clock.interval_in_sim_days(self._duration)
        travel_group_manager = services.travel_group_manager()
        sim_info_manager = services.sim_info_manager()
        sim_infos = []
        for sim_id in self._guest_sim_ids:
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is not None:
                sim_infos.append(sim_info)
        travel_group_manager.create_travel_group_and_rent_zone(sim_infos=sim_infos, zone_id=self._zone_id, played=False, create_timestamp=create_timestamp, end_timestamp=end_timestamp, cost=0, stayover_situation=self._behavior_situation)

    @flexmethod
    def get_destination_lot_id(cls, inst):
        if inst is None:
            return services.active_household_lot_id()
        return services.get_persistence_service().get_lot_id_from_zone_id(inst._zone_id)

    @flexmethod
    def get_travel_interaction(cls, inst):
        return VenueEventDramaNode.GO_TO_VENUE_ZONE_INTERACTION

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO):
        success = super().schedule(resolver, specific_time=specific_time, time_modifier=time_modifier)
        if success:
            services.calendar_service().mark_on_calendar(self)
        return success

    def _validate_time(self, time_to_check):
        pass

    def cleanup(self, from_service_stop=False):
        services.calendar_service().remove_on_calendar(self.uid)
        super().cleanup(from_service_stop=from_service_stop)

    def _get_guest_sim_infos(self):
        sim_infos = []
        for sim_id in self._guest_sim_ids:
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info is not None:
                sim_infos.append(sim_info)
        return sim_infos

    def get_calendar_end_time(self):
        return self.selected_time + create_time_span(days=self._duration)

    def create_calendar_entry(self):
        calendar_entry = super().create_calendar_entry()
        calendar_entry.zone_id = self._zone_id
        calendar_entry.scoring_enabled = False
        calendar_entry.deletable = False
        for sim_id in self._guest_sim_ids:
            calendar_entry.household_sim_ids.append(sim_id)
        return calendar_entry

    def _save_custom_data(self, writer):
        if self._zone_id is not None:
            writer.write_uint64(ZONE_ID_TOKEN, self._zone_id)
        if self._household_id is not None:
            writer.write_uint64(HOUSEHOLD_ID_TOKEN, self._household_id)
        if self._duration is not None:
            writer.write_uint64(DURATION_TOKEN, self._duration)
        if self._guest_sim_ids:
            writer.write_uint64s(GUEST_SIM_IDS_TOKEN, self._guest_sim_ids)
        if self._behavior_situation is not None:
            writer.write_uint64(BEHHAVIOR_SITUATION_ID_TOKEN, self._behavior_situation.guid64)

    def _load_custom_data(self, reader):
        super_success = super()._load_custom_data(reader)
        if not super_success:
            return False
        self._zone_id = reader.read_uint64(ZONE_ID_TOKEN, None)
        if self._zone_id is None:
            return False
        self._household_id = reader.read_uint64(HOUSEHOLD_ID_TOKEN, None)
        if self._household_id is None:
            return False
        self._duration = reader.read_uint64(DURATION_TOKEN, None)
        if self._duration is None:
            return False
        self._guest_sim_ids = reader.read_uint64s(GUEST_SIM_IDS_TOKEN, ())
        if not self._guest_sim_ids:
            return False
        else:
            self._behavior_situation = services.get_instance_manager(sims4.resources.Types.SITUATION).get(reader.read_uint64(BEHHAVIOR_SITUATION_ID_TOKEN, 0))
            if self._behavior_situation is None:
                return False
        return True

    def load(self, drama_node_proto, schedule_alarm=True):
        super_success = super().load(drama_node_proto, schedule_alarm=schedule_alarm)
        if not super_success:
            return False
        household = services.household_manager().get(self._household_id)
        if household is None:
            return False
        if household.home_zone_id != self._zone_id:
            return False
        if household.is_active_household:
            services.calendar_service().mark_on_calendar(self)
        return True
lock_instance_tunables(PlayerPlannedStayoverDramaNode, ui_display_data=None)