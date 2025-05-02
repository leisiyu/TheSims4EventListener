from __future__ import annotationsimport servicesfrom element_utils import build_elementfrom event_testing.tests import TunableTestSetfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableList, TunableTuple, TunableVariant, TunableRange, TunableMapping, TunableEnumEntryfrom snippets import TunableSnippetfrom typing import TYPE_CHECKINGfrom ui.notification_suppression_enums import TNSSuppressionGroupif TYPE_CHECKING:
    from ui.ui_dialog_notification import UiDialogNotification
    from scheduling import Timeline
    from GameplaySaveData_pb2 import PersistableUiDialogService
    from typing import *
class _BaseSuppressionStrategy(HasTunableFactory, AutoFactoryInit):

    def execute(self, limit:'int', passed_callback:'Callable[(None, None)]', suppressed_callback:'Callable[(None, None)]') -> 'None':
        raise NotImplementedError

    def get_suppression_count(self) -> 'int':
        raise NotImplementedError

    def set_suppression_count(self, value:'int') -> 'None':
        raise NotImplementedError

class _SuppressForTick(_BaseSuppressionStrategy):

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._suppression_count = 0

    def execute(self, limit:'int', passed_callback:'Callable[(None, None)]', suppressed_callback:'Callable[(None, None)]') -> 'None':
        self._suppression_count += 1
        if self._suppression_count > 1:
            return

        def _next_tick_callback(_:'Timeline') -> 'Optional[Any]':
            if self._suppression_count < limit:
                passed_callback()
            else:
                suppressed_callback()
            self._suppression_count = 0

        element = build_element((_next_tick_callback,))
        services.time_service().sim_timeline.schedule(element)

    def get_suppression_count(self) -> 'int':
        return self._suppression_count

    def set_suppression_count(self, value:'int') -> 'None':
        self._suppression_count = value

class _SuppressForSave(_BaseSuppressionStrategy):

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._suppressed = False

    def execute(self, limit:'int', passed_callback:'Callable[(None, None)]', suppressed_callback:'Callable[(None, None)]') -> 'None':
        if self._suppressed:
            suppressed_callback()
        else:
            passed_callback()
        self._suppressed = True

    def get_suppression_count(self) -> 'int':
        if self._suppressed:
            return 1
        return 0

    def set_suppression_count(self, value:'int') -> 'None':
        self._suppressed = value > 0

class _BaseFallbackStrategy(HasTunableFactory, AutoFactoryInit):

    def execute(self, source_tns:'UiDialogNotification', **kwargs) -> 'None':
        raise NotImplementedError

class _FallbackToNothing(_BaseFallbackStrategy):

    def execute(self, source_tns:'UiDialogNotification', **kwargs) -> 'None':
        pass

class _FallbackToTns(_BaseFallbackStrategy):
    FACTORY_TUNABLES = {'tns': TunableSnippet(description='\n            The TNS we will show instead when we suppress the original TNSes.\n            ', snippet_type='Notification', pack_safe=True)}

    def execute(self, source_tns:'UiDialogNotification', **kwargs) -> 'None':
        source_tns.build_from_type(self.tns).show_dialog(**kwargs)

class _FallbackToTestedTns(_BaseFallbackStrategy):
    FACTORY_TUNABLES = {'tested_tnses': TunableList(description='\n            A list of tests and the TNS to show if that test succeeds.\n            Will only show the first TNS in the list to pass its tests.\n            ', tunable=TunableTuple(description='\n                The tests and the TNS to show if those tests succeed.\n                ', tests=TunableTestSet(description='\n                    The tests to see if we should show this TNS.\n                    '), tns=TunableSnippet(description='\n                    The TNS to show if the associated tests pass.\n                    ', snippet_type='Notification', pack_safe=True))), 'fallback_strategy': TunableVariant(description='\n            What to do when none of the tested TNSes pass?\n            ', do_nothing=_FallbackToNothing.TunableFactory(description='\n                Do nothing when none of the tested TNSes pass.\n                '), show_tns=_FallbackToTns.TunableFactory(description='\n                Display a tuned TNS when none of the tested TNSes pass.\n                '), default='do_nothing')}

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._fallback_strategy = self.fallback_strategy()

    def execute(self, source_tns:'UiDialogNotification', **kwargs) -> 'None':
        resolver = source_tns.get_resolver()
        if resolver is None:
            self._fallback_strategy.execute(source_tns, **kwargs)
            return
        for tns_pair in self.tested_tnses:
            if tns_pair.tests.run_tests(resolver):
                source_tns.build_from_type(tns_pair.tns).show_dialog(**kwargs)
                return
        self._fallback_strategy.execute(source_tns, **kwargs)

class TNSSuppression(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'limit': TunableRange(description='\n            How many TNSes do we want to allow before we start suppressing?\n            ', tunable_type=int, minimum=1, default=1), 'suppression_strategy': TunableVariant(description='\n            How do we want to be suppressing these TNSes?\n            ', suppress_for_tick=_SuppressForTick.TunableFactory(description='\n                Suppress these TNSes for a single tick.\n                '), suppress_for_save=_SuppressForSave.TunableFactory(description='\n                Suppress these TNSes for an entire save.\n                '), default='suppress_for_tick'), 'fallback_strategy': TunableVariant(description='\n            When these TNSes are suppressed, what do we want to do?\n            ', do_nothing=_FallbackToNothing.TunableFactory(description='\n                Do nothing.\n                '), show_tns=_FallbackToTns.TunableFactory(description='\n                Show a fallback TNS.\n                '), show_tested_tns=_FallbackToTestedTns.TunableFactory(description='\n                Select a TNS to show based on tests.\n                '), default='do_nothing')}

    def __init__(self, *args, **kwargs) -> 'None':
        super().__init__(*args, **kwargs)
        self._strategy = self.suppression_strategy()
        self._fallback_strategy = self.fallback_strategy()

    def try_show_tns(self, tns:'UiDialogNotification', call_on_show:'Callable[(None, None)]', **kwargs) -> 'None':
        if tns.tns_suppression_group is None:
            call_on_show()
        self._strategy.execute(self.limit, call_on_show, lambda : self._fallback_strategy.execute(tns, **kwargs))

    def save(self, data:'PersistableUiDialogService.SuppressionEntry') -> 'None':
        data.suppression_count = self._strategy.get_suppression_count()

    def load(self, data:'PersistableUiDialogService.SuppressionEntry') -> 'None':
        self._strategy.set_suppression_count(data.suppression_count)

class NotificationSuppressionTuning:
    SUPPRESSION_GROUP_CONFIG_MAPPING = TunableMapping(description='\n        A mapping of suppression groups to their suppression configs.\n        If we want to suppress a category of TNSes (such as milestones),\n        use this tuning.\n        ', key_type=TunableEnumEntry(tunable_type=TNSSuppressionGroup, default=TNSSuppressionGroup.NONE, invalid_enums=(TNSSuppressionGroup.NONE,)), value_type=TNSSuppression.TunableFactory(description='\n            The suppression config for the suppression group.\n            '))
