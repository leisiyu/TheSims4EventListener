from __future__ import annotationsfrom objects.components.stored_object_info_tuning import _ObjectGeneratorFromStoredObjectComponentfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from event_testing.resolver import Resolver
    from typing import *from animation.animation_constants import CreatureTypefrom protocolbuffers import Consts_pb2, UI_pb2, DistributorOps_pb2from protocolbuffers.DistributorOps_pb2 import SetWhimBucksfrom protocolbuffers.InteractionOps_pb2 import TravelSimsToZonefrom clock import ClockSpeedModefrom distributor.ops import BreakThroughMessage, GenericProtocolBufferOpfrom distributor.system import Distributorfrom event_testing.resolver import SingleObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeSingleSimfrom interactions.context import InteractionContext, InteractionSourcefrom interactions.priority import Priorityfrom interactions.utils import LootTypefrom interactions.utils.common import InteractionUtilsfrom interactions.utils.loot_basic_op import BaseLootOperation, BaseTargetedLootOperationfrom objects import HiddenReasonFlagfrom objects.components import typesfrom objects.components.inventory_enums import InventoryTypefrom objects.components.portal_lock_data import LockAllWithGenusException, LockAllWithSimIdExceptionData, LockAllWithSituationJobExceptionData, LockRankedStatisticData, LockCreatureDatafrom objects.components.portal_locking_enums import LockPriority, LockType, ClearLockfrom objects.components.spawner_component_enums import SpawnerTypefrom objects.components.state_references import TunableStateValueReferencefrom objects.gallery_tuning import ContentSourcefrom objects.slot_strategy import SlotStrategyVariantfrom sims.funds import FundsSource, get_funds_for_sourcefrom sims.unlock_tracker import TunableUnlockVariantfrom sims4 import mathfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import Tunable, TunableRange, TunableReference, OptionalTunable, TunableRealSecond, TunableVariant, TunableEnumEntry, TunableList, TunableFactory, HasTunableSingletonFactory, AutoFactoryInit, TunablePackSafeReference, TunableTuple, TunableEnumSetfrom traits.trait_type import TraitTypefrom tunable_multiplier import TunableMultiplierfrom tunable_utils.tested_list import TunableTestedListfrom ui.notebook_tuning import NotebookSubCategoriesfrom ui.ui_dialog import UiDialogOk, CommandArgType, UiDialog, UiDialogResponsefrom ui.ui_dialog_buff_notification import UiDialogBuffNotificationfrom ui.ui_dialog_labeled_icons import UiDialogAspirationProgress, UiDialogIconsfrom ui.ui_dialog_notification import UiDialogNotification, TunableUiDialogNotificationReferencefrom ui.ui_dialog_notification_story_progression_discovery import UIDialogNotificationStoryProgressionDiscoveryfrom ui.ui_dialog_reveal_sequence import UiDialogRevealSequencefrom ui.ui_lifestyles_dialog import UiDialogNpcDisplayimport build_buyimport distributor.systemimport enumimport randomimport servicesimport sims4.logimport sims4.resourcesimport tagimport telemetry_helperimport venues.venue_constantslogger = sims4.log.Logger('LootOperations')FLOAT_TO_PERCENT = 0.01TELEMETRY_GROUP_LOOT_OPS = 'LOOT'TELEMETRY_HOOK_DETECTIVE_CLUE = 'DECL'TELEMETRY_DETECTIVE_CLUE_FOUND = 'clue'loot_op_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_LOOT_OPS)
class BaseGameLootOperation(BaseLootOperation):
    FACTORY_TUNABLES = {'locked_args': {'advertise': False}}

