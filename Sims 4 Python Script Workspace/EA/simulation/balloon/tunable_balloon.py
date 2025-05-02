from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from elements import Element
    from event_testing.resolver import Resolver
    from interactions.base.interaction import Interaction
    from objects.game_object import GameObject
    from sims4.math import Vector3
    from typing import *import randomfrom balloon.balloon_enums import BALLOON_TYPE_LOOKUPfrom balloon.balloon_request import BalloonRequestfrom balloon.balloon_variant import BalloonVariantfrom interactions import ParticipantTypefrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import TunableFactory, Tunable, TunableEnumFlags, TunableList, TunableRange, TunablePercent, OptionalTunableimport gsi_handlersimport sims4.loglogger = sims4.log.Logger('Balloons')
class TunableBalloon(TunableFactory):
    X_ACTOR_EVENT = 710
    Y_ACTOR_EVENT = 711
    BALLOON_DURATION = Tunable(description='\n        The duration, in seconds, that a balloon should last.\n        ', tunable_type=float, default=3.0)

    @staticmethod
    def factory(interaction:'Interaction', balloon_target:'ParticipantType', balloon_choices:'List[BalloonVariant]', balloon_delay:'float', balloon_delay_random_offset:'range', balloon_chance:'float', balloon_view_offset:'Vector3', used_target_set:'Optional[Set[GameObject]]'=None, balloon_target_override:'ParticipantType'=None, sequence:'Element'=None, **kwargs) -> 'Union[List[BalloonRequest], List[Union[BalloonRequest, Element]], Element]':
        balloon_requests = []
        if interaction is None:
            if sequence is not None:
                return sequence
            return balloon_requests
        else:
            balloon_requests = TunableBalloon.build_balloon_requests(interaction.get_resolver(), balloon_target, balloon_choices, balloon_delay, balloon_delay_random_offset, balloon_chance, balloon_view_offset, used_target_set, balloon_target_override, sequence, source=interaction, **kwargs)
            if sequence is not None:
                return (balloon_requests, sequence)
        return balloon_requests

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(balloon_target=TunableEnumFlags(description='\n                             Who to play balloons over relative to the interaction. \n                             Generally, balloon tuning will use either balloon_animation_target \n                             or balloon_target.\n                             ', enum_type=ParticipantType, default=ParticipantType.Invalid, invalid_enums=(ParticipantType.Invalid,), minlength=1), balloon_choices=TunableList(description='\n                             A list of the balloons and balloon categories\n                             ', tunable=BalloonVariant.TunableFactory()), balloon_delay=Tunable(float, None, description='\n                             If set, the number of seconds after the start of the animation to \n                             trigger the balloon. A negative number will count backwards from the \n                             end of the animation.'), balloon_delay_random_offset=TunableRange(float, 0, minimum=0, description='\n                             The amount of randomization that is added to balloon requests. \n                             Will always offset the delay time later, and requires the delay \n                             time to be set to a number. A value of 0 has no randomization.'), balloon_chance=TunablePercent(100, description='\n                             The chance that the balloon will play.'), balloon_view_offset=OptionalTunable(description='\n                             If enabled, the Vector3 offset from the balloon bone to the thought balloon. \n                             ', tunable=TunableVector3(default=TunableVector3.DEFAULT_ZERO)), verify_tunable_callback=TunableBalloon._verify_tunable_callback, **kwargs)

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, balloon_target=None, balloon_choices=None, balloon_delay=None, balloon_delay_random_offset=None, balloon_chance=None, balloon_view_offset=None):
        if balloon_delay is not None and balloon_delay < 0 and balloon_delay_random_offset >= -balloon_delay:
            logger.error('Tuning error: Balloon random offset ({}) is not smaller in magnitude                          than its negative delay ({})'.format(balloon_delay, balloon_delay_random_offset))

    @staticmethod
    def build_balloon_requests(resolver:'Resolver', balloon_target:'ParticipantType', balloon_choices:'List[BalloonVariant]', balloon_delay:'float', balloon_delay_random_offset:'range', balloon_chance:'float', balloon_view_offset:'Vector3', used_target_set:'Optional[Set[GameObject]]'=None, balloon_target_override:'ParticipantType'=None, sequence:'Element'=None, source:'Union[Resolver, Interaction]'=None, **kwargs) -> 'Union[List[BalloonRequest], Element]':
        balloon_requests = []
        roll = random.uniform(0, 1)
        if roll > balloon_chance:
            if sequence is not None:
                return sequence
            return balloon_requests
        if used_target_set is None:
            used_target_set = set()
        balloon_targets = resolver.get_participants(balloon_target)
        for target in balloon_targets:
            if target.is_sim:
                target = target.sim_info.get_sim_instance()
            if target is None:
                pass
            else:
                if gsi_handlers.balloon_handlers.archiver.enabled:
                    gsi_entries = []
                else:
                    gsi_entries = None
                balloon_icon = TunableBalloon.select_balloon_icon(balloon_choices, resolver, gsi_entries=gsi_entries, gsi_balloon_target_override=balloon_target_override)
                category_icon = None
                if balloon_icon is not None:
                    icon_info = balloon_icon.icon(resolver, balloon_target_override=balloon_target_override)
                    if balloon_icon.category_icon is not None:
                        category_icon = balloon_icon.category_icon(resolver, balloon_target_override=balloon_target_override)
                else:
                    icon_info = None
                if gsi_handlers.balloon_handlers.archiver.enabled:
                    gsi_handlers.balloon_handlers.archive_balloon_data(target, source, balloon_icon, icon_info, gsi_entries)
                if balloon_icon is not None:
                    if target in used_target_set:
                        logger.error('{} (id:{}) has multiple balloons tuned for source {}. This is not supported.', target, target.id, source)
                    else:
                        used_target_set.add(target)
                        if icon_info[0] is None and icon_info[1] is None:
                            pass
                        else:
                            (balloon_type, priority) = BALLOON_TYPE_LOOKUP[balloon_icon.balloon_type]
                            balloon_overlay = balloon_icon.overlay
                            request = BalloonRequest(target, icon_info[0], icon_info[1], balloon_overlay, balloon_type, priority, TunableBalloon.BALLOON_DURATION, balloon_delay, balloon_delay_random_offset, category_icon, balloon_view_offset)
                            balloon_requests.append(request)
        return balloon_requests

    @staticmethod
    def get_balloon_requests(interaction, overrides):
        balloon_requests = []
        used_target_set = set()
        for balloon in overrides.balloons:
            new_balloon_requests = balloon(interaction, used_target_set=used_target_set, balloon_target_override=overrides.balloon_target_override)
            balloon_requests.extend(new_balloon_requests)
        return balloon_requests

    @staticmethod
    def _get_balloon_icons(balloon_choices, resolver, **kwargs):
        possible_balloons = []
        for balloon in balloon_choices:
            balloons = balloon.get_balloon_icons(resolver, **kwargs)
            possible_balloons.extend(balloons)
        return possible_balloons

    @staticmethod
    def select_balloon_icon(balloon_choices, resolver, **kwargs):
        possible_balloons = TunableBalloon._get_balloon_icons(balloon_choices, resolver, **kwargs)
        chosen_balloon = sims4.random.weighted_random_item(possible_balloons)
        return chosen_balloon
