from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from objects.game_object import GameObjectimport build_buyimport servicesimport sims4.logfrom autonomy.autonomy_modifier import OffLotAutonomyRulesfrom dynamic_areas.dynamic_area_enums import DynamicAreaTypefrom indexed_manager import CallbackTypesfrom routing.portals.portal_tuning import PortalFlagsfrom server.live_drag_tuning import LiveDragLocationfrom sims4.callback_utils import CallableListfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableList, TunableEnumFlags, TunableEnumEntry, TunableTuple, TunableMappingfrom tag import Taglogger = sims4.log.Logger('Dynamic Area', default_owner='pgoujet')
class DynamicArea:

    def __init__(self):
        self.area_type = DynamicAreaType.INVALID
        self.blocks = []
        self.objects = set()

class DynamicAreaService(Service):
    PORTALS_EXCLUSIONS = TunableList(description='\n        The list of navigation portal restriction for each dynamic area type\n        ', tunable=TunableTuple(area_type=TunableEnumEntry(tunable_type=DynamicAreaType, default=DynamicAreaType.INVALID), portal_exclusion_flag=TunableEnumFlags(description='\n                Define the exclusion flag for navigation portals\n                ', enum_type=PortalFlags, allow_no_flags=True)))
    PORTALS_TRANSITION_OVERRIDE = TunableList(description='\n        The list of transition between specific area type that will override Portal Exclusion\n        ', tunable=TunableTuple(entry_area_type=TunableEnumEntry(tunable_type=DynamicAreaType, default=DynamicAreaType.INVALID), exit_area_type=TunableEnumEntry(tunable_type=DynamicAreaType, default=DynamicAreaType.INVALID), portal_exclusion_flag=TunableEnumFlags(description='\n                Define the exclusion flag for navigation portals for transition from entry to exit\n                ', enum_type=PortalFlags, allow_no_flags=True)))
    DYNAMIC_AREA_AUTONOMY_RESTRICTION = TunableList(description='\n        Define the restrictions to use an object given an autonomy type and the dynamic area type\n        ', tunable=TunableTuple(autonomy_rule=TunableEnumEntry(description='\n                Define the autonomy rule that will restrict object usage\n                ', tunable_type=OffLotAutonomyRules, default=OffLotAutonomyRules.DEFAULT), area_types=TunableList(description='\n                Define the dynamic area types that will affect the object usage\n                ', tunable=TunableEnumEntry(tunable_type=DynamicAreaType, default=DynamicAreaType.INVALID))))
    AREA_TYPE_OBJECT_TAG = TunableMapping(description='\n        A mapping that define which tag objects will receive when they belong to a specific area type\n        ', key_name='Area Type', key_type=TunableEnumEntry(tunable_type=DynamicAreaType, default=DynamicAreaType.INVALID, invalid_enums=(DynamicAreaType.INVALID,)), value_name='Tag', value_type=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID, pack_safe=True))
    EXTERIOR_AREA_TYPE = TunableEnumEntry(description='\n        Define the area type that should be set for exterior\n        ', tunable_type=DynamicAreaType, default=DynamicAreaType.INVALID)

    def __init__(self):
        self._areas = None
        self._update_object_callback = CallableList()
        self._is_registered_to_callbacks = False
        self._is_in_build_buy = False
        build_buy.register_build_buy_enter_callback(self._on_build_buy_enter)
        build_buy.register_build_buy_exit_callback(self._on_build_buy_exit)

    def on_zone_unload(self):
        build_buy.unregister_build_buy_enter_callback(self._on_build_buy_enter)
        build_buy.unregister_build_buy_exit_callback(self._on_build_buy_exit)
        if self._is_registered_to_callbacks:
            self.unregister_to_callbacks()

    def register_to_callbacks(self):
        if self._is_registered_to_callbacks:
            logger.error('Trying to registered to the callbacks but is already register')
            return
        services.object_manager().register_callback(CallbackTypes.ON_OBJECT_ADD, self.add_object)
        services.object_manager().register_callback(CallbackTypes.ON_OBJECT_REMOVE, self.remove_object)
        client = services.client_manager().get_first_client()
        if client is not None:
            client.register_end_live_drag_object_callback(self.on_object_dragged)
        self._is_registered_to_callbacks = True

    def unregister_to_callbacks(self):
        if not self._is_registered_to_callbacks:
            logger.error('Trying to Unregistered to the callbacks but is already register')
            return
        services.object_manager().unregister_callback(CallbackTypes.ON_OBJECT_ADD, self.add_object)
        services.object_manager().unregister_callback(CallbackTypes.ON_OBJECT_REMOVE, self.remove_object)
        client = services.client_manager().get_first_client()
        if client is not None:
            client.unregister_end_live_drag_object_callback(self.on_object_dragged)
        self._is_registered_to_callbacks = False

    def _on_build_buy_enter(self):
        self._is_in_build_buy = True

    def _on_build_buy_exit(self):
        self._is_in_build_buy = False

    def register_update_object_callback(self, callback):
        if callback not in self._update_object_callback:
            self._update_object_callback.append(callback)

    def unregister_update_object_callback(self, callback):
        if callback in self._update_object_callback:
            self._update_object_callback.remove(callback)

    def clear_all_areas(self):
        if self._is_registered_to_callbacks:
            self.unregister_to_callbacks()
        object_manager = services.object_manager()
        if self._areas is not None:
            for area in self._areas:
                for obj_id in area.objects:
                    obj = object_manager.get(obj_id)
                    if obj is not None:
                        tag_to_remove = self.AREA_TYPE_OBJECT_TAG.get(area.area_type)
                        if tag_to_remove is not None and obj.has_tag(tag_to_remove):
                            obj.remove_dynamic_tags({tag_to_remove})
                        obj.unregister_on_location_changed(self._update_object)
        self._areas = None

    def create_area(self, area_type:'DynamicAreaType', blocks:'[int]'):
        new_area = DynamicArea()
        new_area.area_type = area_type
        new_area.blocks = blocks
        if self._areas is None:
            self._areas = []
            self.register_to_callbacks()
        self._areas.append(new_area)

    def get_dynamic_area(self, area_type:'DynamicAreaType') -> 'DynamicArea':
        if self._areas is None:
            return
        for area in self._areas:
            if area.area_type == area_type:
                return area

    def get_area_type_for_block(self, block_id:'int') -> 'DynamicAreaType':
        if self._areas is None:
            return DynamicAreaType.INVALID
        for area in self._areas:
            if block_id in area.blocks:
                return area.area_type
        return DynamicAreaType.INVALID

    def get_area_type_for_object(self, object_id:'int') -> 'DynamicAreaType':
        if self._areas is None:
            return DynamicAreaType.INVALID
        for area in self._areas:
            if object_id in area.objects:
                return area.area_type
        return DynamicAreaType.INVALID

    def is_object_relevant(self, obj:'GameObject') -> 'bool':
        if self._areas is None:
            return False
        if obj.interactable:
            if obj.is_on_active_lot(tolerance=0):
                return True
            else:
                parent = obj.parent
                if parent is not None and parent.is_on_active_lot(tolerance=0):
                    return True
        return False

    def add_object(self, obj:'GameObject'):
        if self.is_object_relevant(obj):
            obj_block_id = build_buy.get_block_id(services.current_zone_id(), obj.position, obj.level)
            area_type = self.get_area_type_for_block(obj_block_id)
            if self._add_object_to_area_type(obj, DynamicAreaType(area_type)):
                obj.register_on_location_changed(self._update_object)
                self._update_object_callback(obj.id)

    def remove_object(self, obj:'GameObject'):
        if obj is None:
            return
        if self.is_object_relevant(obj):
            for area in self._areas:
                if self._remove_from_area(obj, area):
                    obj.unregister_on_location_changed(self._update_object)
                    return

    def on_object_dragged(self, obj:'GameObject', dragged_from:'LiveDragLocation', dragged_to:'LiveDragLocation'):
        if dragged_from == LiveDragLocation.GAMEPLAY_UI and dragged_to == LiveDragLocation.BUILD_BUY:
            self.add_object(obj)
        elif dragged_from == LiveDragLocation.BUILD_BUY and dragged_to == LiveDragLocation.GAMEPLAY_UI:
            self.remove_object(obj)

    def _remove_from_area(self, obj:'GameObject', area:'DynamicArea') -> 'bool':
        if obj.id in area.objects:
            tag_to_remove = self.AREA_TYPE_OBJECT_TAG.get(area.area_type)
            if tag_to_remove is not None:
                obj.remove_dynamic_tags({tag_to_remove})
            area.objects.remove(obj.id)
            self._update_object_callback(obj.id)
            return True
        return False

    def _update_object(self, obj:'GameObject', old_pos, new_pos):
        if self._is_in_build_buy:
            return
        old_block_id = 0
        new_block_id = 0
        if old_pos.world_routing_surface is not None:
            old_block_id = build_buy.get_block_id(services.current_zone_id(), old_pos.world_transform.translation, old_pos.level)
        if new_pos.world_routing_surface is not None:
            new_block_id = build_buy.get_block_id(services.current_zone_id(), new_pos.world_transform.translation, new_pos.level)
        if old_block_id != new_block_id:
            old_area_type = self.get_area_type_for_block(old_block_id)
            new_area_type = self.get_area_type_for_block(new_block_id)
            if old_area_type != new_area_type:
                has_been_removed = False
                has_been_added = False
                old_area = self.get_dynamic_area(old_area_type)
                if old_area is not None:
                    if self._remove_from_area(obj, old_area):
                        has_been_removed = True
                    else:
                        for area in self._areas:
                            if self._remove_from_area(obj, area):
                                has_been_removed = True
                                logger.error('Object was remove from area {} but was expected to be in area {} in block {}', area.area_type, old_area.area_type, old_block_id)
                                break
                if self._add_object_to_area_type(obj, new_area_type):
                    has_been_added = True
                self._update_object_callback(obj.id)
                if has_been_removed and not has_been_added:
                    obj.unregister_on_location_changed(self._update_object)

    def _add_object_to_area_type(self, obj:'GameObject', area_type:'DynamicAreaType') -> 'bool':
        if self._areas is None:
            return False
        for area in self._areas:
            if area.area_type == area_type:
                area.objects.add(obj.id)
                tag_to_add = self.AREA_TYPE_OBJECT_TAG.get(area_type)
                if tag_to_add is not None:
                    obj.append_tags({tag_to_add})
                return True
        return False

    def can_object_be_used_by_autonomy(self, obj:'GameObject', autonomy_type:'OffLotAutonomyRules') -> 'bool':
        area_type = self._get_sim_area_type(obj)
        if area_type == DynamicAreaType.INVALID:
            area_type = services.dynamic_area_service().get_area_type_for_object(obj.id)
        if area_type != DynamicAreaType.INVALID:
            for autonomy_restriction in self.DYNAMIC_AREA_AUTONOMY_RESTRICTION:
                if autonomy_restriction.autonomy_rule == autonomy_type and area_type in autonomy_restriction.area_types:
                    return False
            return True
        return False

    def _get_sim_area_type(self, obj:'GameObject') -> 'DynamicAreaType':
        if obj.is_sim:
            obj_block_id = build_buy.get_block_id(services.current_zone_id(), obj.position, obj.level)
            return self.get_area_type_for_block(obj_block_id)
        return DynamicAreaType.INVALID

    def update_all_objects(self):
        if self._areas is None:
            return
        for obj in list(services.object_manager(services.current_zone_id()).objects):
            self.add_object(obj)

    def get_portal_flags_for_areas(self, entry_area:'DynamicAreaType', exit_area:'DynamicAreaType') -> 'PortalFlags':
        entry_flag = 0
        exit_flag = 0
        is_entry_override = False
        is_exit_override = False
        for transition_override in self.PORTALS_TRANSITION_OVERRIDE:
            if transition_override.entry_area_type == entry_area and transition_override.exit_area_type == exit_area:
                entry_flag |= transition_override.portal_exclusion_flag
                is_entry_override = True
            elif transition_override.entry_area_type == exit_area and transition_override.exit_area_type == entry_area:
                exit_flag |= transition_override.portal_exclusion_flag
                is_exit_override = True
        for portal_exclusion in self.PORTALS_EXCLUSIONS:
            check_type = portal_exclusion.area_type
            if not is_exit_override:
                exit_flag |= portal_exclusion.portal_exclusion_flag
            if check_type == entry_area and check_type == exit_area and not is_entry_override:
                entry_flag |= portal_exclusion.portal_exclusion_flag
        return (entry_flag, exit_flag)

    def cheat_force_type_for_block(self, block_id:'int', area_type:'DynamicAreaType'):
        current_block_type = self.get_area_type_for_block(block_id)
        if current_block_type is not DynamicAreaType.INVALID:
            current_area = self.get_dynamic_area(current_block_type)
            if current_area is not None:
                current_area.blocks.remove(block_id)
        new_area = self.get_dynamic_area(area_type)
        if new_area is not None:
            new_area.blocks.append(block_id)
            return
        new_area = DynamicArea()
        new_area.area_type = area_type
        new_area.blocks.append(block_id)
        if self._areas is None:
            self._areas = []
        self._areas.append(new_area)
