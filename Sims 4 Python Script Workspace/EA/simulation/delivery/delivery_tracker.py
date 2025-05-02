from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from crafting.recipe import Recipe
    from delivery.scheduled_delivery_loot_op import ScheduledDeliveryLoot
    from interactions.utils.loot import LootActions
    from sims.sim_info import SimInfofrom collections import namedtuplefrom crafting.crafting_interactions import create_craftablefrom date_and_time import DateAndTime, TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom households.household_tracker import HouseholdTrackerfrom interactions import ParticipantTypefrom interactions.utils import LootTypefrom objects import HiddenReasonFlagfrom sims4.resources import Typesimport alarmsimport servicesimport sims4.logfrom sims4.tuning.tunable import OptionalTunablefrom tunable_time import TunableTimeSpanfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippet_Delivery = namedtuple('_Delivery', ('sim_id', 'tuning_guid', 'expected_arrival_time', 'sender_sim_id'))logger = sims4.log.Logger('DeliveryTracker', default_owner='jdimailig')
class _DeliveryAlarmHandler:

    def __init__(self, tracker, delivery):
        self._tracker = tracker
        self._delivery = delivery

    def __call__(self, timeline):
        self._tracker.try_do_delivery(self._delivery, from_alarm=True)

class DeliveryTracker(HouseholdTracker):
    RECIPE_AT_HOME_DELIVERY_NOTIFICATION = OptionalTunable(description='\n            The notification that will be displayed when the Sim is at\n            home when the object(s) would be delivered. The object(s)\n            will end up in hidden inventory waiting to be delivered by\n            the mailman.\n            ', tunable=TunableUiDialogNotificationSnippet())
    RECIPE_AWAY_DELIVERY_NOTIFICATION = OptionalTunable(description='\n            If enabled, a notification will be displayed when the Sim is not\n            currently home when the object(s) would be delivered.\n            The object will be in the mailbox when they arrive back at their\n            home lot.\n            ', tunable=TunableUiDialogNotificationSnippet())
    RECIPE_DELIVERY_TIME_SPAN = TunableTimeSpan(description='\n        The amount of time it takes to deliver a craftable when ordered from a Recipe.\n        ', default_days=1)

    def __init__(self, household):
        self._household = household
        self._expected_deliveries = {}
        self._sims_spawned = False

    def request_delivery(self, delivery_tuning_guid:'int', sim_id:'int'=None, time_span_from_now:'TimeSpan'=None, sender_sim_id:'int'=None) -> 'None':
        if sim_id is not None and not self._household.sim_in_household(sim_id):
            logger.warn('Sim {} not in household {}, {} will not be delivered', sim_id, self._household, delivery_tuning_guid)
            return
        if time_span_from_now is None:
            recipe_manager = services.get_instance_manager(Types.RECIPE)
            delivery_recipe = recipe_manager.get(delivery_tuning_guid, None)
            if delivery_recipe is not None:
                time_span_from_now = DeliveryTracker.RECIPE_DELIVERY_TIME_SPAN()
        expected_arrival_time = services.time_service().sim_now + time_span_from_now
        delivery = _Delivery(sim_id, delivery_tuning_guid, expected_arrival_time, sender_sim_id)
        self._expected_deliveries[delivery] = alarms.add_alarm(self, time_span_from_now, _DeliveryAlarmHandler(self, delivery), cross_zone=True)

    def try_do_delivery(self, delivery:'_Delivery', from_alarm:'bool'=False) -> 'None':
        if delivery.sim_id is None:
            sim_info = None
        else:
            sim_info = services.sim_info_manager().get(delivery.sim_id)
            if sim_info is None:
                logger.error('Could not perform delivery, Sim {} not found.', delivery.sim_id)
                del self._expected_deliveries[delivery]
                return
        loot_tuning_manager = services.get_instance_manager(Types.ACTION)
        delivery_tuning = loot_tuning_manager.get(delivery.tuning_guid)
        if delivery_tuning is not None:
            if delivery_tuning.loot_type == LootType.SCHEDULED_DELIVERY:
                self._try_do_delivery_loot(delivery, delivery_tuning, sim_info=sim_info, from_alarm=from_alarm)
                return
            if delivery_tuning.loot_type == LootType.ACTIONS:
                self._try_do_delivery_loot_actions(delivery, delivery_tuning, sim_info=sim_info)
                return
        recipe_manager = services.get_instance_manager(Types.RECIPE)
        delivery_recipe = recipe_manager.get(delivery.tuning_guid, None)
        if delivery_recipe is not None:
            self._try_do_delivery_recipe(delivery, delivery_recipe, sim_info, from_alarm=from_alarm)
            return
        logger.error('Could not perform delivery, the tuning_guid {} is not a delivery loot or recipe.', delivery.tuning_guid)
        del self._expected_deliveries[delivery]

    def _try_do_delivery_loot_actions(self, delivery:'_Delivery', delivery_tuning:'LootActions', sim_info:'SimInfo'=None) -> 'None':
        if delivery.sim_id is not None:
            sim_info = services.sim_info_manager().get(delivery.sim_id)
        if sim_info is None and sim_info is not None and sim_info.is_instanced(allow_hidden_flags=HiddenReasonFlag.RABBIT_HOLE):
            if self._household.home_zone_id == services.current_zone_id():
                resolver = SingleSimResolver(sim_info)
                delivery_tuning.apply_to_resolver(resolver)
                del self._expected_deliveries[delivery]
        elif delivery.sender_sim_id is not None:
            sim_info = services.active_sim_info()
            resolver = SingleSimResolver(sim_info)
            sender_sim_info = services.sim_info_manager().get(delivery.sender_sim_id)
            resolver.set_additional_participant(ParticipantType.StoredSim, (sender_sim_info,))
            delivery_tuning.apply_to_resolver(resolver)
            del self._expected_deliveries[delivery]

    def _try_do_delivery_loot(self, delivery:'_Delivery', delivery_tuning:'ScheduledDeliveryLoot', sim_info:'SimInfo'=None, from_alarm:'bool'=False) -> 'None':
        if delivery.sim_id is None:
            sim_info = services.active_sim_info()
        resolver = SingleSimResolver(sim_info)
        if sim_info is None and delivery.sender_sim_id is not None:
            sender_sim_info = services.sim_info_manager().get(delivery.sender_sim_id)
            resolver.set_additional_participant(ParticipantType.StoredSim, (sender_sim_info,))
        if self._household == services.active_household() and self._household.home_zone_id == services.current_zone_id():
            delivery_tuning.objects_to_deliver.apply_to_resolver(resolver)
            del self._expected_deliveries[delivery]
            at_home_notification_tuning = delivery_tuning.at_home_notification
            if at_home_notification_tuning is not None:
                at_home_notification = at_home_notification_tuning(sim_info, resolver=resolver)
                at_home_notification.show_dialog()
        elif from_alarm:
            not_home_notification_tuning = delivery_tuning.not_home_notification
            if not_home_notification_tuning is not None:
                not_home_notification = not_home_notification_tuning(sim_info, resolver=resolver)
                not_home_notification.show_dialog()

    def _try_do_delivery_recipe(self, delivery, delivery_recipe, sim_info, from_alarm:'bool'=False):
        resolver = SingleSimResolver(sim_info)
        if self._household.home_zone_id == services.current_zone_id():
            craftable = create_craftable(delivery_recipe, None)
            current_zone = services.current_zone()
            if current_zone is not None:
                lot_hidden_inventory = current_zone.lot.get_hidden_inventory()
                if lot_hidden_inventory is not None and not lot_hidden_inventory.player_try_add_object(craftable):
                    return
            if DeliveryTracker.RECIPE_AT_HOME_DELIVERY_NOTIFICATION is not None:
                notification = DeliveryTracker.RECIPE_AT_HOME_DELIVERY_NOTIFICATION(sim_info, resolver)
                notification.show_dialog()
            del self._expected_deliveries[delivery]
        elif from_alarm and DeliveryTracker.RECIPE_AWAY_DELIVERY_NOTIFICATION is not None:
            notification = DeliveryTracker.RECIPE_AWAY_DELIVERY_NOTIFICATION(sim_info, resolver)
            notification.show_dialog()

    def on_all_sims_spawned(self) -> 'None':
        self._try_deliver_past_due()

    def on_active_sim_set(self) -> 'None':
        self._try_deliver_past_due()

    def _try_deliver_past_due(self) -> 'None':
        if self._household.home_zone_id != services.current_zone_id():
            return
        sim_now = services.time_service().sim_now
        for delivery in tuple(self._expected_deliveries):
            if sim_now < delivery.expected_arrival_time:
                pass
            else:
                self.try_do_delivery(delivery)

    def _deliver_loot_to_mailbox(self, delivery:'_Delivery', delivery_tuning:'ScheduledDeliveryLoot') -> 'None':
        if delivery_tuning is None:
            return
        if delivery_tuning.loot_type != LootType.SCHEDULED_DELIVERY:
            logger.error('Could not perform delivery for {}, not a delivery loot.', delivery_tuning)
            return
        sim_info = None
        if delivery.sim_id is not None:
            sim_info = services.sim_info_manager().get(delivery.sim_id)
        elif self._household == services.active_household():
            sim_info = services.active_sim_info()
        if sim_info is None:
            logger.error('Could not perform delivery for {}, Sim {} not found.', delivery_tuning, delivery.sim_id)
            return
        resolver = SingleSimResolver(sim_info)
        if delivery.sender_sim_id is not None:
            sender_sim_info = services.sim_info_manager().get(delivery.sender_sim_id)
            resolver.set_additional_participant(ParticipantType.StoredSim, (sender_sim_info,))
        delivery_tuning.objects_to_deliver.apply_with_placement_override(sim_info, resolver, self._place_object_in_mailbox)
        del self._expected_deliveries[delivery]

    def _deliver_recipe_to_mailbox(self, delivery:'_Delivery', delivery_recipe:'Recipe') -> 'None':
        sim_info = None
        if delivery.sim_id is not None:
            sim_info = services.sim_info_manager().get(delivery.sim_id)
        elif self._household == services.active_household():
            sim_info = services.active_sim_info()
        if sim_info is None:
            logger.error('Could not perform delivery for {}, Sim {} not found.', delivery_recipe, delivery.sim_id)
            return
        craftable = create_craftable(delivery_recipe, None)
        self._place_object_in_mailbox(sim_info, craftable)
        del self._expected_deliveries[delivery]

    def _place_object_in_mailbox(self, subject_to_apply, created_object):
        sim_household = subject_to_apply.household
        if sim_household is not None:
            zone = services.get_zone(sim_household.home_zone_id)
            if zone is not None:
                mailbox_inventory = zone.lot.get_mailbox_inventory(sim_household.id)
                if mailbox_inventory is not None:
                    mailbox_inventory.player_try_add_object(created_object)

    def household_lod_cleanup(self):
        self._expected_deliveries = {}

    def load_data(self, household_proto):
        sim_now = services.time_service().sim_now
        for delivery_data in household_proto.deliveries:
            from_now = DateAndTime(delivery_data.expected_arrival_time) - sim_now
            delivery_sim_id = delivery_data.sim_id if delivery_data.sim_id else None
            if from_now <= TimeSpan.ZERO:
                delivery = _Delivery(delivery_sim_id, delivery_data.delivery_tuning_guid, delivery_data.expected_arrival_time, delivery_data.sender_sim_id)
                self._expected_deliveries[delivery] = None
            else:
                self.request_delivery(delivery_data.delivery_tuning_guid, delivery_sim_id, from_now, delivery_data.sender_sim_id)

    def save_data(self, household_proto):
        for delivery in self._expected_deliveries:
            with ProtocolBufferRollback(household_proto.deliveries) as delivery_data:
                if delivery.sim_id:
                    delivery_data.sim_id = delivery.sim_id
                delivery_data.delivery_tuning_guid = delivery.tuning_guid
                delivery_data.expected_arrival_time = delivery.expected_arrival_time
                if delivery.sender_sim_id:
                    delivery_data.sender_sim_id = delivery.sender_sim_id
