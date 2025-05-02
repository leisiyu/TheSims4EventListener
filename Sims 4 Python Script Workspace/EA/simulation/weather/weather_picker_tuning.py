import servicesimport sims4.resourcesfrom sims4.tuning.tunable import TunablePackSafeReference
class WeatherPickerTuning:
    WEATHER_AFFORDANCE = TunablePackSafeReference(description='\n        The weather affordance to run \n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction')