class LifeExtensionLootOp(BaseLootOperation):

    class RestoreDaysFromAgingProgress(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'days_to_restore': TunableRange(tunable_type=int, default=0, minimum=0)}

        def perform(self, subject, *_, **__):
            subject.decrement_age_progress(self.days_to_restore)

    class ResetAgingProgressInCategory(HasTunableSingletonFactory, AutoFactoryInit):

        def perform(self, subject, *_, **__):
            subject.reset_age_progress()

    class AddDaysToAgingProgress(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'days_to_add': TunableRange(tunable_type=int, default=0, minimum=0)}

        def perform(self, subject, *_, **__):
            subject.increment_age_progress(self.days_to_add)

    class FillAgingProgressInCategory(HasTunableSingletonFactory, AutoFactoryInit):

        def perform(self, subject, *_, **__):
            subject.fill_age_progress()

    FACTORY_TUNABLES = {'bonus_days': TunableRange(description="\n            Number of bonus days to be granted to the target's life.\n            ", tunable_type=int, default=1, minimum=0), 'modify_aging_progress': TunableVariant(description='\n            If enabled, this loot will modify aging progress of a sim.\n            ', restore_days_from_aging_progress=RestoreDaysFromAgingProgress.TunableFactory(), reset_aging_progress_in_category=ResetAgingProgressInCategory.TunableFactory(), add_days_to_aging_progress=AddDaysToAgingProgress.TunableFactory(), fill_aging_progress_in_category=FillAgingProgressInCategory.TunableFactory(), locked_args={'disabled': None}, default='disabled')}

    def __init__(self, bonus_days, modify_aging_progress, **kwargs):
        super().__init__(**kwargs)
        self.bonus_days = bonus_days
        self.modify_aging_progress = modify_aging_progress

    @property
    def loot_type(self):
        return LootType.LIFE_EXTENSION

    def _apply_to_subject_and_target(self, subject, target, resolver):
        subject.add_bonus_days(self.bonus_days)
        if self.modify_aging_progress is not None:
            self.modify_aging_progress.perform(subject)

class StateChangeLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'description': '\n            This loot will change the state of the subject.\n            ', 'state_value': TunableStateValueReference(), 'force_update': Tunable(description="\n            If checked, force update the subject's state.\n            ", tunable_type=bool, default=False)}

    @TunableFactory.factory_option
    def subject_participant_type_options(**kwargs):
        return {'subject': TunableVariant(description='\n            The subject of this loot.\n            ', participant=TunableEnumEntry(description='"\n                The participant type for the subject of this loot.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor, invalid_enums=(ParticipantType.Invalid,)), all_objects_with_tag=TunableEnumEntry(description='\n                All objects with this tag.\n                ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,)), from_stored_object_component=_ObjectGeneratorFromStoredObjectComponent.TunableFactory(), default='participant')}

    def __init__(self, state_value, force_update, **kwargs):
        super().__init__(**kwargs)
        self.state_value = state_value
        self.force_update = force_update

    def resolve_participants(self, subject, resolver, filter_tests, resolved_recipient=None):
        if isinstance(subject, _ObjectGeneratorFromStoredObjectComponent):
            stored_objects = subject.get_objects(resolver)
            for obj in stored_objects:
                yield obj
        else:
            yield from super().resolve_participants(subject, resolver, filter_tests, resolved_recipient)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        subject_obj = self._get_object_from_recipient(subject)
        if subject_obj is not None:
            state_value = self.state_value
            subject_obj.set_state(state_value.state, state_value, force_update=self.force_update)

class DialogLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'dialog': TunableVariant(description='\n            Type of dialog to show.\n            ', dialog_icon=UiDialogIcons.TunableFactory(description='\n                Display a dialog that has tunable icons as content.\n                '), notification=UiDialogNotification.TunableFactory(description='\n                This text will display in a notification pop up when completed.\n                '), notification_reference=TunableUiDialogNotificationReference(description='\n                Display a notification from a reference.\n                '), dialog_ok=UiDialogOk.TunableFactory(description='\n                Display a dialog with an okay button.\n                '), aspiration_progress=UiDialogAspirationProgress.TunableFactory(description="\n                Display a dialog that will show the Sim's progress towards one\n                or more aspirations.\n                "), reveal_sequence=UiDialogRevealSequence.TunableFactory(description="\n                Display a dialog that will show the Sim's gig photos in a sequence.\n                "), npc_display=UiDialogNpcDisplay.TunableFactory(description='\n                Display a dialog that will show a list of Sims and information\n                about them in a grid.\n                '), buff_notification=UiDialogBuffNotification.TunableFactory(description="\n                Display a dialog that will use the text from the Highest Priority Subject's buff \n                with the highest priority. The priority and text will come from the priority and \n                text tuning in the buff's Buff Notification Info when enabled.\n                (If there is a tie for highest, the most recently added tied buff will be chosen.)\n                ", locked_args={'text': None}), story_progression_discovery_notification=UIDialogNotificationStoryProgressionDiscovery.TunableFactory(description='\n                Display a dialog that displays text informing the player of a recently completed story progression\n                chapter. \n                ', locked_args={'text': None}), default='notification')}

    def __init__(self, dialog, **kwargs):
        super().__init__(**kwargs)
        self.dialog = dialog

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not services.current_zone().is_zone_loading:
            owner = subject if subject.is_sim else services.get_active_sim()
            if owner is not None and owner.is_selectable:
                dialog = self.dialog(owner, resolver)
                dialog.show_dialog(event_id=self.dialog.factory.DIALOG_MSG_TYPE)
