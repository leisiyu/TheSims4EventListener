from sims4.utils import constpropertyfrom traits.preference import Preferencefrom tunable_multiplier import TestedSum
class AttractionPreference(Preference):
    INSTANCE_TUNABLES = {'attraction_modifier': TestedSum.TunableFactory(description="\n            A tested sum that will be applied towards the actor sim's attraction\n            towards the target sim.\n            ")}

    @constproperty
    def is_attraction_trait():
        return True
