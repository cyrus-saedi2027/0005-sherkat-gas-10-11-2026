"""Import every module's models so Base.metadata is complete (Alembic, create_all)."""

from app.modules.audit import models as _audit  # noqa: F401
from app.modules.auth import models as _auth  # noqa: F401
from app.modules.files import models as _files  # noqa: F401
from app.modules.notifications import models as _notifications  # noqa: F401
from app.modules.points import models as _points  # noqa: F401

# Stage 1+: modules register here as they are built.
from app.modules.readings import models as _readings  # noqa: F401,E402
from app.modules.referrals import models as _referrals  # noqa: F401
from app.modules.regions import models as _regions  # noqa: F401
from app.modules.settings import models as _settings  # noqa: F401
from app.modules.staff import models as _staff  # noqa: F401
from app.modules.subscribers import models as _subscribers  # noqa: F401
from app.modules.users import models as _users  # noqa: F401
