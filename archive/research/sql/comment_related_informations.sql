-- This file contains all the querry that are present in scope of comments
-- This includes:
--      0. Comment Retrieval & Threading
--      1. Engagement & Quality
--      2. Reactions & User Interactions

-- [0]
-- COMMENT RETRIEVAL & THREADING
--    PID       :
--    PARENT_MID: comment-uuid-aaaa-bbbb-cccc-dddddddddddd

-- a. GET ALL ROOT COMMENTS FOR A POST (No Parent)
SELECT C.mid, content, likes, created_at
FROM
    commentcore as C
    NATURAL JOIN commentcontent
    NATURAL JOIN commentstats
WHERE
    pid = 'post-uuid-1111-2222-3333-444444444444'
    AND parent_mid IS NULL
ORDER BY created_at ASC

-- b. GET REPLIES TO A SPECIFIC COMMENT
SELECT C.mid, content, likes, created_at
FROM
    commentcore as C
    NATURAL JOIN commentcontent
    NATURAL JOIN commentstats
WHERE
    parent_mid = 'comment-uuid-aaaa-bbbb-cccc-dddddddddddd'
ORDER BY created_at ASC

-- [1]
-- ENGAGEMENT & QUALITY
--    PID       : post-uuid-1111-2222-3333-444444444444

-- a. GET TOP RANKED COMMENTS FOR A POST
SELECT content, likes, dislikes, (likes - dislikes) as score
FROM
    commentcore
    NATURAL JOIN commentcontent
    NATURAL JOIN commentstats
WHERE
    pid = 'post-uuid-1111-2222-3333-444444444444'
ORDER BY score DESC
LIMIT 10

-- [2]
-- REACTIONS & USER INTERACTIONS
--    MID       : comment-uuid-aaaa-bbbb-cccc-dddddddddddd
--    UID       : 1234567890abcdef1234567890abcdef

-- a. LIST USERS WHO LIKED A COMMENT
SELECT U.name, R.timestamp
FROM
    commentreaction as R
    JOIN userprofile as U ON R.uid = U.uid
WHERE
    R.mid = 'comment-uuid-aaaa-bbbb-cccc-dddddddddddd'
    AND R.reaction_type = 'LIKE'

-- b. CHECK IF USER REACTED TO A COMMENT
SELECT reaction_type
FROM commentreaction
WHERE
    mid = 'comment-uuid-aaaa-bbbb-cccc-dddddddddddd'
    AND uid = '1234567890abcdef1234567890abcdef'