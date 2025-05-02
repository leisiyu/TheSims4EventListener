from __future__ import annotationsimport enumfrom business.business_enums import BusinessTypefrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from relationships.relationship_bit import RelationshipBit
    from relationships.relationship_objects.sim_relationship import SimRelationship
    from sims.sim_info import SimInfofrom protocolbuffers import SimObjectAttributes_pb2 as protocols, FileSerialization_pb2 as serializationfrom buffs.tunable import TunableBuffReferencefrom distributor.ops import GenerateMemorialPhotofrom distributor.system import Distributorfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom interactions.utils.death_enums import DeathTypefrom objects import ALL_HIDDEN_REASONSfrom relationships.relationship_enums import RelationshipDirectionfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims.loan_tuning import LoanTunablesfrom sims4.common import is_available_pack, Packfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableVariant, TunableReference, TunableList, TunableTuple, OptionalTunable, AutoFactoryInit, HasTunableSingletonFactoryfrom sims4.utils import classpropertyfrom ui.ui_dialog import ButtonType, UiDialogResponsefrom ui.ui_dialog_generic import UiDialogfrom ui.ui_dialog_notification import TunableUiDialogNotificationReferenceimport build_buyimport clansimport clubsimport servicesimport sims4.reloadwith sims4.reload.protected(globals()):
    _is_death_enabled = Truelogger = sims4.log.Logger('Death')DEATH_INTERACTION_MARKER_ATTRIBUTE = 'death_interaction'
def toggle_death(enabled=None):
    global _is_death_enabled
    if enabled is None:
        _is_death_enabled = not _is_death_enabled
    else:
        _is_death_enabled = enabled

def is_death_enabled():
    return _is_death_enabled

def get_death_interaction(sim):
    return getattr(sim, DEATH_INTERACTION_MARKER_ATTRIBUTE, None)

class DeathOption(enum.Int):
    PLAYER_GHOST = ButtonType.DIALOG_RESPONSE_CUSTOM_1
    FREEROAMING_GHOST = ButtonType.DIALOG_RESPONSE_CUSTOM_2
    REINCARNATION = ButtonType.DIALOG_RESPONSE_CUSTOM_3

