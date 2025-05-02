from distributor import shared_messagesfrom distributor.system import Distributorfrom protocolbuffers import Consts_pb2, UI_pb2from sims.ghost_powers.ghost_powers_tuning import GhostPowersTunablesfrom sims4.commands import CommandTypefrom sims4.common import Packimport servicesimport sims4
@sims4.commands.Command('ghost_powers.get_ultimate_progress', command_type=CommandType.Live, pack=Pack.EP17)
def get_ultimate_progress(sim_id:int, _connection=None):
    sim_info = services.sim_info_manager().get(sim_id)
    good_ultimate_stat = GhostPowersTunables.GHOST_POWERS_GOOD_ULTIMATE_STATISTIC
    evil_ultimate_stat = GhostPowersTunables.GHOST_POWERS_EVIL_ULTIMATE_STATISTIC
    good_stat_tracker = sim_info.get_tracker(good_ultimate_stat)
    evil_stat_tracker = sim_info.get_tracker(evil_ultimate_stat)
    if good_stat_tracker is None or evil_stat_tracker is None:
        return
    good_stat = good_stat_tracker.get_statistic(good_ultimate_stat)
    evil_stat = evil_stat_tracker.get_statistic(evil_ultimate_stat)
    ultimate_progress_msg = UI_pb2.GhostUltimateStatisticProgress()
    ultimate_progress_msg.good_ultimate_progress = int(round(good_stat.get_value()))
    ultimate_progress_msg.evil_ultimate_progress = int(round(evil_stat.get_value()))
    op = shared_messages.create_message_op(ultimate_progress_msg, Consts_pb2.MSG_GHOST_POWERS_ULTIMATE_PROGRESS)
    Distributor.instance().add_op_with_no_owner(op)
