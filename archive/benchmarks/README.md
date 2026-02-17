# Database Benchmarking & Fragmentation Strategy

This directory contains benchmarks comparing **Monolithic** vs **Fragmented** database architectures for the Cluster social platform.

## Key Findings (Trade-offs)

> [!IMPORTANT]
> **Write Penalty**: Fragmentation introduces a significantly higher cost for insertions (approx **4x-6x slower**). This is due to the overhead of multiple transaction management and index updates across separate tables.

> [!TIP]
> **Read Optimization**: The strategy pays off in specific **high-frequency read paths** like Feed Construction and Author Resolution, where scanning thin "Core" tables is significantly faster.

## Benchmarks

### 1. User Entity (`benchmark_user.ipynb`)
*   **Strategy**: `UserAuth` (Secrets) + `UserProfile` (Public).
*   **Write Performance**: ~6x slower for Fragmented.
*   **Read Performance**: **Feed Author Resolution** (UID -> Name/Image) is faster because `UserProfile` is thinner than `UserMonolith`, allowing more rows per memory page.

### 2. Post Entity (`benchmark_post.ipynb`)
*   **Strategy**: `PostCore` (Feed Skeleton) + `PostContent` (Blob) + `PostStats` (Volatile).
*   **Write Performance**: significantly slower for Fragmented.
*   **Read Performance**: **Feed Scan** (Cluster -> Top 20) is faster because `PostCore` effectively acts as a covering index, avoiding the need to load heavy `content` text for the initial scan.

### 3. Cluster & Comment Entities
Similar fragmentation strategies are applied to separate volatile stats (writes) from static core data (reads).

## Running the Benchmarks
Each notebook generates a temporary SQLite database in `temp/db/` and prints execution times.

```bash
# Example
python archive/benchmarks/benchmark_user.py
```