class DeathTracker(SimInfoTracker):
    DEATH_ZONE_ID = 0
    DEATH_TYPE_GHOST_TRAIT_MAP = TunableMapping(description='\n        The ghost trait to be applied to a Sim when they die with a given death\n        type.\n        ', key_type=TunableEnumEntry(description='\n            The death type to map to a ghost trait.\n            ', tunable_type=DeathType, default=DeathType.NONE, pack_safe=True), key_name='Death Type', value_type=TunableReference(description='\n            The ghost trait to apply to a Sim when they die from the specified\n            death type.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_name='Ghost Trait')
    DEATH_BUFFS = TunableList(description='\n        A list of buffs to apply to Sims when another Sim dies. For example, use\n        this tuning to tune a "Death of a Good Friend" buff.\n        ', tunable=TunableTuple(test_set=TunableReference(description="\n                The test that must pass between the dying Sim (TargetSim) and\n                the Sim we're considering (Actor). If this test passes, no\n                further test is executed.\n                ", manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TestSetInstance',), pack_safe=True), buff=TunableBuffReference(description='\n                The buff to apply to the Sim.\n                ', pack_safe=True), notification=OptionalTunable(description='\n                If enabled, an off-lot death generates a notification for the\n                target Sim. This is limited to one per death instance.\n                ', tunable=TunableUiDialogNotificationReference(description='\n                    The notification to show.\n                    ', pack_safe=True))))

    class _RelationshipBitRemap(HasTunableSingletonFactory, AutoFactoryInit):

        class _GenderBasedBit(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'male_bit': TunableReference(description='\n                    Relationship bit to be added if subject is male.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True), 'female_bit': TunableReference(description='\n                    Relationship bit to be added if subject is female.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True)}

            def __call__(self, sim_info:'SimInfo', target_sim_id:'int', relationship:'SimRelationship') -> 'None':
                if sim_info.is_male:
                    relationship.add_relationship_bit(sim_info.sim_id, target_sim_id, self.male_bit, notify_client=False)
                    return
                relationship.add_relationship_bit(sim_info.sim_id, target_sim_id, self.female_bit, notify_client=False)

        class _GenderNeutralBit(HasTunableSingletonFactory, AutoFactoryInit):
            FACTORY_TUNABLES = {'bit': TunableReference(description='\n                    Relationship bit to be added.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True)}

            def __call__(self, sim_info:'SimInfo', target_sim_id:'int', relationship:'SimRelationship') -> 'None':
                relationship.add_relationship_bit(sim_info.sim_id, target_sim_id, self.bit, notify_client=False)

        FACTORY_TUNABLES = {'map': TunableMapping(description='\n                Mapping of relationship bits to be removed or possibly replaced, based on where this map is used.\n                ', key_type=TunableReference(description='\n                    Relationship bit to be removed\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True), key_name='Bit To Remove', value_type=TunableTuple(description='\n                    Changes to make between sims whose relationship has the bit to be removed.\n                    ', replacement_bits=TunableList(description='\n                        Bits to be added, thereby replacing the removed bit.\n                        ', tunable=TunableVariant(description='\n                            The type of test to run.\n                            ', gender_neutral=_GenderNeutralBit.TunableFactory(), gender_based=_GenderBasedBit.TunableFactory(), default='gender_neutral'))), value_name='changes to make')}

        def __call__(self, sim_info:'SimInfo', target_sim_id:'int', relationship:'SimRelationship', bidirectional_bits:'set[RelationshipBit]') -> 'bool':
            sim_id = sim_info.sim_id
            dirty_relationship = False
            for (bit_to_remove, modifications) in self.map.items():
                if relationship.has_bit(sim_id, bit_to_remove):
                    dirty_relationship = True
                    if bit_to_remove.directionality == RelationshipDirection.UNIDIRECTIONAL:
                        relationship.remove_bit(sim_id, target_sim_id, bit_to_remove, notify_client=False)
                    else:
                        bidirectional_bits.add(bit_to_remove)
                    for bit_to_add in modifications.replacement_bits:
                        bit_to_add(sim_info, target_sim_id, relationship)
            return dirty_relationship

    RELATIONSHIP_BASED_FIXUP = TunableTuple(description='\n        Tuning for modifications made between a dying sim and all the sims that sim has a relationship with..\n        ', deceased_to_relation=_RelationshipBitRemap.TunableFactory(description='\n            Mapping of relationship bits to be removed or possibly replaced from the deceased to each relation in the\n            deceaseds relationship\n            '), relation_to_deceased=_RelationshipBitRemap.TunableFactory(description='\n            Mapping of relationship bits to be removed or possibly replaced from each relation the deceased sim\n            has a relationship with to the deceased.\n            '), loots=TunableList(description='\n            A list of loot that will be applied between the relation (actor) and the deceased (target sim).\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True)), non_ghost_fixups=TunableTuple(description="\n            Fixups to apply only if the other sim in the relationship isn't already a ghost.\n            ", deceased_to_relation=_RelationshipBitRemap.TunableFactory(description='\n                Mapping of relationship bits to be removed or possibly replaced from the deceased to each relation in the\n                deceaseds relationship\n                '), relation_to_deceased=_RelationshipBitRemap.TunableFactory(description='\n                Mapping of relationship bits to be removed or possibly replaced from each relation the deceased sim\n                has a relationship with to the deceased.\n                '), loots=TunableList(description='\n                A list of loot that will be applied between the relation (actor) and the deceased (target sim).\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True))))
    IS_DYING_BUFF = TunableReference(description='\n        A reference to the buff a Sim is given when they are dying.\n        ', manager=services.get_instance_manager(sims4.resources.Types.BUFF))
    DEATH_RELATIONSHIP_BIT_FIXUP_LOOT = TunableReference(description='\n        A reference to the loot to apply to a Sim upon death.\n        \n        This is where the relationship bit fixup loots will be tuned. This\n        used to be on the interactions themselves but if the interaction was\n        reset then the bits would stay as they were. If we add more relationship\n        bits we want to clean up on death, the references Loot is the place to \n        do it.\n        \n        DEPRECATED:  Use/Convert to Relationship Based Fixup.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), deprecated=True)
    INVENTORY_OPTIONS_DIALOG = TunableTuple(description='\n        Dialog for inventory options when a sim in the player household dies. \n        ', dialog=UiDialog.TunableFactory(description="\n            Dialog that's shown. \n            "), purge_text=TunableLocalizedStringFactory(description='\n            Text for the purge inventory option.\n            '), purge_tooltip=TunableLocalizedStringFactory(description='\n            Toolitp for the purge inventory option.\n            '), transfer_to_hh_text=TunableLocalizedStringFactory(description='\n            Text for the transfer to hh inventory option.\n            '), transfer_to_hh_tooltip=TunableLocalizedStringFactory(description='\n            Toolitp for the transfer to hh inventory option.\n            '), leave_alone_text=TunableLocalizedStringFactory(description='\n            Text for the leave on ghost inventory option.\n            '), leave_alone_tooltip=TunableLocalizedStringFactory(description='\n            Toolitp for the leave on ghost inventory option.\n            '))

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._death_type = None
        self._death_time = None
        self._death_object_id = 0

    @property
    def death_type(self):
        return self._death_type

    @property
    def death_time(self):
        return self._death_time

    @property
    def is_ghost(self):
        return self._sim_info.trait_tracker.has_any_trait(self.DEATH_TYPE_GHOST_TRAIT_MAP.values())

    def get_ghost_trait(self):
        return self.DEATH_TYPE_GHOST_TRAIT_MAP.get(self._death_type)

    def do_inventory_options_dialog(self, callback:'Callable[[], None]', dialog_override_tuning:'Optional[Any]'=None) -> 'None':
        if self._sim_info.household.is_played_household and services.misc_options_service().automatic_death_inventory_handling_enabled:
            callback()
            return
        sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            if not self._sim_info.inventory_data:
                callback()
                return
        elif sim.inventory_component.get_shelved_object_count() == 0 and next(iter(sim.inventory_component), None) is None:
            callback()
            return

        def _on_dialog_response(responding_dialog):
            if responding_dialog.response == ButtonType.DIALOG_RESPONSE_CUSTOM_3:
                callback()
                return
            if not sim:
                if responding_dialog.response == ButtonType.DIALOG_RESPONSE_CUSTOM_2:
                    for inventory_data in self._sim_info.inventory_data.objects:
                        build_buy.copy_objectdata_to_household_inventory(inventory_data, self._sim_info.household)
                self._sim_info.inventory_data = serialization.ObjectList()
            else:
                if responding_dialog.response == ButtonType.DIALOG_RESPONSE_CUSTOM_2:
                    sim.inventory_component.push_items_to_household_inventory()
                sim.inventory_component.purge_inventory()
            callback()

        resolver = SingleSimResolver(self._sim_info)
        if dialog_override_tuning:
            dialog = dialog_override_tuning.dialog(self._sim_info, resolver)
        else:
            dialog = self.INVENTORY_OPTIONS_DIALOG.dialog(self._sim_info, resolver)
        responses = []
        responses.append(UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_CUSTOM_1, text=self.INVENTORY_OPTIONS_DIALOG.purge_text, tooltip_text=self.INVENTORY_OPTIONS_DIALOG.purge_tooltip))
        if any(sim_info.can_live_alone for sim_info in self._sim_info.household if sim_info is not self._sim_info):
            responses.append(UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_CUSTOM_2, text=self.INVENTORY_OPTIONS_DIALOG.transfer_to_hh_text, tooltip_text=self.INVENTORY_OPTIONS_DIALOG.transfer_to_hh_tooltip))
        if dialog_override_tuning and dialog_override_tuning.allow_leave_items_on_ghost:
            responses.append(UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_CUSTOM_3, text=self.INVENTORY_OPTIONS_DIALOG.leave_alone_text, tooltip_text=self.INVENTORY_OPTIONS_DIALOG.leave_alone_tooltip))
        dialog.set_responses(responses)
        dialog.add_listener(_on_dialog_response)
        dialog.show_dialog(auto_response=ButtonType.DIALOG_RESPONSE_CUSTOM_1)

    def set_death_type(self, death_type:'Optional[DeathType]', is_off_lot_death:'bool'=False, remove_from_household:'bool'=True, set_to_min_lod:'bool'=False, process_inventory:'bool'=True, is_reincarnation:'bool'=False) -> 'None':
        self._sim_info.career_tracker.on_death()
        if set_to_min_lod or self._sim_info.degree_tracker is not None:
            self._sim_info.degree_tracker.on_death()
        if is_off_lot_death or remove_from_household:
            business_service = services.business_service()
            small_business_manager = business_service.get_business_manager_for_sim(self._sim_info.sim_id)
            if small_business_manager is not None:
                small_business_manager.on_death(self._sim_info, show_transfer_dialog=not (is_off_lot_death or is_reincarnation))
        LoanTunables.on_death(self._sim_info)
        if process_inventory:
            self.do_inventory_options_dialog(lambda : self._set_death_type(death_type=death_type, is_off_lot_death=is_off_lot_death, remove_from_household=remove_from_household, set_to_min_lod=set_to_min_lod))
            return
        self._set_death_type(death_type=death_type, is_off_lot_death=is_off_lot_death, remove_from_household=remove_from_household, set_to_min_lod=set_to_min_lod)

    def _set_death_type(self, death_type:'Optional[DeathType]', is_off_lot_death:'bool'=False, remove_from_household:'bool'=True, set_to_min_lod:'bool'=False) -> 'None':
        is_npc = self._sim_info.is_npc
        household = self._sim_info.household
        sim_id = self._sim_info.sim_id
        will_service = services.get_will_service()
        if will_service is not None:
            will_service.finalize_will(self._sim_info)
        if remove_from_household:
            self._sim_info.inject_into_inactive_zone(self.DEATH_ZONE_ID, start_away_actions=False, skip_instanced_check=True, skip_daycare=True)
            household.remove_sim_info(self._sim_info, destroy_if_empty_household=True)
        if is_off_lot_death:
            household.pending_urnstone_ids.append(sim_id)
        if remove_from_household:
            self._sim_info.transfer_to_hidden_household()
            if death_type is not None and household.is_played_household and not set_to_min_lod:
                self._sim_info.household.set_played_household(True)
        clubs.on_sim_killed_or_culled(self._sim_info)
        clans.on_sim_killed_or_culled(self._sim_info)
        if is_available_pack(Pack.EP17):
            self._cache_sim_death_photo()
        if death_type is None:
            return
        relationship_service = services.relationship_service()
        fixups = self.RELATIONSHIP_BASED_FIXUP
        non_ghost_fixups = fixups.non_ghost_fixups
        for relationship in relationship_service.get_all_sim_relationships(sim_id):
            target_sim_info = relationship.get_other_sim_info(sim_id)
            target_sim_id = target_sim_info.sim_id
            resolver = DoubleSimResolver(target_sim_info, self._sim_info)
            for death_data in self.DEATH_BUFFS:
                if not death_data.test_set(resolver):
                    pass
                else:
                    target_sim_info.add_buff_from_op(death_data.buff.buff_type, buff_reason=death_data.buff.buff_reason)
                    if is_npc and not target_sim_info.is_npc:
                        notification = death_data.notification(target_sim_info, resolver=resolver)
                        notification.show_dialog()
                    break
            dirty_relationship = False
            bidirectional_bits = set()
            dirty_relationship |= fixups.deceased_to_relation(self._sim_info, target_sim_id, relationship, bidirectional_bits)
            dirty_relationship |= fixups.relation_to_deceased(target_sim_info, sim_id, relationship, bidirectional_bits)
            for loot in fixups.loots:
                loot.apply_to_resolver(resolver)
            if not target_sim_info.is_ghost:
                dirty_relationship |= non_ghost_fixups.deceased_to_relation(self._sim_info, target_sim_id, relationship, bidirectional_bits)
                dirty_relationship |= non_ghost_fixups.relation_to_deceased(target_sim_info, sim_id, relationship, bidirectional_bits)
                for loot in non_ghost_fixups.loots:
                    loot.apply_to_resolver(resolver)
            for bit_to_remove in bidirectional_bits:
                relationship.remove_bit(sim_id, target_sim_id, bit_to_remove, notify_client=False)
            if dirty_relationship:
                relationship.send_relationship_info()
        ghost_trait = DeathTracker.DEATH_TYPE_GHOST_TRAIT_MAP.get(death_type)
        if ghost_trait is not None:
            self._sim_info.add_trait(ghost_trait)
        traits = list(self._sim_info.trait_tracker.equipped_traits)
        for trait in traits:
            if trait.remove_on_death:
                self._sim_info.remove_trait(trait)
        self._death_type = death_type
        self._death_time = services.time_service().sim_now.absolute_ticks()
        self._sim_info.reset_age_progress()
        self._sim_info.resend_death_type()
        self._handle_remove_rel_bits_on_death()
        services.get_event_manager().process_event(test_events.TestEvent.SimDeathTypeSet, sim_info=self._sim_info)

    def _cache_sim_death_photo(self) -> 'None':
        op = GenerateMemorialPhoto(self._sim_info.sim_id)
        Distributor.instance().add_op_with_no_owner(op)

    def _handle_remove_rel_bits_on_death(self):
        resolver = SingleSimResolver(self._sim_info)
        if self.DEATH_RELATIONSHIP_BIT_FIXUP_LOOT is not None:
            for (loot, _) in self.DEATH_RELATIONSHIP_BIT_FIXUP_LOOT.get_loot_ops_gen():
                result = loot.test_resolver(resolver)
                if result:
                    loot.apply_to_resolver(resolver)

    def clear_death_type(self):
        self._death_type = None
        self._death_time = None
        self._sim_info.resend_death_type()

    @property
    def death_object_id(self) -> 'int':
        return self._death_object_id

    @death_object_id.setter
    def death_object_id(self, urnstone_obj_id:'int') -> 'None':
        self._death_object_id = urnstone_obj_id

    def save(self):
        if self._death_type is not None:
            data = protocols.PersistableDeathTracker()
            data.death_type = self._death_type
            data.death_time = self._death_time
            try:
                data.death_object_id = self._death_object_id
            except:
                return data
            return data

    def load(self, data:'protocols.PersistableDeathTracker', skip_load:'bool') -> 'None':
        try:
            self._death_type = DeathType(data.death_type)
        except:
            self._death_type = DeathType.NONE
        self._death_time = data.death_time
        if hasattr(data, 'death_object_id'):
            self._death_object_id = data.death_object_id

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.MINIMUM
