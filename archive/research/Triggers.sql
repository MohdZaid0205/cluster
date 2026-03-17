-- TRIGGER 1: trg_init_post_stats
CREATE TRIGGER IF NOT EXISTS trg_init_post_stats
AFTER INSERT ON postcore
FOR EACH ROW
BEGIN
    INSERT INTO poststats (pid, likes, dislikes)
    VALUES (NEW.pid, 0, 0);
END;

-- TRIGGER 2: trg_init_comment_stats
CREATE TRIGGER IF NOT EXISTS trg_init_comment_stats
AFTER INSERT ON commentcore
FOR EACH ROW
BEGIN
    INSERT INTO commentstats (mid, likes, dislikes)
    VALUES (NEW.mid, 0, 0);
END;

-- TRIGGER 3: trg_increment_member_count
CREATE TRIGGER IF NOT EXISTS trg_increment_member_count
AFTER INSERT ON clustermember
FOR EACH ROW
BEGIN
    UPDATE clusterstats
    SET    member_count = member_count + 1
    WHERE  cid = NEW.cid;
END;

-- TRIGGER 4: trg_decrement_member_count
CREATE TRIGGER IF NOT EXISTS trg_decrement_member_count
AFTER DELETE ON clustermember
FOR EACH ROW
BEGIN
    UPDATE clusterstats
    SET    member_count = MAX(0, member_count - 1)
    WHERE  cid = OLD.cid;
END;

-- TRIGGER 5: trg_update_last_active
CREATE TRIGGER IF NOT EXISTS trg_update_last_active
AFTER INSERT ON postcore
FOR EACH ROW
BEGIN
    UPDATE userprofile
    SET    last_active = CURRENT_TIMESTAMP
    WHERE  uid = NEW.uid;
END;