import itertoolsimport sims4from buffs.buff import Bufffrom buffs.buff_display_type import BuffDisplayTypefrom careers.career_enums import CareerCategorylogger = sims4.log.Logger('BurnoutBuff', default_owner='jsampson')
class BurnoutBuff(Buff):

    @property
    def display_type(self):
        return BuffDisplayType.BURNOUT

    def on_add(self, *args, **kwargs):
        super().on_add(*args, **kwargs)
        self._send_career_update_message()

    def on_remove(self, *args, **kwargs):
        super().on_remove(*args, **kwargs)
        self._send_career_update_message()

    def _send_career_update_message(self):
        career_tracker = self._owner.career_tracker
        if career_tracker is None:
            return
        careers_work_gen = career_tracker.get_careers_by_category_gen(CareerCategory.Work)
        careers_adult_part_time_gen = career_tracker.get_careers_by_category_gen(CareerCategory.AdultPartTime)
        careers = list(itertools.chain(careers_work_gen, careers_adult_part_time_gen))
        if len(careers) == 0:
            return
        careers[0].resend_career_data()
