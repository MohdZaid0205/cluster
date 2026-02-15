# Database Benchmarking & Fragmentation Strategy

This directory contains benchmarks comparing **Monolithic** vs **Fragmented** database architectures for the Cluster social platform.

## Goal
To demonstrate that vertically fragmenting entities based on access patterns (Hot vs Cold data) and write frequency improves performance for critical paths like Feed Construction, Login, and Discovery.

## Benchmarks

### 1. User Entity (`benchmark_user.ipynb`)
**Strategy**: Split into `UserAuth` and `UserProfile`.
*   **Why**: Authentication only needs `email`, `password`, `role`. Profile data (`bio`, `image`) is larger and less frequently accessed during auth checks.
*   **Result**: Faster login queries, smaller index footprint for auth table.

### 2. Cluster Entity (`benchmark_cluster.ipynb`)
**Strategy**: Split into `ClusterCore`, `ClusterInfo`, `ClusterStats`.
*   **Why**:
    *   **Core**: minimal data (`name`, `topic`, `img`) for list/discovery views.
    *   **Info**: heavy text (`description`, `rules`) loaded only on detail view.
    *   **Stats**: (`member_count`) extremely high write frequency. Separating this prevents locking the Core/Info tables during updates.

### 3. Post Entity (`benchmark_post.ipynb`)
**Strategy**: Split into `PostCore`, `PostContent`, `PostStats`.
*   **Why**:
    *   **Feeds** need to scan thousands of rows to find the "latest 20". Keeping `PostCore` thin (just IDs and timestamps) packs more rows into memory pages, speeding up scans.
    *   **Content** is fetched only for the visible posts.
    *   **Stats** (Likes/Views) are volatile and updated constantly.

### 4. Comment Entity (`benchmark_comment.ipynb`)
**Strategy**: Split into `CommentCore`, `CommentContent`, `CommentStats`.
*   **Why**:
    *   **Tree Traversal**: Reconstructing a comment thread requires sorting by `pid` and `created_at`. A thin `CommentCore` table allows faster sorting and pagination.
    *   **Content**: Loaded lazily or on demand.

## Running the Benchmarks
Each notebook generates a temporary SQLite database in `temp/db/` and prints execution times for Monolithic vs Fragmented operations.

```bash
# Example
python archive/benchmarks/benchmark_user.py
```
