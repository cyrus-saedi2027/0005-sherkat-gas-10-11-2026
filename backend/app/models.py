"""Import every module's models so Base.metadata is complete (Alembic, create_all)."""

from app.modules.audit import models as _audit  # noqa: F401
from app.modules.auth import models as _auth  # noqa: F401

# stage 2
from app.modules.cases import models as _cases  # noqa: F401,E402

# Event handlers register on import (reading.approved → cases, referrals).
from app.modules.cases import service as _cases_service  # noqa: F401,E402
from app.modules.content import models as _content  # noqa: F401,E402
from app.modules.files import models as _files  # noqa: F401
from app.modules.notifications import models as _notifications  # noqa: F401
from app.modules.points import models as _points  # noqa: F401
from app.modules.readings import models as _readings  # noqa: F401,E402
from app.modules.referrals import models as _referrals  # noqa: F401
from app.modules.referrals import service as _referrals_service  # noqa: F401,E402
from app.modules.regions import models as _regions  # noqa: F401

# stage 3
from app.modules.reports import models as _reports  # noqa: F401,E402
from app.modules.settings import models as _settings  # noqa: F401
from app.modules.staff import models as _staff  # noqa: F401
from app.modules.store import models as _store  # noqa: F401,E402
from app.modules.subscribers import models as _subscribers  # noqa: F401
from app.modules.surveys import models as _surveys  # noqa: F401,E402
from app.modules.tickets import models as _tickets  # noqa: F401,E402
from app.modules.users import models as _users  # noqa: F401
