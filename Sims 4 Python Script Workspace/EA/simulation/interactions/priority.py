import enum
class Priority(enum.Int):
    Low = 1
    High = 2
    Critical = 3

class PriorityExtended(Priority, export=False):
    SubLow = 0

def can_priority_displace(priority_new, priority_existing, allow_clobbering=False):
    if priority_new is None:
        return False
    if allow_clobbering:
        return priority_new >= priority_existing
    return priority_new > priority_existing

def can_displace(interaction_new, interaction_existing, allow_clobbering=False, use_max_priority=False):
    existing_interaction_priority = interaction_existing.priority
    if use_max_priority:
        super_priority = interaction_existing.super_interaction.priority if interaction_existing.super_interaction is not None else Priority.Low
        existing_interaction_priority = max(super_priority, existing_interaction_priority)
    if not can_priority_displace(interaction_new.priority, existing_interaction_priority, allow_clobbering=allow_clobbering):
        return False
    if interaction_existing.is_waiting_pickup_putdown:
        return False
    return not interaction_existing.is_cancel_aop
