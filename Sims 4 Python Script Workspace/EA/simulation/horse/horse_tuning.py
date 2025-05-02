import enumimport servicesimport sims4.resourcesfrom sims4.tuning.tunable import Tunable, TunablePackSafeReferencefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippet
class HorseTuning:
    PAIRED_HORSE_MINIMUM_ROUTE_NEARBY_DISTANCE = Tunable(description='\n        The minimum distance we require for the horse to try to route nearby.\n        If the carried sim wants to dismount the horse, we will evaluate whether\n        their path is sufficiently far, and try to have the horse route near their\n        final destination before retrying on the rider.\n        ', tunable_type=float, default=5.0)
    ROUTE_NEARBY_DISMOUNT_RADIUS = Tunable(description="\n        Tuned radius for the fallback dismount during Route Rider Nearby. This is \n        used to generate a circle constraint when the rider is unable to use the \n        original interaction's constraint, and should accommodate the size of the horse.\n        \n        i.e. when a horse is blocked from routing a rider to their original\n        destination by a portal, we will generate a constraint from this radius.\n        ", tunable_type=float, default=5.0)
    HORSE_FIRST_PLAY_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        The notification to show a household if they have a horse \n        a part of their family.\n        ')
    REINS_DOWN_TRAIT = TunablePackSafeReference(description='\n        Trait that gets added to the rider when the reins are down.\n        ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT))

class PairedHorseTransitionState(enum.Int):
    NOT_STARTED = 0
    WAITING = 1
    FINISHED = 2
