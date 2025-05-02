from __future__ import annotationsimport dataclassesfrom dataclasses import dataclassfrom distributor.shared_messages import IconInfoDatafrom event_testing.test_events import TestEventfrom indexed_manager import CallbackTypesfrom objects.components.types import STORED_SIM_INFO_COMPONENT, BRANDING_ICON_COMPONENTfrom sims.sim_info import SimInfofrom tag import Tagfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from interactions.utils.loot import LootActionsimport sims4from default_property_stream_reader import DefaultPropertyStreamReaderfrom event_testing.resolver import SingleActorAndObjectResolver, SingleSimResolverfrom objects.game_object import GameObjectfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableInterval, TunableSimMinute, TunableTuple, TunableList, TunableReference, HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableSet, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionimport servicesfrom ui.ui_dialog_notification import UiDialogNotificationCUSTOMER_SITUATIONS_TOKEN = 'customer_situation_ids'SITUATION_ALARM = 'situation_alarm'SALES_TOKEN = 'yard_sale_sales'INITIATING_SELLING_PLATFORM_ID = 'initiating_sellling_platform_id'
class ManageCustomersState(CommonSituationState):
    FACTORY_TUNABLES = {'time_between_customer_checks': TunableSimMinute(description='\n            Time in Sim minutes between situation checks to see if we need to add\n            more Sims to be customers.\n            ', default=10)}

    def __init__(self, *args, time_between_customer_checks=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.time_between_customer_checks = time_between_customer_checks

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.number_of_situations = self.owner.number_of_expected_customers.random_int()
        self._create_or_load_alarm(SITUATION_ALARM, self.time_between_customer_checks, lambda _: self._check_customers(), repeating=True, should_persist=False, reader=reader)

    def _check_customers(self):
        customer_situations = self.owner.get_customer_situations()
        if len(customer_situations) < self.number_of_situations:
            num_to_create = self.number_of_situations - len(customer_situations)
            num_to_create = min(num_to_create, 2)
            for _ in range(num_to_create):
                self.owner.create_customer_situation()
