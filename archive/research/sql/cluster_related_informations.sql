-- This file contains all the querry that are present in scope of clusters
-- This includes:
--      0. Cluster Discovery & Listing
--      1. Cluster Details & Rules
--      2. Membership & Roles
--      3. Analytics & Rankings

-- [0]
-- CLUSTER DISCOVERY & LISTING
--    CATEGORY  : Tech

-- a. LIST ALL PUBLIC CLUSTERS WITH MEMBER COUNTS
SELECT cid, name, category, member_count
FROM clustercore
    NATURAL JOIN clusterstats
WHERE
    is_private = false
ORDER BY member_count DESC

-- b. SEARCH CLUSTERS BY NAME
SELECT cid, name, category
FROM clustercore
WHERE
    name LIKE '%Ltd%'

-- c. LIST CLUSTERS BY CATEGORY
SELECT cid, name, member_count
FROM clustercore
    NATURAL JOIN clusterstats
WHERE
    category = 'Tech'
ORDER BY member_count DESC

-- [1]
-- CLUSTER DETAILS & RULES
--    CID       : a1b2c3d4e5f678901234567890abcdef

-- a. GET FULL CLUSTER PROFILE
SELECT *
FROM
    clustercore
    NATURAL JOIN clusterinfo
    NATURAL JOIN clusterstats
WHERE
    cid = 'a1b2c3d4e5f678901234567890abcdef'

-- b. LIST RULES FOR A SPECIFIC CLUSTER
SELECT name, pattern, action, description
FROM clusterrule
WHERE
    cid = 'a1b2c3d4e5f678901234567890abcdef'

-- c. GET CLUSTER CREATOR PROFILE
SELECT U.name, U.bio, C.name as cluster_name
FROM
    clusterinfo as I
    JOIN userprofile as U ON I.creator_uid = U.uid
    JOIN clustercore as C ON I.cid = C.cid
WHERE
    C.cid = 'a1b2c3d4e5f678901234567890abcdef'

-- [2]
-- MEMBERSHIP & ROLES
--    CID       : a1b2c3d4e5f678901234567890abcdef
--    UID       : 1234567890abcdef1234567890abcdef

-- a. LIST ALL MODERATORS OF A CLUSTER
SELECT U.uid, U.name, M.assigned_at
FROM
    clustermoderator as M
    JOIN userprofile as U ON M.uid = U.uid
WHERE
    M.cid = 'a1b2c3d4e5f678901234567890abcdef'

-- b. CHECK IF A USER IS A MEMBER OF A CLUSTER
SELECT *
FROM clustermember
WHERE
    uid = '1234567890abcdef1234567890abcdef'
    AND cid = 'a1b2c3d4e5f678901234567890abcdef'

-- c. LIST ALL MEMBERS
SELECT U.name, M.joined_at, M.role
FROM
    clustermember as M
    JOIN userprofile as U ON M.uid = U.uid
WHERE
    M.cid = 'a1b2c3d4e5f678901234567890abcdef'
LIMIT 50

-- [3]
-- ANALYTICS & RANKINGS

-- a. TOP 5 CLUSTERS BY MEMBER COUNT
SELECT name, member_count
FROM clustercore
    NATURAL JOIN clusterstats
ORDER BY member_count DESC
LIMIT 5

-- b. TOP 5 ACTIVE CLUSTERS BY POST COUNT
SELECT C.name, COUNT(P.pid) as post_count
FROM clustercore as C
    JOIN postcore as P ON C.cid = P.cid
GROUP BY
    C.cid
ORDER BY post_count DESC
LIMIT 5

-- c. TOP 5 CATEGORIES BY TOTAL CLUSTERS
SELECT category, count(cid)
FROM clustercore
GROUP BY
    category
ORDER BY count(cid) DESC
LIMIT 5