from call_to_action.call_to_action_elements import OpenStreetDirectorCallToActionMixinfrom event_testing.resolver import GlobalResolver, SingleSimAndHouseholdResolverfrom open_street_director.festival_open_street_director import BaseFestivalOpenStreetDirector, FestivalStateInfo, TimedFestivalState, LoadLayerFestivalState, CleanupObjectsFestivalStatefrom sims4.tuning.tunable import OptionalTunablefrom sims4.utils import classpropertyfrom ui.tested_ui_dialog_notification import TunableTestedUiDialogNotificationSnippetimport event_testing.testsimport servicesimport sims4.commands
class SpinupFestivalState(LoadLayerFestivalState):

    @classproperty
    def key(cls):
        return 1

    def _get_next_state(self):
        return self._owner.main_festival_state(self._owner)

class MainFestivalState(TimedFestivalState):

    @classproperty
    def key(cls):
        return 2

    def on_state_activated(self, reader=None, preroll_time_override=None):
        super().on_state_activated(reader=reader, preroll_time_override=preroll_time_override)
        client = services.client_manager().get_first_client()
        if client is not None:
            sims4.commands.automation_output('Festival; ready:true', client.id)

    def _get_next_state(self):
        return self._owner.cooldown_festival_state(self._owner)

class CooldownFestivalState(TimedFestivalState):
    FACTORY_TUNABLES = {'notification': OptionalTunable(description='\n            If enabled, the notification that will appear when we enter this festival\n            state.\n            ', tunable=TunableTestedUiDialogNotificationSnippet()), 'notification_tests': OptionalTunable(description='\n            If enabled, run this set of tests to determine whether the festival should show the notification or not\n            ', tunable=event_testing.tests.TunableTestSet())}

    @classproperty
    def key(cls):
        return 3

    def on_state_activated(self, reader=None, preroll_time_override=None):
        super().on_state_activated(reader=reader, preroll_time_override=preroll_time_override)
        for situation in self._owner.get_running_festival_situations():
            situation.put_on_cooldown()
        if self.notification is None:
            return
        should_show_notification = True
        if self.notification_tests is not None:
            notification_test_resolver = SingleSimAndHouseholdResolver(services.active_sim_info(), services.active_household())
            should_show_notification = self.notification_tests.run_tests(notification_test_resolver)
        if should_show_notification:
            resolver = GlobalResolver()
            notification = self.notification(services.active_sim_info(), resolver=resolver)
            notification.show_dialog()

    def _get_next_state(self):
        return self._owner.cleanup_festival_state(self._owner)

class CleanupFestivalState(CleanupObjectsFestivalState):

    @classproperty
    def key(cls):
        return 4

    def _get_next_state(self):
        pass

class BasicFestivalOpenStreetDirector(BaseFestivalOpenStreetDirector):
    INSTANCE_TUNABLES = {'spinup_festival_state': SpinupFestivalState.TunableFactory(), 'main_festival_state': MainFestivalState.TunableFactory(), 'cooldown_festival_state': CooldownFestivalState.TunableFactory(), 'cleanup_festival_state': CleanupFestivalState.TunableFactory()}

    @classmethod
    def _states(cls):
        return (FestivalStateInfo(SpinupFestivalState, cls.spinup_festival_state), FestivalStateInfo(MainFestivalState, cls.main_festival_state), FestivalStateInfo(CooldownFestivalState, cls.cooldown_festival_state), FestivalStateInfo(CleanupFestivalState, cls.cleanup_festival_state))

    def _get_starting_state(self):
        return self.spinup_festival_state(self)

    def on_startup(self):
        super().on_startup()
        if self.was_loaded or not self.did_preroll:
            self.change_state(self._get_starting_state())

    def _clean_up(self):
        if self._current_state.key != CleanupFestivalState.key:
            self.change_state(self.cleanup_festival_state(self))

class FestivalWithHighlightOpenStreetDirector(OpenStreetDirectorCallToActionMixin, BasicFestivalOpenStreetDirector):
    pass
