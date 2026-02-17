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


## Real-World Scale Analysis: Is it worth it?

The benchmarks show a **~4x-6x Write Penalty** but a **~2x Read Speedup**. Is this trade-off roughly profitable?

### The "90-9-1" Rule (or 100:1 Read-to-Write Ratio)
In social media, for every **1 post created**, there are typically **100+ views** (Feed loads, Profile visits).

Let's assume:
*   **Write Cost (Monolith)**: 10ms
*   **Write Cost (Fragmented)**: 50ms (5x penalty) → **+40ms cost**
*   **Read Cost (Monolith)**: 50ms
*   **Read Cost (Fragmented)**: 25ms (2x speedup) → **-25ms saved**

### The Calculation
If a user creates **1 Post** and views their feed **10 times** in a day:

1.  **Write "Loss"**: $1 \text{ post} \times 40\text{ms} = \mathbf{40\text{ms lost}}$
2.  **Read "Gain"**: $10 \text{ views} \times 25\text{ms} = \mathbf{250\text{ms gained}}$

### Net Result
**210ms saved per user, per day.**
At 100,000 users, this fragmentation strategy saves **~5.8 hours of cumulative database processing time per day**, despite the slower writes. This frees up significant CPU/IO resources for the system to handle concurrent users.

