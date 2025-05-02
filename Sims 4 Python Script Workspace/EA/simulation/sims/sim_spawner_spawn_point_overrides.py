from event_testing.resolver import SingleSimResolverfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumWithFilter, TunableTuple, OptionalTunablefrom tag import Tag, SPAWN_PREFIXfrom tunable_utils.tested_list import TunableTestedList, STOP_PROCESSING_ALWAYSfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippet
class TestedSpawnPointOverride(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tested_list': TunableTestedList(tunable_type=TunableTuple(description='\n                A spawn tag to spawn the sim at and associated tuning.\n                ', spawn_tag=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=SPAWN_PREFIX), spawn_notification=OptionalTunable(description='\n                    If enabled and the corresponding spawn tag is chosen, this\n                    notification will display when the sim spawns. \n                    ', tunable=TunableUiDialogNotificationSnippet())), stop_processing_behavior=STOP_PROCESSING_ALWAYS)}

    def get_spawner_tag_and_notification(self, sim_info):
        resolver = SingleSimResolver(sim_info)
        chosen_entry = next(iter(entry for entry in self.tested_list(resolver=resolver)), None)
        if chosen_entry is None:
            return (None, None)
        notification_tuning = chosen_entry.spawn_notification
        notification = None
        if notification_tuning is not None:
            notification = notification_tuning(sim_info, resolver)
        return (chosen_entry.spawn_tag, notification)
