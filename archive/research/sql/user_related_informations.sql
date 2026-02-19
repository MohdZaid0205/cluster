-- This file contains all the querry that are present in scope of users
-- This includes:
--      0. User Access Control
--      1. Listing Users on various stats
--      2. Listing Analytics of all users
--      3. User Verification Status

-- [0]
-- USER ACCESS CONTROL
--    EMAIL     : mary55@example.net
--    PASSWORD  : 4db4d354c3ed5dc61e4be9fb509e4c03eec85ad32f56f3033a25be9f17e8e5c5

-- a. USER CAN LOGIN TO THEIR OWN ACCOUNT
--    SAMPLE DATA USED:
SELECT * from userauth 
    where email = 'mary55@example.net' AND 
    password_hash = '4db4d354c3ed5dc61e4be9fb509e4c03eec85ad32f56f3033a25be9f17e8e5c5'

-- b. USER CANNOT LOGIN INTO SOMEONE ELSES ACCOUNT WITH THEIR PASSWORD
SELECT * from userauth 
    where email = 'peckheather@example.org' AND 
    password_hash = '4db4d354c3ed5dc61e4be9fb509e4c03eec85ad32f56f3033a25be9f17e8e5c5'

-- c. USER CAN FETCH HIS PROFILE STATS
SELECT * from userprofile NATURAL JOIN userauth
    where email = 'mary55@example.net' AND 
    password_hash = '4db4d354c3ed5dc61e4be9fb509e4c03eec85ad32f56f3033a25be9f17e8e5c5'

-- [1]
-- LISTING USERS ON VARIOUS STATS

-- a. LIST POSTS CREATED BY A PARTICULAR USER ALL ACROSS THE CLUSTERS
SELECT uid, content, tags, created_at, cid FROM postcore NATURAL JOIN postcontent
    WHERE uid = '055fe07107514cbeba738b51faaa30a7' 
    ORDER BY created_at DESC

-- b. LIST NUMBER OF POSTS CREATED BY A PARTICULAR USER IN A PARTICULAR CLUSTER
SELECT uid, name, count(pid) FROM postcore NATURAL JOIN postcontent NATURAL JOIN clustercore
    WHERE uid = '055fe07107514cbeba738b51faaa30a7'
    GROUP BY cid ORDER BY count(pid) DESC

-- c. LIST TOP 5 COMMENTS OF A USER BASED ON LIKES COUNT
SELECT uid, content, likes FROM commentcore NATURAL JOIN commentcontent NATURAL JOIN commentstats
    WHERE uid = '055fe07107514cbeba738b51faaa30a7'
    ORDER BY likes DESC LIMIT 5

-- d. LIST TOP 5 POSTS OF A USER BASED ON LIKES COUNT
SELECT uid, content, likes FROM postcore NATURAL JOIN postcontent NATURAL JOIN poststats
    WHERE uid = '055fe07107514cbeba738b51faaa30a7'
    ORDER BY likes DESC LIMIT 5

-- e. LIST TOP 5 POSTS OF A USER BASED ON DISLIKES COUNT
SELECT uid, content, dislikes FROM postcore NATURAL JOIN postcontent NATURAL JOIN poststats
    WHERE uid = '055fe07107514cbeba738b51faaa30a7'
    ORDER BY dislikes DESC LIMIT 5

-- [2]
-- LISTING USERS ON VARIOUS STATS

-- a. LIST TOP 5 USERS BASED ON POST COUNT
SELECT uid, count(pid) FROM postcore 
    WHERE uid in (
        SELECT uid FROM userauth WHERE is_verified = true
    )   
    GROUP BY uid
    ORDER BY count(pid) DESC
    LIMIT 5

-- b. LIST TOP 5 USERS BASED ON AGGREGATE REACTIONS COUNT
SELECT uid, sum(likes), count(pid) FROM postcore NATURAL JOIN poststats
    GROUP BY uid
    ORDER BY sum(likes)
    LIMIT 5

-- c. LIST TOP 5 USERS BASED ON THEIR ENGAGEMENT BASED ON TOTAL REACTION COUNT
SELECT P.uid, count(R.uid) FROM postreaction as R INNER JOIN postcore as P USING (pid)
    GROUP BY P.uid ORDER BY count(R.uid) DESC

-- [3]
-- a. USER VERIFIES HIMSELF AND NOW WE ADD HIS VERIFICATION INFORMATION
UPDATE userauth SET email='verified@verifiedmail.com' 
    WHERE uid='bab750de09e54059afb5ef71a28860b9'