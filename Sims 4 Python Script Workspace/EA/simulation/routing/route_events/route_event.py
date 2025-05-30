import weakreffrom protocolbuffers import Routing_pb2 as routing_protocolsfrom broadcasters.broadcaster_request import BroadcasterRequestfrom date_and_time import TICKS_PER_REAL_WORLD_SECOND, TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolver, SingleObjectResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.utils.success_chance import SuccessChancefrom native.animation.arb import BlockOnAnimationTagfrom routing.route_enums import RouteEventPriorityfrom routing.route_events.route_event_mixins import RouteEventBasefrom routing.route_events.route_event_type_animation import RouteEventTypeAnimationfrom routing.route_events.route_event_type_balloon import RouteEventTypeBalloonfrom routing.route_events.route_event_type_create_carry import RouteEventTypeCreateCarryfrom routing.route_events.route_event_type_empty import RouteEventTypeEmptyfrom routing.route_events.route_event_type_exit_carry import RouteEventTypeExitCarryfrom routing.route_events.route_event_type_set_posture import RouteEventTypeSetPosturefrom routing.route_events.route_event_utils import RouteEventSchedulePreferencefrom sims4 import resourcesfrom sims4.tuning.instance_manager import GET_TUNING_SUGGESTIONSfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import TunableEnumEntry, Tunable, TunableVariant, OptionalTunable, TunableList, TunableTuple, TunablePercent, TunableReferenceimport alarmsimport id_generatorimport servicesimport sims4.loglogger = sims4.log.Logger('RouteEvents', default_owner='rmccord')MINIMUM_ROUTE_EVENT_SEGMENT_DURATION_RATIO = 25
class RouteEvent(RouteEventBase, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(resources.Types.SNIPPET)):
    INSTANCE_TUNABLES = {'event_type': TunableVariant(description='\n            Define what is the event that is played.\n            ', animation=RouteEventTypeAnimation.TunableFactory(), balloon=RouteEventTypeBalloon.TunableFactory(), create_carry=RouteEventTypeCreateCarry.TunableFactory(locked_args={'loots_on_xevt': None}), exit_carry=RouteEventTypeExitCarry.TunableFactory(locked_args={'loots_on_xevt': None}), empty=RouteEventTypeEmpty.TunableFactory(), set_posture=RouteEventTypeSetPosture.TunableFactory(), default='animation'), 'priority': TunableEnumEntry(description='\n            The priority at which we play this route event when it overlaps\n            with another of the same Type.\n            ', tunable_type=RouteEventPriority, default=RouteEventPriority.DEFAULT), 'tests': TunableTestSet(description='\n            Tests whether or not the animation will play during a route. The\n            participants for these tests are dependent on the instance that\n            references this Route Event.\n            '), 'retest_on_execute': Tunable(description='\n            If True, Tests that will be re-run right as client executes this \n            route event. If these tests fail, gameplay will not provide any \n            loots or process any deferred animations or broadcasters.\n            ', tunable_type=bool, default=False), 'chance': SuccessChance.TunableFactory(description='\n            Percent Chance that the Route Event will play.\n            '), 'skippable': Tunable(description="\n            If disabled, this route event will not be skippable on the Client.\n            They will attempt to play it no matter what. This should only be\n            used in cases where the route event would stop the Sim's locomotion\n            so they can animate at a particular point on the ground. If you\n            disable this on an animation that does not stop locomotion, it\n            could look quite irregular.\n                        \n            Use caution when disabling this. Consult your GPE partner.\n            ", tunable_type=bool, default=True), 'scheduling_override': OptionalTunable(description='\n            If enabled, we will override schedule preference for the route\n            event and schedule it accordingly.\n            ', tunable=TunableEnumEntry(description='\n                The schedule preference we want this route event to obey.\n                ', tunable_type=RouteEventSchedulePreference, default=RouteEventSchedulePreference.BEGINNING)), 'prefer_straight_paths': OptionalTunable(description="\n            If enabled, we will try to center this animation on the longest \n            segment available.\n            \n            Note: We do not consider collinear segments to be a single segment,\n            and won't take that into account when finding the longest.\n            ", tunable=TunableTuple(description='\n                Tuning for straight path requirements.\n                ', straight_path_offset=OptionalTunable(description='\n                    If enabled, allows setting a percentage offset (in time\n                    from the beginning of the route event) at which to start\n                    requiring a straight path. If disabled, the straight path\n                    will portion will be the center of the route event.\n                    ', tunable=TunablePercent(description='\n                        The offset of the straight path portion\n                        ', default=0)), straight_path_percentage=TunablePercent(description='\n                    The percent of the duration that we require to be\n                    on a straight segment.\n                    ', default=MINIMUM_ROUTE_EVENT_SEGMENT_DURATION_RATIO))), 'loot_actions': TunableList(description='\n            A list of loot actions that are processed when the route event\n            fires, not when the event is scheduled.\n            ', tunable=TunableReference(description='\n                A loot action that fires when the route event is hit.\n                \n                Note: This will not fire when the route event is scheduled.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'broadcaster': OptionalTunable(description='\n            If enabled, we will create a broadcaster and attach it to the Sim.\n            It will ping at least once, and will be disabled when we have\n            finished playing any content attached to this Route Event.\n            ', tunable=BroadcasterRequest.TunableFactory(description='\n                A broadcaster that is created when the route event fires and is\n                destroyed at the end of the duration.\n                ')), 'allowed_at_animated_portal': Tunable(description='\n            If enabled, we allow this route event to play at portals that has\n            animation on them (e.g. stairs). \n            ', tunable_type=bool, default=False), 'loot_at_end': Tunable(description='\n            loot will be given approximately at the end of the event\n            instead of when the event is triggered.\n            ', tunable_type=bool, default=False)}

    @classmethod
    def _verify_tuning_callback(cls):
        if hasattr(cls.event_type.factory, '_verify_tuning_callback'):
            cls.event_type.factory._verify_tuning_callback(cls.event_type)

    @classmethod
    def _get_tuning_suggestions(cls, print_suggestion):
        if hasattr(cls.event_type.factory, GET_TUNING_SUGGESTIONS):
            get_tuning_suggestions = getattr(cls.event_type.factory, GET_TUNING_SUGGESTIONS)
            get_tuning_suggestions(cls.event_type, print_suggestion)
        if cls.retest_on_execute:
            print_suggestion('Retest_on_execute is set. This option should only be used for route events that defer processing', owner='rrodgers')
        if not cls.skippable:
            print_suggestion('Skippable is disabled. This is a highly uncommonoption. Please read its description.', owner='rrodgers')

    def __init__(self, *args, provider=None, provider_required=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag = 0
        self.provider_ref = weakref.ref(provider) if provider is not None else None
        self.event_id = id_generator.generate_object_id()
        self.event_data = None
        self._end_alarm = None
        self.actor = None
        self._processed = False
        self._provider_required = provider_required

    @property
    def id(self):
        return self.event_id

    @property
    def processed(self):
        return self._processed

    @property
    def route_event_parameters(self):
        return {'provider': self.provider, 'provider_required': self._provider_required}

    @property
    def duration(self):
        duration_override = self.event_data.duration_override
        if duration_override is not None:
            return duration_override
        return super().duration

    @property
    def provider(self):
        if self.provider_ref is not None:
            return self.provider_ref()

    @classmethod
    def test(cls, resolver, from_update=False):
        result = cls.tests.run_tests(resolver)
        if not result:
            return result
        if not from_update:
            actor = resolver.get_participant(ParticipantType.Actor)
            actor = actor.sim_info.get_sim_instance() if actor is not None and actor.is_sim else actor
            event_type = cls.event_type
            result = event_type.factory.test(actor, event_type)
            if not result:
                return result
        return TestResult.TRUE

    def prepare_route_event(self, sim, defer_process_until_execute=False):
        self.event_data = self.event_type()
        if hasattr(self.event_data, 'defer_process_until_execute'):
            self.event_data.defer_process_until_execute = defer_process_until_execute
        self.event_data.prepare(sim)

    def on_executed(self, sim, path=None, force_alarm=False):
        provider = self.provider
        if provider is not None:
            provider.on_event_executed(self, sim)
        if self.retest_on_execute and not self.test(self.get_resolver(sim)):
            return
        self.event_data.execute(sim, path=path)
        if self.broadcaster is not None:
            broadcaster_request = self.broadcaster(sim)
            broadcaster_request.start_one_shot()
        if not self.loot_at_end:
            self._give_loot(sim)
        if self.duration == 0:
            self._on_end()
        elif force_alarm or self.loot_at_end:
            self.actor = sim
            self._end_alarm = alarms.add_alarm(self, TimeSpan(self.duration*TICKS_PER_REAL_WORLD_SECOND), self._on_end)

    def _give_loot(self, sim):
        if self.loot_actions:
            resolver = self.get_resolver(sim)
            for loot_action in self.loot_actions:
                loot_action.apply_to_resolver(resolver)

    def get_resolver(self, actor, **kwargs):
        if actor.is_sim:
            return SingleSimResolver(actor.sim_info)
        else:
            return SingleObjectResolver(actor)

    def process(self, actor, time):
        self.time = time
        if self._processed:
            return
        with BlockOnAnimationTag() as tag:
            self.tag = tag
            self.event_data.process(actor)
        self._processed = True

    def is_route_event_valid(self, route_event, time, sim, path):
        provider = self.provider
        if self.provider is None:
            return not self._provider_required
        return provider.is_route_event_valid(route_event, time, sim, path)

    def build_route_event_msg(self, route_msg, time):
        with ProtocolBufferRollback(route_msg.events) as event_msg:
            event_msg.id = self.id
            event_msg.time = time
            event_msg.skippable = self.skippable
            event_msg.type = routing_protocols.RouteEvent.BARRIER_EVENT
            event_msg.duration = self.duration
            if self.tag:
                event_msg.tag = self.tag

    def _on_end(self, *args):
        self._end_alarm = None
        if self.loot_at_end:
            self._give_loot(self.actor)
