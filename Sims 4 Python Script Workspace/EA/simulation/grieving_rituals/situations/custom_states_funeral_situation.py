from __future__ import annotationsfrom sims.ghost import Ghostfrom sims.outfits.outfit_enums import OutfitCategoryfrom situations.situation_zone_director_mixin import SituationZoneDirectorMixinfrom tag import Tagfrom typing import TYPE_CHECKINGfrom venues.venue_constants import ZoneDirectorRequestTypeif TYPE_CHECKING:
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from situations.situation_guest_list import SituationGuestList
    from situations.situation_job import SituationJob
    from typing import Listfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom sims4.tuning.tunable import TunableMapping, TunableReference, TunableEnumWithFilter, TunablePackSafeReference, TunableEnumEntryimport randomimport servicesimport sims4from situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.custom_states.custom_states_situation import CustomStatesSituationfrom situations.situation_guest_list import SituationGuestInfologger = sims4.log.Logger('Funeral Situations', default_owner='cparrish')
class CustomStateFuneralSituation(SituationZoneDirectorMixin, CustomStatesSituation):
    INSTANCE_TUNABLES = {'departed_job': TunableReference(description='\n            The Situation Job used by the departed sim.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), class_restrictions=('SituationJob',)), 'will_preference_completeness_map': TunableMapping(description="\n            A map of Situation Activity to the Buff that was rewarded when\n            the related goal was completed. Used to measure adherence to\n            the deceased's will.\n            ", key_name='activity', key_type=TunableReference(description='\n                An available activity for this Situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION), class_restrictions=('SituationActivity',), pack_safe=True), value_name='completed_buff', value_type=TunablePackSafeReference(description="\n                The buff awarded by the activity's SituationGoal.\n                ", manager=services.get_instance_manager(sims4.resources.Types.BUFF), class_restrictions=('Buff',))), 'will_preference_success_loot': TunableReference(description='\n            Apply a set of loot actions to the Host sim for successfully completing all\n            Funeral Preferences of the deceased.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), allow_none=True, pack_safe=True), 'will_preference_failure_loot': TunableReference(description='\n            Apply a set of loot actions to the Host sim for failing to complete all\n            Funeral Preferences of the deceased.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), allow_none=True, pack_safe=True), 'funeral_activities_buff_tag': TunableEnumWithFilter(description='\n            The tag associated with all buffs awarded by funeral activities.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=('buff',)), 'preferred_outfit_category': TunableEnumEntry(description="\n            If a sim's outfit in the tuned category complies with one of the tags in the \n            outfit extra tag set, then use that existing outfit instead of \n            generating a new one. \n            ", tunable_type=OutfitCategory, default=OutfitCategory.SITUATION)}

    def start_situation(self) -> 'None':
        super().start_situation()
        venue_service = services.venue_service()
        active_zone_director = venue_service.get_zone_director()
        if active_zone_director and active_zone_director.guid64 != self._zone_director.guid64:
            venue_service.change_zone_director(self._zone_director(), True)

    def _on_set_sim_role_state(self, sim:'Sim', job_type:'SituationJob', *args, **kwargs) -> 'None':
        super()._on_set_sim_role_state(sim, job_type, *args, **kwargs)
        if sim.sim_info is self.guest_list.host_sim_info:
            deceased_guest_infos = self._guest_list.get_guest_infos_for_job(self.departed_job)
            if len(deceased_guest_infos) > 0:
                deceased_sim_info = services.sim_info_manager().get(deceased_guest_infos[0].sim_id)
                if deceased_sim_info is not None:
                    self._ensure_urnstone_on_lot_or_in_host_inventory(deceased_sim_info, sim)

    def _ensure_urnstone_on_lot_or_in_host_inventory(self, deceased_sim_info:'SimInfo', host_sim:'Sim') -> 'None':
        original_urnstone_id = deceased_sim_info.death_tracker.death_object_id
        active_lot = services.active_lot()
        if original_urnstone_id:
            urnstone = services.object_manager().get(original_urnstone_id)
            if urnstone and active_lot.is_position_on_lot(urnstone.position):
                return
            urnstone = services.inventory_manager().get(original_urnstone_id)
            if urnstone:
                inventory_owner = urnstone.inventoryitem_component.inventory_owner
                if inventory_owner.is_sim and inventory_owner != host_sim:
                    owning_inventory = urnstone.inventoryitem_component.inventory_owner.inventory_component
                    owning_inventory.try_remove_object_by_id(urnstone.id)
                    host_sim.inventory_component.system_add_object(urnstone, compact=False)
                    return
                if active_lot.is_position_on_lot(inventory_owner.position):
                    return
        else:
            urnstone = Ghost.get_urnstone_for_sim_id(deceased_sim_info.sim_id, check_sim_inventories=True)
            if urnstone and active_lot.is_position_on_lot(urnstone.position):
                return
        resolver = SingleSimResolver(deceased_sim_info)
        urnstone = Ghost.create_urnstone(resolver)
        urnstone.update_ownership(host_sim)
        host_sim.inventory_component.system_add_object(urnstone, compact=False)

    def on_remove(self) -> 'None':
        super().on_remove()
        host_sim_info = self._guest_list.host_sim_info
        deceased_guest_infos = self._guest_list.get_guest_infos_for_job(self.departed_job)
        if len(deceased_guest_infos) < 1:
            host_sim_info.remove_buffs_by_tags([self.funeral_activities_buff_tag])
            return
        targeted_deceased = deceased_guest_infos[0]
        sim_will = services.get_will_service().get_sim_will(targeted_deceased.sim_id)
        if targeted_deceased is not None and sim_will is not None:
            situation_activity_manager = services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION)
            resolver = DoubleSimResolver(host_sim_info, targeted_deceased)
            preference_guid64s = sim_will.get_funeral_activity_preferences()
            for activity_guid64 in preference_guid64s:
                activity = situation_activity_manager.get(activity_guid64)
                if activity in self.will_preference_completeness_map:
                    buff = self.will_preference_completeness_map[activity]
                    if not host_sim_info.has_buff(buff):
                        if self.will_preference_failure_loot is not None:
                            self.will_preference_failure_loot.apply_to_resolver(resolver)
                        break
                        logger.error('Activity {} is not tuned in the Will Preference Completeness Map.', activity)
                else:
                    logger.error('Activity {} is not tuned in the Will Preference Completeness Map.', activity)
            if self.will_preference_success_loot is not None:
                self.will_preference_success_loot.apply_to_resolver(resolver)
        host_sim_info.remove_buffs_by_tags([self.funeral_activities_buff_tag])
        venue_service = services.venue_service()
        original_zone_director = venue_service.active_venue.create_zone_director_instance()
        venue_service.change_zone_director(original_zone_director, True)

    def get_preferred_outfit_category(self) -> 'OutfitCategory':
        return self.preferred_outfit_category

    @classmethod
    def get_preferred_activities(cls, sim_id:'int', job:'SituationJob') -> 'List[int]':
        if job is cls.departed_job:
            sim_will = services.get_will_service().get_sim_will(sim_id)
            if sim_will is not None:
                return sim_will.get_funeral_activity_preferences()
        return []

    @classmethod
    def get_extended_guest_list(cls, guest_list:'SituationGuestList'=None) -> 'SituationGuestList':
        active_sim_info = services.active_sim_info()
        sim_filter_service = services.sim_filter_service()
        blocklist = [active_sim_info.sim_id]
        hidden_jobs = [job for job in cls._jobs if job.hide_from_creation_ui]
        for job_type in hidden_jobs:
            num_to_auto_fill = job_type.get_auto_invite() - len(guest_list.get_guest_infos_for_job(job_type))
            if num_to_auto_fill < 1:
                pass
            else:
                filter_result = sim_filter_service.submit_matching_filter(sim_filter=job_type.filter, requesting_sim_info=active_sim_info, allow_yielding=False, allow_instanced_sims=True, blacklist_sim_ids=blocklist, gsi_source_fn=cls.get_sim_filter_gsi_name)
                if not filter_result:
                    logger.error('Failed to find/create any sims for {} job in {}.', job_type, cls)
                else:
                    for _ in range(num_to_auto_fill):
                        picked_sim = random.choice(filter_result)
                        blocklist.append(picked_sim.sim_info.sim_id)
                        guest_info = SituationGuestInfo(picked_sim.sim_info.sim_id, job_type, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True)
                        guest_list.add_guest_info(guest_info)
        return guest_list

    @classmethod
    def _get_zone_director_request_type(cls) -> 'ZoneDirectorRequestType':
        return ZoneDirectorRequestType.SOCIAL_EVENT
