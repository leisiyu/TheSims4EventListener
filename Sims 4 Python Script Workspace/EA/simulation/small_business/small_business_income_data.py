from __future__ import annotationsimport pathsfrom dataclasses import dataclassfrom interactions import ParticipantTypefrom interactions.payment.payment_element import PaymentElementfrom protocolbuffers import Consts_pb2, Business_pb2import servicesimport sims4from business.business_enums import SmallBusinessAttendanceSaleMode, BusinessTypefrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.test_events import TestEventfrom interactions.payment.payment_info import PaymentBusinessRevenueTypefrom sims.funds import get_funds_for_source, FundsSourcefrom small_business.small_business_tuning import SmallBusinessTunablesfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import *
    from event_testing.resolver import DataResolver, InteractionResolver
    from small_business.small_business_manager import SmallBusinessManager
    from interactions.base.interaction import Interaction
    from interactions.payment.payment_dest import _PaymentDest
    from interactions.payment.payment_altering_service import PaymentAlteringService
    from sims.sim import Sim
    from sims.sim_info import SimInfo
    from tag import Taglogger = sims4.log.Logger('SmallBusinessIncomeData', default_owner='sersanchez')