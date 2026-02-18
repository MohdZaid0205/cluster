-- This file contains all the querry that are present in scope of posts
-- This includes:
--      0. Post Retrieval & Filtering
--      1. Post Engagement & Analytics
--      2. Reactions & Interactivity
--      3. Special Post Types (Megaphones & Windows)

-- [0]
-- POST RETRIEVAL & FILTERING
--    PID       : post-uuid-1111-2222-3333-444444444444
--    CID       : a1b2c3d4e5f678901234567890abcdef
--    UID       : 1234567890abcdef1234567890abcdef

-- a. GET FULL POST DETAILS BY ID
SELECT *
FROM postcore
    NATURAL JOIN postcontent
    NATURAL JOIN poststats
WHERE
    pid = 'post-uuid-1111-2222-3333-444444444444'

-- b. LIST ALL POSTS IN A SPECIFIC CLUSTER (Most Recent First)
SELECT P.pid, C.content, S.likes, P.created_at
FROM
    postcore as P
    JOIN postcontent as C ON P.pid = C.pid
    JOIN poststats as S ON P.pid = S.pid
WHERE
    P.cid = 'a1b2c3d4e5f678901234567890abcdef'
ORDER BY P.created_at DESC
LIMIT 50

-- c. LIST ALL POSTS BY A SPECIFIC USER
SELECT P.pid, content, likes, created_at
FROM
    postcore as P
    NATURAL JOIN postcontent
    NATURAL JOIN poststats
WHERE
    uid = '1234567890abcdef1234567890abcdef'
ORDER BY created_at DESC

-- [1]
-- POST ENGAGEMENT & ANALYTICS

-- a. TOP 5 MOST LIKED POSTS IN A CLUSTER
SELECT content, likes
FROM postcontent
    NATURAL JOIN poststats
    NATURAL JOIN postcore
WHERE
    cid = 'a1b2c3d4e5f678901234567890abcdef'
ORDER BY likes DESC
LIMIT 5

-- b. TOP 5 MOST CONTROVERSIAL POSTS (High Dislikes)
SELECT content, dislikes
FROM postcontent
    NATURAL JOIN poststats
    Natural JOIN postcore
WHERE
    cid = 'a1b2c3d4e5f678901234567890abcdef'
ORDER BY dislikes DESC
LIMIT 5

-- [2]
-- REACTIONS & INTERACTIVITY
--    PID       : post-uuid-1111-2222-3333-444444444444

-- a. LIST USERS WHO LIKED A SPECIFIC POST
SELECT U.name, R.timestamp
FROM
    postreaction as R
    JOIN userprofile as U ON R.uid = U.uid
WHERE
    R.pid = 'post-uuid-1111-2222-3333-444444444444'
    AND R.reaction_type = 'LIKE'

-- b. COUNT REACTIONS BY TYPE FOR A POST
SELECT reaction_type, count(*) as count
FROM postreaction
WHERE
    pid = 'post-uuid-1111-2222-3333-444444444444'
GROUP BY
    reaction_type

-- [3]
-- SPECIAL POST TYPES

-- a. LIST ALL ACTIVE MEGAPHONES (Announcements/Events)
SELECT P.pid, C.content, M.type, M.end_time
FROM
    megaphone as M
    JOIN postcore as P ON M.pid = P.pid
    JOIN postcontent as C ON P.pid = C.pid
WHERE
    M.is_active = true
    AND M.end_time > CURRENT_TIMESTAMP

-- b. FIND ALL WINDOWS (SHARES) OF A SPECIFIC ORIGINAL POST
SELECT W.wid, U.name as shared_by, W.created_at
FROM
window as W
    JOIN userprofile as U ON W.shared_by_uid = U.uid
WHERE
    W.origin_pid = 'post-uuid-1111-2222-3333-444444444444'
ORDER BY W.created_at DESC