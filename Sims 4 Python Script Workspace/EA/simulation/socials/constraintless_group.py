from interactions.constraints import Anywherefrom socials.group import SocialGroup
class ConstraintlessGroup(SocialGroup):

    @classmethod
    def make_constraint_default(cls, *args, **kwargs):
        return Anywhere()

    def _make_constraint(self, *args, **kwargs):
        return Anywhere()

    def _get_constraint(self, *args, **kwargs):
        return Anywhere()
