from _weakrefset import WeakSetfrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom sims4.tuning.tunable import Tunable
class Liability:

    def release(self):
        pass

    def merge(self, interaction, key, new_liability):
        return new_liability

    def should_transfer(self, continuation):
        return True

    @property
    def is_super_to_mixer_transfer_allowed(self) -> bool:
        return False

    def transfer(self, interaction):
        pass

    def on_reset(self):
        self.release()

    def on_add(self, interaction):
        pass

    def on_run(self):
        pass

    def gsi_text(self):
        return type(self).__name__

    @classmethod
    def on_affordance_loaded_callback(cls, affordance, liability_tuning):
        pass

class ReplaceableLiability(Liability):

    def merge(self, interaction, key, new_liability):
        interaction.remove_liability(key)
        return new_liability

class SharedLiability(Liability):

    def __init__(self, *args, source_liability=None, **kwargs):
        super().__init__(**kwargs)
        self._released = False
        if source_liability is None:
            self._shared_liability_refs = WeakSet()
        else:
            self._shared_liability_refs = source_liability._shared_liability_refs
        self._shared_liability_refs.add(self)

    def shared_release(self):
        raise NotImplementedError('SharedLiability: {} trying to release with no shared_release implementation'.format(self))

    def release(self, *args, **kwargs):
        self._released = True
        if all(cur_liability._released for cur_liability in self._shared_liability_refs):
            self.shared_release(*args, **kwargs)

    def create_new_liability(self, interaction, *args, **kwargs):
        return self.__class__(*args, source_liability=self, **kwargs)

class PreparationLiability(Liability):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_prepared = False

    def on_add(self, interaction):
        super().on_add(interaction)
        if interaction.is_super:
            interaction.add_prepare_liability(self)

    def _prepare_gen(self, timeline):
        raise NotImplementedError

    def transfer(self, continuation):
        super().transfer(continuation)
        self._is_prepared = False

    def on_prepare_gen(self, timeline):
        if self._is_prepared:
            return InteractionQueuePreparationStatus.SUCCESS
        result = yield from self._prepare_gen(timeline)
        if result == InteractionQueuePreparationStatus.SUCCESS:
            self._is_prepared = True
        return result

    def path_generation_deferred(self):
        return False

class LiabilityCrossTransferMixin:
    FACTORY_TUNABLES = {'allow_transfer_from_si_to_mixers': Tunable(description='\n            Generally, SIs can only transfer liabilities to other SIs \n            (and mixers can only transfer liabilities to other mixers). \n            If checked, allow transfer of this liability from SIs to mixers.\n            ', tunable_type=bool, default=False)}

    def __init__(self, allow_transfer_from_si_to_mixers:bool, **kwargs) -> None:
        super().__init__(**kwargs)
        self._allow_transfer_from_si_to_mixers = allow_transfer_from_si_to_mixers

    @property
    def is_super_to_mixer_transfer_allowed(self) -> bool:
        return self._allow_transfer_from_si_to_mixers
