-- TASK 4 SUBMISSION FOR 15 QUERRIES

-- [LEVEL 1]

-- LIST ALL MUSIC OR ART CLUSTERS THAT ARE PUBLIC
SELECT *
FROM clustercore
WHERE
    category IN ('Music', 'Art')
    AND is_private = false

-- LIST ALL AVAILABLE CATEOGRY AND COUNT CLUSTER OF THIS CATEGORY
SELECT category, count(cid)
FROM clustercore
GROUP BY category
ORDER BY count(cid) DESC

-- [LEVEL 2]

-- LIST MODERATORS FOR EACH CLUSTER
SELECT moderator, moderates
FROM (
        SELECT cid, name as moderates
        FROM clustercore
    )
    NATURAL JOIN (
        SELECT cid, name as moderator
        FROM clustermoderator
            NATURAL JOIN userprofile
    )

-- LIST CLUSTERS WITH HIGHEST MODERATORS TO MEMBERS RATIO
SELECT
    *,
    n_members / n_moderators as mem_to_mod_ratio
FROM clustercore
    NATURAL JOIN (
        SELECT cid, count(uid) as n_members
        FROM clustermember
        GROUP BY
            cid
    )
    NATURAL JOIN (
        SELECT cid, count(uid) as n_moderators
        FROM clustermoderator
        GROUP BY
            cid
    )
ORDER BY mem_to_mod_ratio ASC

-- LIST TOP 5 USERS BASED ON POST COUNT
SELECT *
FROM userprofile
    NATURAL JOIN (
        SELECT uid, count(pid)
        FROM postcore
        WHERE
            uid IN (
                SELECT uid
                FROM userauth
                WHERE
                    is_verified = true
            )
        GROUP BY
            uid
        ORDER BY count(pid) DESC
        LIMIT 5
    )

-- SELECT LAST POST WAS IN TAHT SPECIFIC CLUSTER FOR EACH CLUSTER
-- ALSO SHOW THAT LAST POST IN THAT CLUSTER
SELECT *
FROM postcontent
    NATURAL JOIN (
        SELECT name as cluster_name, pid, MAX(created_at) as recent
        FROM clustercore
            Natural JOIN postcore
        GROUP BY
            cid
    )
ORDER BY recent DESC

-- LIST CATEGORIES OF CLUSTER BASED ON NUMBER OF PARTICIPATIONS
SELECT category, sum(n_members)
FROM clustercore
    NATURAL JOIN (
        SELECT cid, count(uid) as n_members
        FROM clustermember
        GROUP BY
            cid
    )
GROUP BY
    category
ORDER BY sum(n_members) DESC

-- [LEVEL 3]

-- SELECT POSTS FOR TRENDING PAGE DEPENDING UPON ENGAGEMENT
-- ENGAGEMENT IS DEFINED AS: LIKES + 3*REACTIONS + DISLIKES / N_DAYS
SELECT *
FROM postcontent
    NATURAL JOIN (
        SELECT pid, (
                likes + dislikes + 3 * total_reactions
            ) as engagement
        FROM poststats
            NATURAL JOIN (
                SELECT pid, count(R.uid) as total_reactions
                FROM postcore as P
                    INNER JOIN postreaction as R USING (pid)
                GROUP BY
                    pid
            )
    )
ORDER BY engagement DESC

-- LIST ALL USERS WHO HAVE NEVER CREATED A POST NOR A CCOMMENT (ANTIJOINT)
SELECT *
FROM userprofile
WHERE
    uid IN (
        SELECT X.uid
        FROM (
                SELECT DISTINCT
                    U.uid as uid
                FROM userprofile as U
                    LEFT JOIN postcore as P ON (U.uid = P.uid)
                WHERE
                    P.uid IS NULL
            ) as X
            INNER JOIN (
                SELECT DISTINCT
                    U.uid as uid
                FROM userprofile as U
                    LEFT JOIN commentcore as C ON (U.uid = C.uid)
                WHERE
                    C.uid IS NULL
            ) as Y ON (X.uid = Y.uid)
    )

-- [LEVEL 4]

-- FIND CLUSTERS CREATED BY UNVERIFIED USERS
SELECT C.name, C.category, U.email
FROM
    clustercore as C
    JOIN clusterinfo as I ON C.cid = I.cid
    JOIN userauth as U ON I.creator_uid = U.uid
WHERE
    U.is_verified = false

-- AVERAGE LIKES PER POST FOR EACH CLUSTER CATEGORY
SELECT category, AVG(likes) as avg_likes
FROM clustercore
    NATURAL JOIN postcore
    NATURAL JOIN poststats
GROUP BY
    category
ORDER BY avg_likes DESC

-- IDENTIFY POTENTIAL MODERATORS (MEMBERS WITH HIGH COMMENT COUNT IN CLUSTER)
SELECT
    C.name as cluster,
    U.name as user,
    count(CM.mid) as comments_made
FROM
    clustercore as C
    JOIN postcore as P ON C.cid = P.cid
    JOIN commentcore as CM ON P.pid = CM.pid
    JOIN userprofile as U ON CM.uid = U.uid
    LEFT JOIN clustermoderator as M ON (
        C.cid = M.cid
        AND U.uid = M.uid
    )
WHERE
    M.uid IS NULL
GROUP BY
    C.cid,
    U.uid
ORDER BY comments_made DESC
LIMIT 10

-- [LEVEL 5]

-- FIND "CONNECTORS": USERS MEMBERS OF CLUSTERS IN >3 DIFFERENT CATEGORIES
SELECT U.name, count(DISTINCT C.category) as distinct_categories
FROM
    userprofile as U
    JOIN clustermember as M ON U.uid = M.uid
    JOIN clustercore as C ON M.cid = C.cid
GROUP BY
    U.uid
HAVING
    distinct_categories > 3
ORDER BY distinct_categories DESC

-- DETECT VIRAL POSTS (SHARED VIA WINDOWS MORE THAN 10 TIMES)
SELECT P.content, U.name as author, count(W.wid) as share_count
FROM
    (postcontent NATURAL JOIN postcore) as P
    JOIN postcontent as PC ON P.pid = PC.pid

    JOIN userprofile as U ON P.uid = U.uid
    JOIN
window as W ON P.pid = W.origin_pid
GROUP BY
    P.pid
HAVING
    share_count > 1
ORDER BY share_count DESC

-- RETENTION ANALYSIS: USERS JOINED >1 YEAR AGO BUT ACTIVE (POSTED) IN LAST 7 DAYS
SELECT U.name, U.created_at as joined, MAX(P.created_at) as last_post
FROM userprofile as U
    JOIN postcore as P ON U.uid = P.uid
WHERE
    U.created_at < date('now', '-1 year')
    AND P.created_at > date('now', '-10 days')
GROUP BY
    U.uid