from interactions.liability import Liabilityfrom sims4.callback_utils import CallableList
class SmallBusinessSatisfactionLiability(Liability):
    LIABILITY_TOKEN = 'SmallBusinessSatisfactionLiability'

    def __init__(self, interaction, callback, **kwargs):
        super().__init__(**kwargs)
        self._interaction = interaction
        self._release_liability_callback = CallableList()
        if callback not in self._release_liability_callback:
            self._release_liability_callback.append(callback)

    def release(self):
        self._release_liability_callback()
        self._release_liability_callback = None

    def should_transfer(self, continuation):
        return True

    def transfer(self, continuation):
        self._interaction = continuation
