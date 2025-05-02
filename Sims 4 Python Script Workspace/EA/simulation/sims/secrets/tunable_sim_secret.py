import servicesimport sims4.resourcesfrom interactions.utils.display_mixin import get_display_mixinfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable_base import ExportModesfrom tunable_multiplier import TunableMultiplierlogger = sims4.log.Logger('Sim Secrets', default_owner='cparrish')TunableSimSecretDisplayMixin = get_display_mixin(has_icon=True, has_tooltip=True, use_string_tokens=True, export_modes=ExportModes.All)
class SimSecret(TunableSimSecretDisplayMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SNIPPET)):
    INSTANCE_TUNABLES = {'weight': TunableMultiplier.TunableFactory(description='\n            The weight of this secret being chosen based on tuned tests.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blackmailed = False

    @classmethod
    def _verify_tuning_callback(cls):
        if not cls._display_data.instance_display_name:
            logger.error("Secrets require a display name, but secret ({})'s display name has a value of None.".format(str(cls)))
        if not cls._display_data.instance_display_tooltip:
            logger.error("Secrets require a display tooltip, but secret ({})'s display tooltip has a value of None.".format(str(cls)))
        if not cls._display_data.instance_display_icon:
            logger.error("Secrets require a display icon, but secret ({})'s display icon has a value of None.".format(str(cls)))

    @property
    def display_name(self):
        return self._display_data.instance_display_name
