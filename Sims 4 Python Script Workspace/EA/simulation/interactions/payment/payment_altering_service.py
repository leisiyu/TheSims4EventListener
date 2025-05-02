from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import Optional, Callable, Dict, List, Set
    from event_testing.resolver import InteractionResolver
    from interactions.payment.payment_dest import _PaymentDest
    from interactions.base.interaction import Interaction
    from sims.sim import Sim
    from tag import Tagimport sims4from dataclasses import dataclassfrom sims4.service_manager import Servicelogger = sims4.log.Logger('Payment', default_owner='sersanchez')