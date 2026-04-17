"""
api/triggers.py

Triggers defined here mirror archive/research/Triggers.sql exactly.
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
    """

    @event.listens_for(engine, "connect")
    def _apply_triggers(dbapi_conn, connection_record):
        import sqlite3
        cursor = dbapi_conn.cursor()
        for ddl in _ALL_TRIGGERS:
            try:
                cursor.execute(ddl)
            except sqlite3.OperationalError as e:
                # Ignore if table doesn't exist yet; triggers will be created when the table exists
                if "no such table" in str(e):
                    pass
                else:
                    raise
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
