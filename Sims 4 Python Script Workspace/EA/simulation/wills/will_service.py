from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from protocolbuffers.FileSerialization_pb2 import SaveGameData
    from sims.household import Household
    from sims.sim_info import SimInfofrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolver, SingleSimAndHouseholdResolverfrom persistence_error_types import ErrorCodesfrom protocolbuffers import GameplaySaveData_pb2from protocolbuffers.Localization_pb2 import LocalizedStringfrom sims4 import protocol_buffer_utilsfrom sims4.localization import TunableLocalizedStringFactory, TunableLocalizedString, LocalizationHelperTuning, _create_localized_stringfrom sims4.common import Packfrom sims4.tuning.tunable import TunablePackSafeReference, TunableRange, TunableList, TunableTuple, TunableReference, OptionalTunablefrom sims4.utils import classpropertyfrom tunable_time import TunableTimeSpanfrom ui.ui_dialog_notification import UiDialogNotificationfrom wills.will import SimWill, HouseholdWillimport build_buyimport randomimport servicesimport sims4.loglogger = sims4.log.Logger('WillService', default_owner='madang')
class WillService(sims4.service_manager.Service):
    DELIVER_WILL_TO_RECIPIENT_LOOT = TunablePackSafeReference(description="\n        A ScheduledDeliveryLoot applied when sending a deceased Sim's Will to a recipient\n        household.\n        ", manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('ScheduledDeliveryLoot',))
    DELIVER_WILL_DELAY = TunableTimeSpan(description='\n        The TimeSpan that the delivery of Wills will be delayed.\n        ')
    SIM_WILL_FUNERAL_ACTIVITY_PREFERENCE_MAX = TunableRange(description='\n        The maximum number of funeral activity preferences a Sim is allowed to set in \n        their SimWill.\n        ', tunable_type=int, default=3, minimum=1)
    DEPENDENT_INHERITANCE_FAIL_NOTIFICATION = UiDialogNotification.TunableFactory(description="\n        The notification to display if a recipient household fails to claim a \n        HouseholdWill's intended dependents.\n        Additional tokens:\n        Dependent household name\n        Recipient household name\n        ")
    ACTIVE_SIM_WILL_TEXT = TunableLocalizedStringFactory(description="\n        Body text of an active SimWill, displayed in a TNS for reviewing a Sim's own \n        Will.\n        e.g. This will take effect when {0.SimFirstName} dies:\n\n{1.String}\n        ")
    ACTIVE_HOUSEHOLD_WILL_HEADER_TEXT = TunableLocalizedStringFactory(description="\n        Body text of an active HouseholdWill, displayed in a TNS for reviewing a Sim's \n        Household Will.\n        e.g. This will take effect when all adults and teens in the {0.Household} \n        Household die:\n\n        ")
    EXECUTED_WILL_READING_TEXT = TunableLocalizedStringFactory(description="\n        Body text of an executed Will, displayed in a TNS when a Sim reads a deceased \n        Sim's Will.\n        e.g. {0.SimFirstName}'s Will has arrived!\n\n{1.String}\n        ")
    SIM_WILL_MOOD_TEXT = TunableLocalizedStringFactory(description='\n        A SimWill mood (emotion) text.  Used in a Will summary or reading TNS.\n        e.g. Mood: {0.String}\n\n        ')
    SIM_WILL_HEIRLOOM_DISTRIBUTION_ITEM_TEXT = TunableLocalizedStringFactory(description='\n        A SimWill heirloom object distribution list item.  Used in a Will summary or \n        reading TNS.\n        e.g. {0.String}: {1.SimFullName}\n\n        ')
    SIM_WILL_BURIAL_PREFERENCE_TEXT = TunableLocalizedStringFactory(description='\n        A SimWill burial preference text.  Used in a Will summary or reading TNS.\n        e.g. Remains: {0.String}\n\n        ')
    SIM_WILL_FUNERAL_ACTIVITY_PREFERENCE_TEXT = TunableLocalizedStringFactory(description='\n        The SimWill funeral activity preferences text.  Used in a Will summary or reading\n        TNS.\n        e.g. Funeral activities: {0.String}\n\n        ')
    HH_WILL_SIMOLEON_HH_RECIPIENT_ITEM_TEXT = TunableLocalizedStringFactory(description='\n        A HouseholdWill simoleon distribution list item for a household recipient.  Used \n        in a Will summary or reading TNS.\n        e.g. {0.Number}% of Simoleons: {1.String} Household\n\n        ')
    HH_WILL_SIMOLEON_CHARITY_RECIPIENT_ITEM_TEXT = TunableLocalizedStringFactory(description='\n        A HouseholdWill simoleon distribution list item for the charity recipient.  Used \n        in a Will summary or reading TNS.\n        e.g. {0.Number}% of Simoleons: Charity\n\n        ')
    HH_WILL_DEPENDENT_DISTRIBUTION_ITEM_TEXT = TunableLocalizedStringFactory(description='\n        A HouseholdWill dependent distribution list item.  Used in a Will summary or \n        reading TNS.\n        e.g. {0.SimFullName}: {1.Household} Household\n\n        ')
    SIM_WILL_NOTE_TEXT = TunableLocalizedStringFactory(description='\n        The SimWill note text.  Used in a Will summary or reading TNS.\n        e.g. Note: {0.String}\n        ')
    WILL_READING_NOTIFICATION = UiDialogNotification.TunableFactory(description="\n        The notification to display a Sim's Will contents.\n        Additional tokens:\n        The entire will content string\n        ")
    SHADY_MERCHANT_TUNING = TunableTuple(description='\n        Tuning specifically for the Shady Merchant NPC generated premade will.\n        ', burial_object_def_list=TunableList(description='\n            A list of burial object definitions, from which a random definition may be\n            selected for the premade SimWill.\n            ', tunable=TunableReference(description='\n                Object definition of a burial object.\n                ', manager=services.definition_manager(), pack_safe=True)), funeral_activities_list=TunableList(description='\n            A list of available Funeral Activities, from which a random activity may be\n            selected for a premade SimWill generated by the Shady Merchant.\n            ', tunable=TunableReference(description='\n                The reference to a Funeral Situation Activity.\n                ', manager=services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION), class_restrictions=('SituationActivity',), pack_safe=True)), will_note_text=TunableLocalizedString(description='\n            The text to be set as the will note for all premade SimWills generated by the\n            Shady Merchant.\n            ', export_modes=sims4.tuning.tunable_base.ExportModes.All), shady_merchant_simoleon_cut=TunableRange(description="\n            The percentage of a household's Simoleons that the Shady Merchant NPC's household\n            will take.\n            ", tunable_type=float, default=0.6, minimum=0.0, maximum=1.0), funeral_activity_max=TunableRange(description='\n            The maximum number of funeral activity preferences that will be randomly \n            selected for a premade SimWill.\n            ', tunable_type=int, default=3, minimum=1))
    HEIRLOOM_INHERITANCE_LOOT = TunablePackSafeReference(description='\n        The loot that will be applied to an heirloom object upon inheritance.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))
    DELIVERY_NOTIFICATION_LOOT = OptionalTunable(description="\n        If enabled, this loot will be applied to each Will recipient upon the Will \n        owner's death, to give the pending Will delivery better visibility.\n        ", tunable=TunablePackSafeReference(description='\n            The loot that will be applied to a Will recipient.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)))

    def __init__(self) -> 'None':
        self._sim_wills = {}
        self._household_wills = {}

    @classproperty
    def required_packs(cls) -> 'Tuple[Pack]':
        return (Pack.EP17,)

    @classproperty
    def save_error_code(cls) -> 'ErrorCodes':
        return ErrorCodes.SERVICE_SAVE_FAILED_WILL_SERVICE

    def get_sim_will(self, sim_id:'int') -> 'SimWill':
        if sim_id in self._sim_wills:
            return self._sim_wills[sim_id]

    def get_household_will(self, household_id:'int') -> 'HouseholdWill':
        if household_id in self._household_wills:
            return self._household_wills[household_id]

    def create_will(self, sim:'SimInfo') -> 'None':
        if sim is None or sim.id in self._sim_wills:
            return
        sim_will = SimWill(sim.id)
        self._sim_wills[sim.id] = sim_will
        if sim.household_id not in self._household_wills:
            household_will = HouseholdWill(sim.household_id)
            self._household_wills[sim.household_id] = household_will

    def destroy_sim_will(self, sim_id:'int') -> 'None':
        if sim_id not in self._sim_wills:
            return
        del self._sim_wills[sim_id]

    def destroy_household_will(self, household_id:'int') -> 'None':
        if household_id not in self._household_wills:
            return
        del self._household_wills[household_id]

    def finalize_will(self, sim:'SimInfo') -> 'None':
        sim_will = None
        if sim.id in self._sim_wills and not self._sim_wills[sim.id].is_finalized():
            sim_will = self._sim_wills[sim.id]
            sim_will.finalize_will()
        household = sim.household
        household_will = None
        if household.id in self._household_wills and not (self._household_wills[household.id].is_finalized() or any(sim_info is not sim and sim_info.can_live_alone for sim_info in household)):
            household_will = self._household_wills[household.id]
            household_will.finalize_will()
            if sim_will is None:
                self.create_will(sim)
                sim_will = self._sim_wills[sim.id]
                sim_will.finalize_will()
        recipient_households = set()
        if sim_will is not None:
            sim_info_manager = services.sim_info_manager()
            for sim_id in sim_will.get_sim_recipients():
                recipient_sim = sim_info_manager.get(sim_id)
                if recipient_sim is not None:
                    recipient_households.add(recipient_sim.household)
        if household_will is not None:
            household_manager = services.household_manager()
            for household_id in household_will.get_household_recipients():
                recipient_household = household_manager.get(household_id)
                if recipient_household is not None:
                    recipient_households.add(recipient_household)
        for recipient_hh in recipient_households:
            if self.DELIVERY_NOTIFICATION_LOOT is not None:
                resolver = SingleSimAndHouseholdResolver(sim, recipient_hh)
                self.DELIVERY_NOTIFICATION_LOOT.apply_to_resolver(resolver)
            self._mail_will_to_household(sim.id, recipient_hh)

    def _mail_will_to_household(self, deceased_sim_id:'int', recipient_household:'Household') -> 'None':
        delivery_tracker = recipient_household.delivery_tracker
        delivery_tracker.request_delivery(self.DELIVER_WILL_TO_RECIPIENT_LOOT.guid64, sim_id=None, time_span_from_now=self.DELIVER_WILL_DELAY(), sender_sim_id=deceased_sim_id)

    def _generate_sim_will_mood_content(self, sim_will:'SimWill') -> 'LocalizedString':
        mood_text = None
        mood = sim_will.get_emotion()
        if mood.mood_names:
            sim_info_manager = services.sim_info_manager()
            mood_text = self.SIM_WILL_MOOD_TEXT(_create_localized_string(mood.mood_names[0].hash, sim_info_manager.get(sim_will.get_will_owner_id())))
        return mood_text

    def _generate_sim_will_heirloom_content(self, sim_will:'SimWill') -> 'LocalizedString':
        heirloom_text = None
        heirloom_tokens = []
        sim_info_manager = services.sim_info_manager()
        obj_def_manager = services.definition_manager()
        heirloom_obj_data = sim_will.get_heirloom_object_data()
        for (object_id, recipient_sim_id) in sim_will.get_heirloom_distributions().items():
            recipient_sim_info = sim_info_manager.get(recipient_sim_id)
            if object_id in heirloom_obj_data.keys():
                object_data = heirloom_obj_data[object_id]
                object_definition = obj_def_manager.get(object_data.guid)
                heirloom_tokens.append(self.SIM_WILL_HEIRLOOM_DISTRIBUTION_ITEM_TEXT(object_definition, recipient_sim_info))
        if heirloom_tokens:
            heirloom_text = LocalizationHelperTuning.get_new_line_separated_strings(*heirloom_tokens)
        return heirloom_text

    def _generate_sim_will_burial_content(self, sim_will:'SimWill') -> 'LocalizedString':
        burial_text = None
        burial_obj_def_id = sim_will.get_burial_preference()
        if burial_obj_def_id:
            burial_obj_def = services.definition_manager().get(burial_obj_def_id)
            burial_text = self.SIM_WILL_BURIAL_PREFERENCE_TEXT(burial_obj_def)
        return burial_text

    def _generate_sim_will_funeral_content(self, sim_will:'SimWill') -> 'LocalizedString':
        funeral_activity_text = None
        activity_tokens = []
        funeral_activities = sim_will.get_funeral_activity_preferences()
        holiday_manager = services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION)
        for activity_id in funeral_activities:
            activity = holiday_manager.get(activity_id)
            if activity is not None:
                activity_tokens.append(activity.display_name)
        if activity_tokens:
            funeral_activity_text = self.SIM_WILL_FUNERAL_ACTIVITY_PREFERENCE_TEXT(LocalizationHelperTuning.get_comma_separated_list(*activity_tokens))
        return funeral_activity_text

    def _generate_household_will_dependent_content(self, household_will:'HouseholdWill') -> 'LocalizedString':
        dependent_text = None
        dependent_tokens = []
        dependent_distribution = household_will.get_dependent_distributions()
        sim_info_manager = services.sim_info_manager()
        hh_manager = services.household_manager()
        for (dependent_sim_id, destination_hh_id) in dependent_distribution.items():
            dependent_sim_info = sim_info_manager.get(dependent_sim_id)
            destination_household = hh_manager.get(destination_hh_id)
            if dependent_sim_info and destination_household:
                dependent_tokens.append(self.HH_WILL_DEPENDENT_DISTRIBUTION_ITEM_TEXT(dependent_sim_info, destination_household.name))
        if dependent_tokens:
            dependent_text = LocalizationHelperTuning.get_new_line_separated_strings(*dependent_tokens)
        return dependent_text

    def _generate_household_will_simoleon_content(self, household_will:'HouseholdWill') -> 'LocalizedString':
        simoleon_text = None
        simoleon_tokens = []
        simoleon_distribution = household_will.get_simoleon_distributions()
        hh_manager = services.household_manager()
        for (recipient_hh_id, percentage) in simoleon_distribution.items():
            recipient_household = hh_manager.get(recipient_hh_id)
            if recipient_household is not None:
                simoleon_tokens.append(self.HH_WILL_SIMOLEON_HH_RECIPIENT_ITEM_TEXT(percentage*100, recipient_household.name))
        charity_distribution = household_will.get_charity_distribution()
        if charity_distribution > 0:
            simoleon_tokens.append(self.HH_WILL_SIMOLEON_CHARITY_RECIPIENT_ITEM_TEXT(charity_distribution*100))
        if simoleon_tokens:
            simoleon_text = LocalizationHelperTuning.get_new_line_separated_strings(*simoleon_tokens)
        return simoleon_text

    def _generate_active_will_content(self, sim_info:'SimInfo') -> 'LocalizedString':
        if sim_info.id not in self._sim_wills:
            logger.warn('Sim {} does not have a SimWill to generate content from.', sim_info)
            return
        sim_will = self._sim_wills[sim_info.id]
        if sim_will.is_finalized():
            logger.warn('Cannot generate active will content text for the finalized SimWill for Sim {}', sim_info)
            return
        loc_strings = []
        heirloom_text = self._generate_sim_will_heirloom_content(sim_will)
        if heirloom_text is not None:
            loc_strings.append(heirloom_text)
        burial_text = self._generate_sim_will_burial_content(sim_will)
        if burial_text is not None:
            loc_strings.append(burial_text)
        funeral_text = self._generate_sim_will_funeral_content(sim_will)
        if funeral_text is not None:
            loc_strings.append(funeral_text)
        household_will = self._household_wills.get(sim_info.household_id)
        if household_will is not None:
            dependent_text = self._generate_household_will_dependent_content(household_will)
            simoleon_text = self._generate_household_will_simoleon_content(household_will)
            if dependent_text is not None or simoleon_text is not None:
                loc_strings.append(self.ACTIVE_HOUSEHOLD_WILL_HEADER_TEXT(sim_info.household.name))
            if dependent_text is not None:
                loc_strings.append(dependent_text)
            if simoleon_text is not None:
                loc_strings.append(simoleon_text)
        note_text = sim_will.get_note()
        if note_text is not None:
            loc_strings.append(note_text)
        mood_text = self._generate_sim_will_mood_content(sim_will)
        if mood_text is not None:
            loc_strings.append(mood_text)
        sim_content = LocalizationHelperTuning.get_new_line_separated_strings(*loc_strings) if loc_strings else LocalizationHelperTuning.get_raw_text('')
        return self.ACTIVE_SIM_WILL_TEXT(sim_info, sim_content)

    def _generate_finalized_will_content(self, sim_info:'SimInfo') -> 'LocalizedString':
        sim_will = None
        if sim_info.id in self._sim_wills:
            sim_will = self._sim_wills[sim_info.id]
            if not sim_will.is_finalized():
                logger.warn('Cannot generate finalized will content from an active SimWill for Sim {}', sim_info)
                return
        loc_strings = []
        if sim_will is not None:
            heirloom_text = self._generate_sim_will_heirloom_content(sim_will)
            if heirloom_text is not None:
                loc_strings.append(heirloom_text)
            burial_text = self._generate_sim_will_burial_content(sim_will)
            if burial_text is not None:
                loc_strings.append(burial_text)
            funeral_text = self._generate_sim_will_funeral_content(sim_will)
            if funeral_text is not None:
                loc_strings.append(funeral_text)
        household_will = self._household_wills.get(sim_will.get_household_id())
        if household_will is not None and household_will.is_finalized():
            dependent_text = self._generate_household_will_dependent_content(household_will)
            if dependent_text is not None:
                loc_strings.append(dependent_text)
            simoleon_text = self._generate_household_will_simoleon_content(household_will)
            if simoleon_text is not None:
                loc_strings.append(simoleon_text)
        if sim_will is not None:
            note_text = sim_will.get_note()
            if note_text is not None:
                loc_strings.append(note_text)
        sim_content = LocalizationHelperTuning.get_new_line_separated_strings(*loc_strings) if loc_strings else LocalizedString()
        return self.EXECUTED_WILL_READING_TEXT(sim_info, sim_content)

    def show_will_contents_notification(self, sim_info:'SimInfo') -> 'None':
        if sim_info is not None and sim_info.id in self._sim_wills:
            sim_will = self._sim_wills[sim_info.id]
            if not sim_will.is_finalized():
                will_content = self._generate_active_will_content(sim_info)
            else:
                will_content = self._generate_finalized_will_content(sim_info)
            will_reading_dialog = self.WILL_READING_NOTIFICATION(services.active_sim_info(), resolver=SingleSimResolver(sim_info))
            will_reading_dialog.show_dialog(additional_tokens=(will_content,))

    def claim_inheritance(self, deceased_sim_info:'SimInfo', recipient_sim_info:'SimInfo') -> 'None':
        if deceased_sim_info.id in self._sim_wills:
            sim_will = self._sim_wills[deceased_sim_info.id]
            if sim_will.is_finalized():
                for hh_sim_info in recipient_sim_info.household.sim_info_gen():
                    sim_will.apply_inheritance(hh_sim_info.id)
            deceased_household_id = sim_will.get_household_id()
            if deceased_household_id in self._household_wills:
                household_will = self._household_wills[deceased_household_id]
                if household_will.is_finalized():
                    household_will.apply_inheritance(recipient_sim_info.household_id)

    def generate_shady_merchant_will(self, sim_info:'SimInfo', shady_merchant_sim_info:'SimInfo') -> 'None':
        if sim_info.id in self._sim_wills or shady_merchant_sim_info is None:
            return
        self.create_will(sim_info)
        sim_will = self.get_sim_will(sim_info.id)
        household_will = self.get_household_will(sim_info.household_id)
        if sim_will is not None:
            if self.SHADY_MERCHANT_TUNING.burial_object_def_list:
                burial_obj_def = random.choice(self.SHADY_MERCHANT_TUNING.burial_object_def_list)
                sim_will.set_burial_preference(burial_obj_def.id)
            if self.SHADY_MERCHANT_TUNING.funeral_activities_list:
                funeral_activities = random.sample(self.SHADY_MERCHANT_TUNING.funeral_activities_list, self.SHADY_MERCHANT_TUNING.funeral_activity_max)
                for activity in funeral_activities:
                    sim_will.set_funeral_activity_preference(activity.guid64)
            if self.SHADY_MERCHANT_TUNING.will_note_text:
                sim_will.set_note(self.SHADY_MERCHANT_TUNING.will_note_text)
        if household_will is not None:
            household_will.clear_simoleon_distributions()
            blacklist_sim_ids = {sim_info.id for sim_info in sim_info.household}
            blacklist_sim_ids.add(shady_merchant_sim_info.id)
            highest_rel_sim_id = sim_info.relationship_tracker.get_highest_rel_score_sim(blacklist_sim_ids=blacklist_sim_ids)
            highest_rel_sim_info = None
            if highest_rel_sim_id:
                highest_rel_sim_info = services.sim_info_manager().get(highest_rel_sim_id)
            if self.SHADY_MERCHANT_TUNING.shady_merchant_simoleon_cut:
                household_will.set_simoleon_distribution(shady_merchant_sim_info.household_id, self.SHADY_MERCHANT_TUNING.shady_merchant_simoleon_cut)
                if highest_rel_sim_info is not None:
                    household_will.set_simoleon_distribution(highest_rel_sim_info.household_id, 1 - self.SHADY_MERCHANT_TUNING.shady_merchant_simoleon_cut)
            if highest_rel_sim_info is not None:
                for hh_sim_info in sim_info.household.sim_info_gen():
                    if hh_sim_info != sim_info and not hh_sim_info.can_live_alone:
                        household_will.set_dependent_distribution(hh_sim_info.id, highest_rel_sim_info.household_id)

    def remove_heirloom_from_will(self, object_id:'int') -> 'None':
        for sim_will in self._sim_wills.values():
            if sim_will.is_finalized():
                pass
            elif object_id in sim_will.get_heirloom_distributions():
                sim_will.remove_heirloom(object_id)
                return

    def save(self, save_slot_data:'SaveGameData'=None, **__) -> 'None':
        if not hasattr(GameplaySaveData_pb2, 'PersistableWillService'):
            return
        will_service_proto = GameplaySaveData_pb2.PersistableWillService()
        for sim_will in self._sim_wills.values():
            with ProtocolBufferRollback(will_service_proto.sim_wills) as sim_wills_msg:
                sim_wills_msg.MergeFrom(sim_will.get_persistable_will_data_proto())
        for household_will in self._household_wills.values():
            with ProtocolBufferRollback(will_service_proto.household_wills) as hh_wills_msg:
                hh_wills_msg.MergeFrom(household_will.get_persistable_will_data_proto())
        save_slot_data.gameplay_data.will_service = will_service_proto

    def load(self, **__) -> 'None':
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if protocol_buffer_utils.has_field(save_slot_data_msg.gameplay_data, 'will_service'):
            will_data = save_slot_data_msg.gameplay_data.will_service
            for sim_will_data in will_data.sim_wills:
                sim_id = sim_will_data.sim_id
                sim_will = SimWill(sim_id)
                sim_will.load_from_persistable_will_data_proto(sim_will_data)
                self._sim_wills[sim_id] = sim_will
            for hh_will_data in will_data.household_wills:
                household_id = hh_will_data.household_id
                household_will = HouseholdWill(household_id)
                household_will.load_from_persistable_will_data_proto(hh_will_data)
                self._household_wills[household_id] = household_will
