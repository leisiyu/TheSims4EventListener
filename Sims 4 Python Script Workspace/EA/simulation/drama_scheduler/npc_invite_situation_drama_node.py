import randomfrom drama_scheduler.drama_node import BaseDramaNode, _DramaParticipant, DramaNodeRunOutcomefrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import DoubleSimResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableTestSetfrom gsi_handlers.drama_handlers import GSIRejectedDramaNodeScoringDatafrom interactions import ParticipantTypefrom sims4.tuning.tunable import TunableReference, OptionalTunable, Tunable, TunableTuple, TunableList, TunableEnumEntry, TunableVariant, TunableWorldDescription, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.npc_hosted_situations import NPCHostedSituationDialogfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom ui.ui_dialog import ButtonTypefrom ui.ui_dialog_picker import SimPickerRowimport build_buyimport servicesimport sims4.resourcesimport telemetry_helperlogger = sims4.log.Logger('DramaNode', default_owner='jjacobson')TELEMETRY_GROUP_SITUATIONS = 'SITU'TELEMETRY_HOOK_SITUATION_INVITED = 'INVI'TELEMETRY_HOOK_SITUATION_ACCEPTED = 'ACCE'TELEMETRY_HOOK_SITUATION_REJECTED = 'REJE'TELEMETRY_SITUATION_TYPE_ID = 'type'TELEMETRY_GUEST_COUNT = 'gcou'TELEMETRY_CHOSEN_ZONE = 'czon'telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SITUATIONS)ZONE_ID_TOKEN = 'zone_id'STREET_TOKEN = 'street'
class NPCInviteSituationDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'sender_sim_info': _DramaParticipant(description='\n            Tuning for selecting the sending sim.\n            \n            The sending sim is considered the sim who will be sending this\n            DramaNode.\n            ', excluded_options=('no_participant',), tuning_group=GroupNames.PARTICIPANT), 'is_simless': Tunable(description='\n            If checked, this DramaNode won\'t be associated with any sims. This\n            means the receiver will be whoever the active sim is when it runs, \n            regardless of who is tuned as the Receiver Sim. This sim will not \n            be automatically invited to the situation unless they are chosen \n            by the player in the "travel with" picker.\n            \n            This also means there will be no sender sim regardless of what\n            was tuned. \n            ', tunable_type=bool, default=False, tuning_group=GroupNames.PARTICIPANT), 'run_over_user_facing_situations': Tunable(description='\n            If checked, the drama node will trigger even during other\n            user facing situations (and certain festivals).\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_situation_to_run': TunableReference(description='\n            The situation that this drama node will try and start.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), tuning_group=GroupNames.SITUATION), '_NPC_host_job': OptionalTunable(description='\n            If enabled then the NPC host will be assigned this specific job in\n            the situation.\n            ', tunable=TunableReference(description='\n                The job that will be assigned to the NPC host of an NPC hosted\n                situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), tuning_group=GroupNames.SITUATION), '_use_alternate_host': OptionalTunable(description='\n            If enabled then we will find a different host Sim for this\n            situation rather than using the Sending Sim as the host.\n            ', tunable=TunableReference(description='\n                The filter that we will use to fine and potentially\n                generate a new host Sim for this situation.  This will\n                be run off of the sending Sim as the requesting Sim unless\n                NPC Hosted Situation Use Player Sim As Filter Requester\n                has been checked.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)), tuning_group=GroupNames.SITUATION), '_NPC_hosted_situation_start_messages': TunableList(description="\n            A List of tests and UiDialogs that should be considered for showing\n            as an npc invite. \n            \n            If more than one dialog passes all of it's tests\n            then one dialog will be chosen at random.\n            ", tunable=TunableTuple(description='\n                A combination of UiDialog and test where if the tuned tests pass\n                then the dialog will be considered as a choice to be displayed. \n                After all choices have been tested one of the dialogs will be\n                chosen at random.\n                ', dialog=NPCHostedSituationDialog.TunableFactory(description='\n                    The message that will be displayed when this situation\n                    tries to start for the initiating sim.\n                    '), tests=TunableTestSet(), dialog_complete_loot_list=TunableList(description='\n                    A list of loot that will always be applied, either when the player responds to the dialog or, if the \n                    dialog is a phone ring or text message, when the dialog times out due to the player ignoring it.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), dialog_canceled_loot_list=TunableList(description='\n                    A list of loot that will only be applied when the player responds canceling the dialog.  If the dialog is a\n                    phone ring or text message then this loot will NOT be triggered when the dialog times out due to the\n                    player ignoring it.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), dialog_seen_loot_list=TunableList(description='\n                    A list of loot that will only be applied when the player responds to the dialog.  If the dialog is a\n                    phone ring or text message then this loot will NOT be triggered when the dialog times out due to the\n                    player ignoring it.\n                    ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True))), tuning_group=GroupNames.SITUATION), '_NPC_hosted_situation_player_job': OptionalTunable(description='\n            The job that the player will be put into when they they are\n            invited into an NPC hosted version of this event.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), tuning_group=GroupNames.SITUATION), '_NPC_hosted_situation_use_player_sim_as_filter_requester': Tunable(description='\n            If checked then when gathering sims for an NPC hosted situation\n            the filter system will look at households and and relationships\n            relative to the player sim rather than the NPC host.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_host_event_at_NPCs_residence': Tunable(description="\n            If checked then the situation will be started at the NPC host's\n            residence rather than just choosing a venue type.  If the NPC\n            host does not have a residence, then we use the venue type as\n            a backup.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_NPC_hosted_situation_scoring_enabled': Tunable(description='\n            If checked then the NPC hosted situation will start with\n            scoring enabled.  If unchecked the situation will have scoring\n            disabled and no rewards will be given.  If you check the Hidden\n            Scoring Override then the and leave this unchecked then the\n            event will look like an event with no score, but score will\n            still be tracked and rewards will still be given.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_require_predefined_guest_list': Tunable(description='\n            If checked then the situation will not start if there is no\n            predefined guest list.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION), '_user_facing': Tunable(description='\n            If checked then the situation will be user facing.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.SITUATION), '_show_venue_dialog': Tunable(description='\n            If checked then we show the name and icon of the venue you will\n            travel to.\n            ', tunable_type=bool, default=True), 'street': OptionalTunable(description='\n            The street that the situation will take place at. \n            ', tunable=TunableReference(description='\n                Identify a specific Street.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STREET)), disabled_name='any_street', enabled_name='specific_street'), 'spawn_sims_during_zone_spin_up': Tunable(description='\n            If checked, the situation will try to spawn situation sims during \n            zone spin up. Check this if you want sims who were not explicitly \n            invited (i.e. autofilled) to already be at the lot after\n            traveling.  \n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION)}

    @classmethod
    def _verify_tuning_callback(cls):
        if not cls.is_simless:
            return
        for dialog_and_tests in cls._NPC_hosted_situation_start_messages:
            dialog = dialog_and_tests.dialog
            if dialog.bring_other_sims is None:
                logger.error("{} is tuned to be simless, but at least one of the NPC hosted situation start messages has 'bring other sims' disabled. This is not allowed.", cls)
                return

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.SITUATION

    @classproperty
    def simless(cls):
        return cls.is_simless

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zone_id = None
        self._street = None
        self._chosen_dialog_data = None
        self._sim_infos_for_travel_picker = None

    def _get_zone_id(self):
        if self._zone_id is not None and self._situation_to_run.is_venue_location_valid(self._zone_id):
            return self._zone_id
        self._zone_id = None
        if self._street is not None:
            lot_id = self._street.get_lot_to_travel_to()
            if lot_id is None:
                return services.current_zone_id()
            persistence_service = services.get_persistence_service()
            self._zone_id = persistence_service.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
            return self._zone_id
        if self._host_event_at_NPCs_residence:
            zone_id = self._sender_sim_info.vacation_or_home_zone_id
            if zone_id is not None:
                self._zone_id = zone_id
                return self._zone_id
        if self._situation_to_run.has_venue_location():
            zone_id = self._situation_to_run.get_venue_location()
            if zone_id is not None:
                self._zone_id = zone_id
        return self._zone_id

    def _get_resolver(self):
        resolver = super()._get_resolver()
        resolver.set_additional_participant(ParticipantType.PickedZoneId, (self._get_zone_id(),))
        return resolver

    def _get_host(self, additional_sims_to_bring):
        if self._use_alternate_host is None:
            return self._sender_sim_info
        blacklist = {sim_info.id for sim_info in additional_sims_to_bring}
        blacklist.add(self._sender_sim_info.id)
        blacklist.intersection_update({sim_info.id for sim_info in services.active_household()})
        if self._NPC_hosted_situation_use_player_sim_as_filter_requester:
            requesting_sim_info = self._receiver_sim_info
        else:
            requesting_sim_info = self._sender_sim_info
        host = services.sim_filter_service().submit_matching_filter(sim_filter=self._use_alternate_host, requesting_sim_info=requesting_sim_info, blacklist_sim_ids=blacklist, allow_yielding=False, gsi_source_fn=lambda : 'NPC Invite Situation: {} is the host filter for this situation'.format(str(self._use_alternate_host)))
        if not host:
            return
        return next(iter(host)).sim_info

    def _get_situation_guest_list(self, additional_sims_to_bring=()):
        host_sim_info = self._get_host(additional_sims_to_bring)
        if host_sim_info is None:
            if not self.simless:
                logger.error('DramaNode {} failed to start its situation. No host found.', self)
                return
            host_sim_id = 0
        else:
            host_sim_id = host_sim_info.id
        guest_list = self._situation_to_run.get_predefined_guest_list()
        if guest_list is None:
            if self._require_predefined_guest_list:
                return
            guest_list = SituationGuestList(invite_only=True, host_sim_id=host_sim_id)
        if self._NPC_hosted_situation_player_job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(self._receiver_sim_info.id, self._NPC_hosted_situation_player_job, SituationInvitationPurpose.INVITED))
        if self._NPC_host_job is not None:
            guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(host_sim_id, self._NPC_host_job, SituationInvitationPurpose.INVITED))
        if additional_sims_to_bring:
            additional_sims_job = self._chosen_dialog_data.dialog.bring_other_sims.situation_job
            for sim_info in additional_sims_to_bring:
                guest_list.add_guest_info(SituationGuestInfo.construct_from_purpose(sim_info.id, additional_sims_job, SituationInvitationPurpose.INVITED))
        if self._NPC_hosted_situation_use_player_sim_as_filter_requester:
            guest_list.filter_requesting_sim_id = self._receiver_sim_info.id
        return guest_list

    def _create_situation(self, additional_sims_to_bring=()):
        guest_list = self._get_situation_guest_list(additional_sims_to_bring=additional_sims_to_bring)
        if guest_list is None:
            return
        services.get_zone_situation_manager().create_situation(self._situation_to_run, guest_list=guest_list, zone_id=self._get_zone_id(), scoring_enabled=self._NPC_hosted_situation_scoring_enabled, user_facing=self._user_facing, allow_uninstanced_main_traveler=self.simless, spawn_sims_during_zone_spin_up=self.spawn_sims_during_zone_spin_up)
        with telemetry_helper.begin_hook(telemetry_writer, TELEMETRY_HOOK_SITUATION_ACCEPTED, sim_info=self._receiver_sim_info) as hook:
            hook.write_guid(TELEMETRY_SITUATION_TYPE_ID, self._situation_to_run.guid64)
            hook.write_int(TELEMETRY_GUEST_COUNT, len(additional_sims_to_bring))

    def _handle_picker_dialog(self, dialog):
        if not dialog.accepted:
            with telemetry_helper.begin_hook(telemetry_writer, TELEMETRY_HOOK_SITUATION_REJECTED, sim_info=self._receiver_sim_info) as hook:
                hook.write_guid('type', self._situation_to_run.guid64)
        else:
            picked_sims = dialog.get_result_tags()
            self._create_situation(additional_sims_to_bring=picked_sims)
        services.drama_scheduler_service().complete_node(self.uid)

    def _get_sim_infos_for_travel_picker(self):
        if self._sim_infos_for_travel_picker is not None:
            return self._sim_infos_for_travel_picker
        self._sim_infos_for_travel_picker = ()
        bring_other_sims_data = self._chosen_dialog_data.dialog.bring_other_sims
        if bring_other_sims_data is None:
            return ()
        if self.simless:
            blacklist = None
        else:
            blacklist = {sim_info.id for sim_info in self._sender_sim_info.household.sim_info_gen()}
            blacklist.add(self._receiver_sim_info.id)
        results = services.sim_filter_service().submit_filter(bring_other_sims_data.travel_with_filter, callback=None, requesting_sim_info=self._receiver_sim_info, blacklist_sim_ids=blacklist, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
        if not results:
            return ()
        sim_infos = tuple(result.sim_info for result in results)
        self._sim_infos_for_travel_picker = sim_infos
        return sim_infos

    def _handle_invite_dialog_canceled(self, resolver):
        for loot_action in self._chosen_dialog_data.dialog_canceled_loot_list:
            loot_action.apply_to_resolver(resolver)

    def _handle_dialog(self, dialog):
        resolver = self._get_resolver()
        for loot_action in self._chosen_dialog_data.dialog_complete_loot_list:
            loot_action.apply_to_resolver(resolver)
        if dialog.response is not None and dialog.response == ButtonType.DIALOG_RESPONSE_CANCEL:
            self._handle_invite_dialog_canceled(resolver)
        if dialog.response != ButtonType.DIALOG_RESPONSE_NO_RESPONSE:
            for loot_action in self._chosen_dialog_data.dialog_seen_loot_list:
                loot_action.apply_to_resolver(resolver)
        additional_valid_responses = (NPCHostedSituationDialog.BRING_OTHER_SIMS_RESPONSE_ID, NPCHostedSituationDialog.BRING_ONE_OTHER_SIM_RESPONSE_ID)
        if dialog.response is not None and dialog.accepted or dialog.response not in additional_valid_responses:
            with telemetry_helper.begin_hook(telemetry_writer, TELEMETRY_HOOK_SITUATION_REJECTED, sim_info=self._receiver_sim_info) as hook:
                hook.write_guid(TELEMETRY_SITUATION_TYPE_ID, self._situation_to_run.guid64)
            services.drama_scheduler_service().complete_node(self.uid)
            return
        sim_infos = self._get_sim_infos_for_travel_picker()
        if dialog.response == NPCHostedSituationDialog.BRING_ONE_OTHER_SIM_RESPONSE_ID:
            self._create_situation(additional_sims_to_bring=sim_infos)
            services.drama_scheduler_service().complete_node(self.uid)
            return
        if dialog.response == NPCHostedSituationDialog.BRING_OTHER_SIMS_RESPONSE_ID:
            self._show_bring_sims_picker()
            return
        self._create_situation()
        services.drama_scheduler_service().complete_node(self.uid)

    def _populate_bring_sims_picker(self, picker_dialog):
        sim_infos = self._get_sim_infos_for_travel_picker()
        for sim_info in sim_infos:
            picker_dialog.add_row(SimPickerRow(sim_info.sim_id, tag=sim_info))

    def _show_bring_sims_picker(self):
        bring_other_sims_data = self._chosen_dialog_data.dialog.bring_other_sims
        dialog_owner = self._receiver_sim_info if not self.simless else None
        picker_dialog = bring_other_sims_data.picker_dialog(dialog_owner, resolver=self._get_resolver())
        self._populate_bring_sims_picker(picker_dialog)
        picker_dialog.show_dialog(on_response=self._handle_picker_dialog)

    def get_sim_filter_gsi_name(self):
        return str(self)

    def run(self):
        if self.simless:
            self._receiver_sim_info = services.active_sim_info()
            self._sender_sim_info = None
        return super().run()

    def _run(self):
        zone_id = self._get_zone_id()
        with telemetry_helper.begin_hook(telemetry_writer, TELEMETRY_HOOK_SITUATION_INVITED, sim_info=self._receiver_sim_info) as hook:
            hook.write_guid(TELEMETRY_SITUATION_TYPE_ID, self._situation_to_run.guid64)
            hook.write_int(TELEMETRY_CHOSEN_ZONE, zone_id)
        additional_tokens = []
        if zone_id == 0:
            logger.error('Drama Node {} trying to be run with zone id of 0.  This is probably an issue with getting the zone id from the street.', self)
            zone_id = services.current_zone_id()
        venue_tuning_id = build_buy.get_current_venue(zone_id)
        if venue_tuning_id is not None:
            venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
            venue_tuning = venue_manager.get(venue_tuning_id)
            if venue_tuning is not None:
                additional_tokens.append(venue_tuning.display_name)
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data is not None:
            additional_tokens.append(zone_data.name)
        self._choose_dialog()
        sim_infos_to_bring = self._get_sim_infos_for_travel_picker()
        if len(sim_infos_to_bring) == 1:
            additional_tokens.append(sim_infos_to_bring[0])
        if self._chosen_dialog_data is None or self._chosen_dialog_data.dialog is None:
            return DramaNodeRunOutcome.FAILURE
        if self._chosen_dialog_data.dialog.bring_other_sims is not None and not (self._receiver_sim_info or sim_infos_to_bring):
            return DramaNodeRunOutcome.FAILURE
        dialog_owner = self._receiver_sim_info if not self.simless else None
        target_sim_id = self._sender_sim_info.id if not self.simless else None
        dialog = self._chosen_dialog_data.dialog(dialog_owner, target_sim_id=target_sim_id, resolver=self._get_resolver(), is_simless=self.simless, sim_infos_to_bring=sim_infos_to_bring)
        dialog_zone_id = zone_id if self._show_venue_dialog else None
        dialog.show_dialog(on_response=self._handle_dialog, zone_id=dialog_zone_id, additional_tokens=additional_tokens)
        return DramaNodeRunOutcome.SUCCESS_NODE_INCOMPLETE

    def _choose_dialog(self):
        choices = []
        resolver = DoubleSimResolver(self._receiver_sim_info, self._sender_sim_info)
        for dialog_data in self._NPC_hosted_situation_start_messages:
            if dialog_data.tests.run_tests(resolver):
                choices.append(dialog_data)
        if choices:
            self._chosen_dialog_data = random.choice(choices)

    def _test(self, resolver, skip_run_tests=False):
        if self._get_zone_id() is None:
            return TestResult(False, 'Cannot run because there is no zone to run this at.')
        if self._sender_sim_info is None and not self.simless:
            return TestResult(False, 'Cannot run because there is no sender sim info.')
        if skip_run_tests or self.run_over_user_facing_situations or services.get_zone_situation_manager().is_incompatible_user_facing_situation_running(global_user_facing_only=True):
            return TestResult(False, 'Did not start NPC Hosted Situation because user facing situation was running.')
        if skip_run_tests or services.get_persistence_service().is_save_locked():
            return TestResult(False, 'Could not start situation since the game is save locked.')
        result = super()._test(resolver, skip_run_tests=skip_run_tests)
        if not result:
            return result
        return TestResult.TRUE

    def _setup(self, *args, street_override=None, gsi_data=None, zone_id=None, **kwargs):
        result = super()._setup(*args, gsi_data=gsi_data, **kwargs)
        if not result:
            return result
        else:
            if zone_id is not None:
                self._zone_id = zone_id
            if street_override is not None:
                self._street = street_override
            else:
                self._street = self.street
            if self._get_zone_id() is None:
                if gsi_data is not None:
                    gsi_data.rejected_nodes.append(GSIRejectedDramaNodeScoringData(type(self), 'There is no valid zone found when trying to setup this drama node.'))
                return False
        return True

    def cleanup(self, from_service_stop=False):
        super().cleanup(from_service_stop=from_service_stop)
        self._zone_id = None
        self._street = None

    def _save_custom_data(self, writer):
        if self._zone_id is not None:
            writer.write_uint64(ZONE_ID_TOKEN, self._zone_id)
        if self._street is not None:
            writer.write_uint64(STREET_TOKEN, self._street.guid64)

    def _load_custom_data(self, reader):
        self._zone_id = reader.read_uint64(ZONE_ID_TOKEN, None)
        street_id = reader.read_uint64(STREET_TOKEN, None)
        if street_id is not None:
            self._street = services.get_instance_manager(sims4.resources.Types.STREET).get(street_id)
        return True
