"""Registry contains only implemented native adapters, not catalogue placeholders."""
from native_extra_apps import Dittofeed
from native_crm_apps import Twenty, Erxes
from native_formbricks import Formbricks
from native_openreplay import OpenReplay
REGISTRY={'dittofeed':Dittofeed,'twenty':Twenty,'erxes':Erxes,'formbricks':Formbricks,'openreplay':OpenReplay}
