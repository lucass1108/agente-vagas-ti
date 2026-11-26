import re
from datetime import datetime, timezone

import vagas_agent as _va

# Re-export helpers from vagas_agent to keep behavior identical
_pat = _va._pat
acha = _va.acha


def dias_desde(data_iso):
    return _va.dias_desde(data_iso)


def calcula_score(v):
    return _va.calcula_score(v)