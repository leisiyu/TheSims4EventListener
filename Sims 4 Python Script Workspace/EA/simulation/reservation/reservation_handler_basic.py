import functoolsfrom reservation.reservation_handler import _ReservationHandlerfrom reservation.reservation_handler_interlocked import ReservationHandlerInterlockedfrom reservation.reservation_handler_multi import ReservationHandlerMultifrom reservation.reservation_handler_uselist import ReservationHandlerUseListfrom reservation.reservation_result import ReservationResultimport sims4.logfrom sims4.tuning.tunable import Tunablelogger = sims4.log.Logger('Reservation')
class ReservationHandlerBasic(_ReservationHandler):

    def allows_reservation(self, other_reservation_handler):
        if self._is_sim_allowed_to_clobber(other_reservation_handler):
            return ReservationResult.TRUE
        if isinstance(other_reservation_handler, ReservationHandlerUseList):
            return ReservationResult.TRUE
        if isinstance(other_reservation_handler, ReservationHandlerInterlocked):
            return ReservationResult.TRUE
        return ReservationResult(False, '{} disallows any other reservation type: ({})', self, other_reservation_handler, result_obj=self.sim)

    def begin_reservation(self, *args, _may_reserve_already_run=False, **kwargs):
        if self.target.parts is not None:
            logger.error("\n                {} is attempting to execute a basic reservation on {}, which has parts. This is not allowed.\n                {} and its associated postures need to be allowed to run on the object's individual parts in order\n                for this to work properly.\n                ", self.sim, self.target, self.reservation_interaction.get_interaction_type() if self.reservation_interaction is not None else 'The reservation owner')
        if not _may_reserve_already_run:
            result = self.may_reserve(_from_reservation_call=True)
            if not result:
                return result
        super().begin_reservation(*args, _may_reserve_already_run=True, **kwargs)
        return ReservationResult.TRUE

class _ReservationHandlerMultiTarget(_ReservationHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._part_handlers = []

    def _get_reservation_handler_type(self):
        return ReservationHandlerBasic

    def _get_reservation_targets(self):
        raise NotImplementedError

    def allows_reservation(self, other_reservation_handler):
        for handler in self._part_handlers:
            reserve_result = handler.allows_reservation(other_reservation_handler)
            if not reserve_result:
                return reserve_result
        return ReservationResult.TRUE

    def begin_reservation(self, *_, _may_reserve_already_run=False, **__):
        if not _may_reserve_already_run:
            result = self.may_reserve(_from_reservation_call=True)
            if not result:
                return result
        handler_type = self._get_reservation_handler_type()
        for target in self._get_reservation_targets():
            part_handler = handler_type(self._sim, target, reservation_interaction=self._reservation_interaction)
            part_handler.begin_reservation(_may_reserve_already_run=True)
            self._part_handlers.append(part_handler)
        return ReservationResult.TRUE

    def end_reservation(self, *_, **__):
        for part_handler in self._part_handlers:
            part_handler.end_reservation()

    def may_reserve(self, _from_reservation_call=False, **kwargs):
        handler_type = self._get_reservation_handler_type()
        for target in self._get_reservation_targets():
            part_handler = handler_type(self._sim, target, **kwargs)
            result = part_handler.may_reserve(**kwargs)
            if not result:
                return result
        return ReservationResult.TRUE

class ReservationHandlerAllParts(_ReservationHandlerMultiTarget):

    def _get_reservation_targets(self):
        target = self._target
        if target.is_part:
            target = target.part_owner
        if not target.parts:
            targets = (target,)
        else:
            targets = target.parts
        return targets

class ReservationHandlerUnmovableObjects(_ReservationHandlerMultiTarget):

    def _get_reservation_handler_type(self):
        return functools.partial(ReservationHandlerMulti, reservation_limit=None)

    def _get_reservation_targets(self):
        if self._target.live_drag_component is None and self._target.carryable_component is None:
            return (self._target,)
        return ()

class ReservationHandlerSocialGroupExclusive(_ReservationHandler):
    FACTORY_TUNABLES = {'reserve_immediately': Tunable(description='\n            If enabled, this will cause the target of the reservation to be immediately reserved. This is not\n            usually how reservations are supposed to work and should only be used in very specific\n            cases. Please consult your GPE about this option before enabling it.\n            ', tunable_type=bool, default=False)}

    def reserves_immediately(self):
        return self.reserve_immediately

    def allows_reservation(self, other_reservation_handler):
        if self.reservation_interaction.social_group is not None:
            for sim in iter(self.reservation_interaction.social_group):
                if other_reservation_handler.sim is sim:
                    return ReservationResult.TRUE
            return ReservationResult(False, '{} disallows any other reservation type: ({})', self, other_reservation_handler, result_obj=self.sim)
        return ReservationResult(False, '{} disallows reservations made by a sim without a social group.', self, result_obj=self.sim)
