"""
api/triggers.py

Triggers defined here mirror archive/research/Triggers.sql exactly.
Registration is wrapped in a try/except so the engine can start even
if the tables haven't been created yet (triggers are re-applied on
every new DBAPI connection, so they'll succeed after create_all).
"""

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# DDL for each trigger
# ---------------------------------------------------------------------------

_TRIGGER_INIT_POST_STATS = """
CREATE TRIGGER IF NOT EXISTS trg_init_post_stats
AFTER INSERT ON postcore
FOR EACH ROW
BEGIN
    INSERT INTO poststats (pid, likes, dislikes)
    VALUES (NEW.pid, 0, 0);
END
"""

_TRIGGER_INIT_COMMENT_STATS = """
CREATE TRIGGER IF NOT EXISTS trg_init_comment_stats
AFTER INSERT ON commentcore
FOR EACH ROW
BEGIN
    INSERT INTO commentstats (mid, likes, dislikes)
    VALUES (NEW.mid, 0, 0);
END
"""

_TRIGGER_INCREMENT_MEMBER_COUNT = """
CREATE TRIGGER IF NOT EXISTS trg_increment_member_count
AFTER INSERT ON clustermember
FOR EACH ROW
BEGIN
    UPDATE clusterstats
    SET    member_count = member_count + 1
    WHERE  cid = NEW.cid;
END
"""

_TRIGGER_DECREMENT_MEMBER_COUNT = """
CREATE TRIGGER IF NOT EXISTS trg_decrement_member_count
AFTER DELETE ON clustermember
FOR EACH ROW
BEGIN
    UPDATE clusterstats
    SET    member_count = MAX(0, member_count - 1)
    WHERE  cid = OLD.cid;
END
"""

_TRIGGER_UPDATE_LAST_ACTIVE = """
CREATE TRIGGER IF NOT EXISTS trg_update_last_active
AFTER INSERT ON postcore
FOR EACH ROW
BEGIN
    UPDATE userprofile
    SET    last_active = CURRENT_TIMESTAMP
    WHERE  uid = NEW.uid;
END
"""

_ALL_TRIGGERS = [
    _TRIGGER_INIT_POST_STATS,
    _TRIGGER_INIT_COMMENT_STATS,
    _TRIGGER_INCREMENT_MEMBER_COUNT,
    _TRIGGER_DECREMENT_MEMBER_COUNT,
    _TRIGGER_UPDATE_LAST_ACTIVE,
]

# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------

def register_triggers(engine: Engine) -> None:
    """
    Attach all application triggers to the given SQLAlchemy engine.

    Uses the `connect` event so that every new raw DBAPI connection
    (including StaticPool test connections) gets the triggers applied
    immediately after the schema tables exist.

    Silently ignores errors if tables don't exist yet – they'll be
    retried on the next connection after create_all runs.
    """

    @event.listens_for(engine, "connect")
    def _apply_triggers(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        for ddl in _ALL_TRIGGERS:
            try:
                cursor.execute(ddl)
            except Exception:
                pass  # table doesn't exist yet, will retry on next connection
        cursor.close()


def apply_triggers_now(engine: Engine) -> None:
    """
    Immediately execute all trigger DDL against the current live connection.

    Use this in test fixtures (StaticPool / in-memory databases) where the
    connection is already open and the `connect` event won't re-fire.
"""
    with engine.connect() as conn:
        for ddl in _ALL_TRIGGERS:
            conn.execute(text(ddl))
        conn.commit()
