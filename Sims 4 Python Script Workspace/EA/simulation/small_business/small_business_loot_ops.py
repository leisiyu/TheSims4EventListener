from __future__ import annotationsimport servicesimport sims4from interactions import ParticipantTypeimport sims4.commandsimport singletonsfrom business.business_enums import SmallBusinessAttendanceSaleMode, BusinessTypefrom interactions import ParticipantTypeSingleSimfrom interactions.utils.loot_basic_op import BaseLootOperation, BaseTargetedLootOperationfrom sims4.tuning.tunable import TunableEnumEntry, TunableFactory, Tunable, TunableEnumFlagsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from sims.sim_info import SimInfologger = sims4.log.Logger('SmallBusinessLootOps', default_owner='sersanchez')
class SmallBusinessSetAttendanceModeLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'attendance_sale_mode': TunableEnumEntry(description='\n            Attendance Sale Mode to set.', tunable_type=SmallBusinessAttendanceSaleMode, default=SmallBusinessAttendanceSaleMode.DISABLED)}

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)

    def __init__(self, *args, attendance_sale_mode, **kwargs):
        super().__init__(*args, **kwargs)
        self._attendance_sale_mode = attendance_sale_mode

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=subject.id)
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return
        business_manager.small_business_income_data.set_attendance_sales_mode(self._attendance_sale_mode)

class SmallBusinessSetMarkupLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'markup_multiplier': Tunable(description='\n            Markup value to set.', tunable_type=float, default=1.0)}

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)

    def __init__(self, *args, markup_multiplier, **kwargs):
        super().__init__(*args, **kwargs)
        self._markup_multiplier = markup_multiplier

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=subject.id)
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return
        business_manager.small_business_income_data.set_markup_multiplier(self._markup_multiplier)

class SmallBusinessSetLightRetailModeLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'light_retail_sale_enabled': Tunable(description='\n            Light Retail Sale Mode to set (either enabled, or disabled).', tunable_type=bool, default=True)}

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)

    def __init__(self, *args, light_retail_sale_enabled, **kwargs):
        super().__init__(*args, **kwargs)
        self._light_retail_sale_enabled = light_retail_sale_enabled

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            return
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=subject.id)
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            return
        business_manager.small_business_income_data.set_light_retail_sales_enabled(self._light_retail_sale_enabled)

class RegisterSmallBusinessLootOp(BaseLootOperation):

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.is_sim:
            logger.error('There is no sim to register small business')
            return
        sims4.commands.execute('business.request_show_small_business_configurator {0} {1}'.format(False, subject.sim_id), None)

class SmallBusinessOpenLootOp(BaseLootOperation):

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.is_sim:
            logger.error('There is no sim to find small business')
            return
        business_manager = services.business_service().get_business_manager_for_sim(sim_id=subject.sim_id)
        is_owner = business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS
        if not is_owner:
            logger.error('No small business is registered to the sim {}', subject.sim_id)
            return
        if business_manager.is_open:
            logger.error('Small business owned by {} is already open', subject.sim_id)
            return
        business_manager.set_open(True)
        if not business_manager.is_open:
            logger.error('Unable to open small business owned by {}', subject.sim_id)

class SmallBusinessCloseLootOp(BaseLootOperation):

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        business_manager = None
        zone_id = services.current_zone_id()
        if subject.is_sim:
            business_manager = services.business_service().get_business_manager_for_sim(sim_id=subject.sim_id)
        if business_manager is None or business_manager.business_type != BusinessType.SMALL_BUSINESS:
            logger.info('Small Business is not available for the sim, therefore fetching small business in current location for close operation')
            business_manager = services.business_service().get_business_manager_for_zone(zone_id)
        is_sb_available = business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS
        if not is_sb_available:
            logger.error('No small business is available to close')
            return
        if not business_manager.is_open:
            logger.error('Cannot close small business as it is not open.')
            return
        business_manager.set_open(False)
        if business_manager.is_open:
            logger.error('Unable to close small business')

class SellSmallBusinessLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'display_confirmation_modal': Tunable(description='\n            If enabled it will display a confirmation modal when selling the business.\n            ', tunable_type=bool, default=True)}

    def __init__(self, *args, display_confirmation_modal, **kwargs):
        super().__init__(*args, **kwargs)
        self._display_confirmation_modal = display_confirmation_modal

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.is_sim:
            logger.error('There is no sim to find small business')
            return
        sims4.commands.execute('business.sell_small_business {0} {1}'.format(subject.sim_id, self._display_confirmation_modal), None)

class TransferSmallBusinessLootOp(BaseTargetedLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('{} has no subject which is required in the TransferSmallBusinessLoot.', resolver)
            return False
        if target is None:
            logger.error('{} has no target {} which is required in the TransferSmallBusinessLoot.', resolver, self.target_participant_type)
            return False
        business_service = services.business_service()
        business_manager = business_service.get_business_manager_for_sim(sim_id=subject.sim_id)
        is_owner = business_manager is not None and business_manager.business_type == BusinessType.SMALL_BUSINESS
        if not is_owner:
            logger.error('No small business is registered to the sim {}', subject.sim_id)
            return
        if business_manager.is_open:
            business_manager.set_open(False)
        business_service.transfer_business_to_sim(subject, target, business_manager.business_type)
