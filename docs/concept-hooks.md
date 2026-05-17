# Concept Hooks by Track

A comprehensive set of conceptual interview hooks per track, ranked easy → hard within each section.
Goal: full concept coverage, not tricky framing.

---

## SQL

### Filtering & Basic Selection

1. `WHERE` vs `HAVING` — which filters before grouping, which after?
2. `IS NULL` vs `= NULL` — why does one always return false?
3. `BETWEEN x AND y` — is the range inclusive or exclusive?
4. `IN (...)` vs multiple `OR` conditions — are they always equivalent?
5. `NOT IN` with a subquery containing NULLs — why can it return zero rows?
6. `DISTINCT` vs `GROUP BY` — when do they produce the same result, and when don't they?
7. `LIKE '%term%'` vs `LIKE 'term%'` — why does one kill index usage?
8. `LIKE` vs `ILIKE` — when does case sensitivity bite you?

### Aggregation

9. `COUNT(*)` vs `COUNT(col)` vs `COUNT(DISTINCT col)` — what does each actually count?
10. Which aggregate functions ignore NULLs, and which don't?
11. `GROUP BY 1, 2` vs `GROUP BY col_a, col_b` — same thing, or footgun?
12. Can you reference an alias from `SELECT` inside `WHERE`? Inside `HAVING`?
13. `SUM` vs `COUNT` on a boolean/flag column — which is more readable?
14. `MIN`/`MAX` on strings — what does it return?

### Joins

15. `INNER JOIN` vs `LEFT JOIN` — when do they produce identical results?
16. `LEFT JOIN` vs `RIGHT JOIN` — is one ever better than the other?
17. `FULL OUTER JOIN` — what problem does it solve that a `UNION` of left/right joins also solves (and when are they not the same)?
18. `CROSS JOIN` — when would you deliberately use a cartesian product?
19. Self join — what class of problems requires joining a table to itself?
20. Joining on inequality (`a.start < b.end`) — what does the result set look like?
21. `JOIN ... ON` vs `JOIN ... USING` — when can you use `USING` and what does it suppress?
22. Multiple joins — does join order affect the result? Does it affect performance?
23. Filtering in `ON` vs filtering in `WHERE` on a `LEFT JOIN` — are they equivalent?

### Subqueries

24. Scalar subquery in `SELECT` — when is this useful vs a join?
25. Correlated vs non-correlated subquery — what's the execution difference?
26. `IN` vs `EXISTS` — when does the choice matter for performance or correctness?
27. Subquery in `FROM` (derived table) vs `JOIN` — are they interchangeable?
28. `ANY` / `ALL` with a subquery — what do they replace?

### NULL Handling

29. `COALESCE(a, b, c)` vs `NULLIF(a, b)` — what does each solve?
30. NULLs in `ORDER BY` — where do they sort by default? How do you control it?
31. NULL on the join key — does a NULL match another NULL in a join?
32. `CASE WHEN col IS NULL` vs `COALESCE(col, default)` — when to use each?
33. NULL in `GROUP BY` — do NULLs group together?

### CASE & Conditional Logic

34. Simple `CASE col WHEN val` vs searched `CASE WHEN condition` — when must you use the searched form?
35. `CASE` inside `COUNT` or `SUM` — how do you count only rows matching a condition?
36. `CASE` in `GROUP BY` — how do you bucket rows into custom groups?
37. `CASE` vs `IIF` / `IF` / `DECODE` — which is standard SQL?

### String Functions

38. `TRIM` vs `LTRIM` vs `RTRIM` — what does each remove?
39. `SUBSTRING` vs `LEFT` / `RIGHT` — when to use each?
40. `CONCAT` vs `||` — portability and NULL behavior differences?
41. `REPLACE` vs `REGEXP_REPLACE` — when is the extra power worth the cost?
42. `SPLIT_PART` / `STRING_SPLIT` — extracting the nth segment from a delimited string

### Date & Time

43. `DATE_TRUNC('month', ts)` vs `EXTRACT(month FROM ts)` — what type does each return?
44. Adding 1 month vs adding 30 days — why are they different?
45. `CURRENT_DATE` vs `NOW()` vs `CURRENT_TIMESTAMP` — what's the difference?
46. Timezone-aware vs naive timestamps — what breaks when you mix them?
47. Calculating age or tenure — why is date subtraction tricky near month/year boundaries?

### Set Operations

48. `UNION` vs `UNION ALL` — performance difference and when deduplication matters
49. `INTERSECT` vs an `INNER JOIN` on the same columns — are they equivalent?
50. `EXCEPT` / `MINUS` vs `NOT IN` / `NOT EXISTS` — NULL edge cases
51. Column count and type matching in `UNION` — what happens on mismatch?

### Window Functions

52. `ROW_NUMBER()` vs `RANK()` vs `DENSE_RANK()` — handling ties
53. `PARTITION BY` with no `ORDER BY` — what do window functions return?
54. `PARTITION BY` with no columns (empty partition) — what's the window?
55. `LAG(col, n)` vs `LEAD(col, n)` — computing period-over-period change
56. `FIRST_VALUE` / `LAST_VALUE` vs `MIN` / `MAX` OVER — when do they differ?
57. `NTILE(n)` — what's it useful for and what's the gotcha when rows don't divide evenly?
58. `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` vs `RANGE BETWEEN` — when do they diverge?
59. Can you nest window functions inside each other?
60. Window function vs `GROUP BY` — when does a window function let you keep detail rows that `GROUP BY` collapses?

### CTEs

61. CTE vs subquery — readability aside, is there a performance difference?
62. Multiple CTEs — can a later CTE reference an earlier one?
63. Recursive CTE — what two parts does it need, and what's the base case?
64. Recursive CTE vs self-join for hierarchical data — when to prefer each?
65. `WITH MATERIALIZED` vs `WITH NOT MATERIALIZED` — optimizer hint for CTE evaluation

### Advanced Aggregation

66. `ROLLUP` vs `CUBE` vs `GROUPING SETS` — what subtotals does each produce?
67. `GROUPING()` function — how do you distinguish a NULL group-by key from a subtotal row?
68. `FILTER (WHERE condition)` on an aggregate vs `CASE WHEN` — which is cleaner and where is it supported?
69. `STRING_AGG` / `LISTAGG` / `GROUP_CONCAT` — aggregating rows into a comma-separated list
70. `ARRAY_AGG` vs `STRING_AGG` — when do you want an array vs a string?

### De-duplication & Top-N Patterns

71. De-duplicating with `ROW_NUMBER() = 1` vs `DISTINCT` vs `GROUP BY` — when must you use the window approach?
72. Top-N per group — why can't you just `WHERE rank <= 3` without a subquery or CTE?
73. Latest record per entity — the canonical pattern and its variants

### Execution & Performance

74. SQL logical execution order — `FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT` — why aliases from `SELECT` aren't visible in `WHERE`
75. Sargable predicates — what makes `YEAR(date_col) = 2024` worse than `date_col BETWEEN ...`?
76. `EXISTS` vs `COUNT(*) > 0` — early termination and when it matters
77. Index on a function — when do you need a functional index?
78. `LIMIT` with `ORDER BY` — does the engine optimize by stopping early?

### Hard / Specialist Patterns

79. Gaps and islands — detecting consecutive sequences (e.g., contiguous active days)
80. Running total with window function vs self-join — why the self-join is O(n²)
81. Slowly changing dimension (SCD Type 2) query — finding the record valid at a given point in time
82. Pivot with `CASE WHEN` vs native `PIVOT` / `CROSSTAB` — portability vs readability
83. Lateral join / `CROSS JOIN LATERAL` — when a correlated subquery in `FROM` is unavoidable
84. `QUALIFY` (Snowflake/BigQuery) — filtering on window function results without a CTE
85. Sessionization — assigning a session ID to events based on inactivity gaps
86. Calendar spine join — filling in missing dates in a time series
87. JSON column extraction (`->`, `->>`, `JSON_VALUE`, `JSON_QUERY`) — querying semi-structured data
88. `UNNEST` / `FLATTEN` — going from array column to rows and back

### Missing Topics To Add

- Ordered-set percentile / median functions — when to use `PERCENTILE_CONT`, `PERCENTILE_DISC`, or warehouse-specific median helpers instead of hand-rolled ranking.
- As-of joins — point-in-time matching between facts and the most recent prior dimension or event row.
- Approximate distinct counting — when `APPROX_COUNT_DISTINCT` / HyperLogLog-style estimates are the right tradeoff.
- Reconciliation and data-quality query patterns — row-count checks, anti-joins, mismatch audits, and source-vs-target validation queries.

---

## PySpark

### Core Execution Model

1. Transformation vs action — what's the difference and why does it matter?
2. Lazy evaluation — when does Spark actually run code?
3. DAG — what does Spark build before executing, and why?
4. Stage vs task vs job — what triggers a new stage?
5. Narrow vs wide transformation — which one causes a shuffle?
6. `collect()` vs `show()` vs `take()` — when is each dangerous?

### RDD vs DataFrame vs Dataset

7. RDD vs DataFrame — what does the Catalyst optimizer get you that RDDs don't?
8. DataFrame vs Dataset — when does typed safety matter in practice?
9. Can you mix RDD and DataFrame operations? What's the cost?
10. `rdd.map()` vs `df.withColumn()` — why prefer the DataFrame API?

### Schema & Types

11. `inferSchema=True` on CSV — what types does Spark default to, and what goes wrong?
12. `StringType` defaults — why does Spark choose String when inference is off?
13. What happens when you read a CSV with a mismatched schema?
14. Schema evolution in Parquet — what does Spark do when columns are added or removed?
15. `StructType` vs DDL string for schema definition — any practical difference?

### Partitioning

16. `repartition(n)` vs `coalesce(n)` — when to use each, and what's the shuffle cost?
17. How does Spark decide the default partition count?
18. Too few partitions vs too many — what are the failure modes of each?
19. `partitionBy()` on write — how is this different from `repartition()`?
20. Data skew — how do you detect it and what are the fix strategies?

### Shuffles & Performance

21. Which operations trigger a shuffle? (groupBy, join, distinct, repartition…)
22. Broadcast join vs sort-merge join — when does Spark choose each, and how do you force it?
23. `spark.sql.shuffle.partitions` — what's the default and when is it wrong?
24. Predicate pushdown — what is it and when does Spark apply it automatically?
25. Projection pushdown — how does reading Parquet differ from reading CSV on column selection?

### Caching & Persistence

26. `cache()` vs `persist()` — what's the difference?
27. `MEMORY_ONLY` vs `MEMORY_AND_DISK` storage level — what happens on eviction?
28. When should you cache a DataFrame, and when does caching hurt?
29. Does caching survive across Spark sessions?
30. `unpersist()` — when do you need to call it explicitly?

### Aggregation & GroupBy

31. `groupBy().agg()` vs `groupBy().count()` — functional difference?
32. What type does `groupBy().sum("col")` return for an integer column?
33. `countDistinct()` vs `approx_count_distinct()` — when is approximate good enough?
34. `collect_list()` vs `collect_set()` — ordering and deduplication guarantees?
35. Pivot in PySpark — what happens to the schema when pivot columns are dynamic?

### Window Functions

36. `Window.partitionBy()` vs `Window.partitionBy().orderBy()` — what changes?
37. `RANK` vs `DENSE_RANK` vs `ROW_NUMBER` in a PySpark window — handling ties
38. `lag()` / `lead()` — what's returned for the first/last row in a partition?
39. Running sum with `Window.rowsBetween(Window.unboundedPreceding, Window.currentRow)` — frame semantics
40. `rangeBetween` vs `rowsBetween` — when do they diverge?

### Joins

41. Inner, left, right, full, semi, anti — when would you use a semi or anti join?
42. `F.broadcast()` hint — what's the default broadcast threshold and how do you tune it?
43. Joining on nullable keys — does a NULL row match another NULL in PySpark joins?
44. Cross join — does PySpark require explicit opt-in?
45. Cartesian product explosion — how do you detect it before it crashes your job?

### UDFs & Built-ins

46. Python UDF vs Pandas UDF (vectorized UDF) — performance difference and why
47. Built-in function vs UDF — when is there no built-in and you must write one?
48. UDF return type — what happens if your function returns a type Spark didn't expect?
49. `F.expr()` — when is passing a SQL string into a DataFrame API useful?
50. `selectExpr()` vs `select(F.expr(...))` — same result?

### I/O & File Formats

51. `write.mode("overwrite")` vs `write.mode("append")` — what's the atomicity guarantee?
52. Reading a Parquet partition with `spark.read.parquet("path/date=2024-01-01")` — what happens to the partition column?
53. `coalesce(1)` before writing — when is this useful and when is it a trap?
54. Delta Lake `MERGE INTO` — how does it differ from overwrite + append?
55. `spark.read.option("mergeSchema", True)` — what does it do, what can it break?

### Debugging & Error Handling

56. `AnalysisException` — most common causes?
57. `OutOfMemoryError` in the executor — spill to disk vs fatal crash, how do you tell?
58. Task failure vs stage failure vs job failure — recovery behavior?
59. `explain()` — what does the physical plan tell you that the logical plan doesn't?
60. Speculative execution — what is it, when does Spark use it, and when does it backfire?

### Missing Topics To Add

- `checkpoint()` vs `cache()` — lineage truncation, fault recovery, and when cache is insufficient.
- Storage levels in `persist()` — `MEMORY_ONLY`, `MEMORY_AND_DISK`, serialized variants, and the tradeoffs of each.
- Spark UI diagnosis — reading stages, tasks, shuffle read/write, skew, spill, and GC symptoms.
- Task failure vs executor failure vs driver failure — how Spark retries, recovers, or aborts.
- Stateful streaming operations — state stores, `mapGroupsWithState`, watermark interaction, and memory growth risks.
- Nested schema evolution — adding/removing nested fields in structs and arrays without breaking downstream jobs.

---

## Pandas

### Data Structures

1. `Series` vs `DataFrame` — when does a single-column DataFrame behave differently from a Series?
2. `Index` in pandas — what is it storing and why can it be duplicated?
3. `RangeIndex` vs custom index — when does the default index cause bugs?
4. `MultiIndex` — what's it for and what operations does it unlock?
5. `dtype` per column vs a single numpy dtype — why does pandas store columns separately?

### Selection & Indexing

6. `df[col]` vs `df[[col]]` — why does one return a Series and the other a DataFrame?
7. `.loc` vs `.iloc` — label-based vs position-based, and what happens when the index is integers?
8. Boolean mask vs `.query()` — performance and readability tradeoffs?
9. `df.loc[mask, col]` — why is this the safe assignment pattern?
10. Chained indexing (`df[mask][col] = val`) — why does it sometimes not write back?
11. `SettingWithCopyWarning` — what does it mean and when is it a real bug vs noise?

### Cleaning & Missings

12. `NaN` vs `None` vs `pd.NA` vs `np.nan` — which works where?
13. `dropna()` vs `fillna()` — when to drop vs impute?
14. `dropna(how='any')` vs `dropna(how='all')` — difference?
15. `fillna(method='ffill')` vs `fillna(value)` — when is forward-fill correct?
16. `isna()` vs `isnull()` — same thing?
17. `df.replace(0, NaN)` — does this modify in-place?

### Aggregation & GroupBy

18. `groupby().agg()` vs `groupby().transform()` — when does each preserve the original shape?
19. `groupby().apply()` — what's the performance cost vs vectorized alternatives?
20. `groupby(dropna=False)` — what changes when you want to group NaN keys?
21. Named aggregation with `agg(new_col=('col', 'func'))` — when is this cleaner than renaming after?
22. `groupby().size()` vs `groupby().count()` — why do they differ on NaN rows?
23. `as_index=False` in groupby — what does it do to the result shape?

### Reshaping

24. `melt()` vs `stack()` — when to use each for wide-to-long reshaping?
25. `pivot()` vs `pivot_table()` — what does `pivot_table` add when values aren't unique?
26. `pivot_table()` vs `crosstab()` — when does crosstab simplify the call?
27. `unstack()` — what level does it move and what happens to NaNs in sparse combinations?
28. `explode()` — what problem does it solve on list-valued columns?

### Merging & Combining

29. `merge()` vs `join()` — key difference in how they align data?
30. `merge(how='left')` vs `merge(how='inner')` — duplicated keys: what does the row count become?
31. `merge()` on multiple columns vs a single composite key — any difference in result?
32. `concat(axis=0)` vs `concat(axis=1)` — alignment behavior when indexes differ?
33. `merge_asof()` — what problem does it solve that a regular merge can't?
34. `combine_first()` — what does it do and when is it useful?

### Apply & Vectorization

35. `apply(func, axis=1)` — why is it slow and what's the faster alternative for most use cases?
36. `map()` vs `apply()` on a Series — when does each apply?
37. `applymap()` / `map()` on a DataFrame — element-wise vs column-wise?
38. Vectorized string operation via `.str` accessor vs a loop — what's the performance difference?
39. `np.where()` vs `df['col'].apply(lambda...)` for conditional column creation — which to prefer?
40. `assign()` for method chaining — what does it enable that direct assignment doesn't?

### Sorting & Ranking

41. `sort_values()` vs `sort_index()` — what does each sort on?
42. `rank(method='average')` vs `method='min'` vs `method='dense'` — handling ties
43. `nlargest(n)` vs `sort_values().head(n)` — any difference?
44. `sort_values(na_position='last')` — where do NaNs go by default?

### Time Series

45. `pd.to_datetime()` — what happens when the format is inconsistent across rows?
46. `.dt` accessor — what operations does it unlock on a datetime column?
47. `resample()` vs `groupby(pd.Grouper(freq='M'))` — same result?
48. `rolling(n)` — what does the window look like for the first n-1 rows?
49. `shift(n)` — how do you compute a period-over-period change without a join?
50. `tz_localize()` vs `tz_convert()` — when to use each?

### Memory & Performance

51. `df.dtypes` — why does `object` dtype signal a potential memory problem?
52. `category` dtype — what's the storage win and what operations does it break?
53. `int64` vs `Int64` (nullable integer) — what does the capital-I version give you?
54. Reading a CSV with `usecols` and `dtype` — why specify both vs letting pandas infer?
55. `copy()` vs view — when does pandas return a view vs a copy, and why does it matter?
56. Chunked reading with `chunksize` — when is this the right pattern?

### Advanced Patterns

57. `pipe()` — how does it fit into a method chain?
58. `pd.cut()` vs `pd.qcut()` — equal-width bins vs equal-frequency bins
59. `value_counts(normalize=True)` — what does it compute?
60. `idxmax()` / `idxmin()` — what does it return on a DataFrame vs a Series?
61. `duplicated(keep='first')` vs `keep='last'` vs `keep=False` — what rows are flagged?
62. `df.eval()` — when is it faster than direct column arithmetic?

### Missing Topics To Add

- Merge cardinality validation — `validate='one_to_one'`, `one_to_many`, and catching accidental fan-out early.
- `merge_asof()` in more depth — nearest-key joins for event streams and slowly changing reference data.
- `explode()` workflows — unnesting list-like columns and rebuilding aggregates safely afterward.
- Chained assignment and `SettingWithCopyWarning` — diagnosing when writes silently hit a copy instead of the source frame.
- MultiIndex construction and alignment semantics — building hierarchical indexes intentionally and understanding index alignment in arithmetic and joins.

---

## Python (Data Interview)

### Core Data Structures

1. `list` vs `tuple` — when does immutability matter beyond "convention"?
2. `dict` vs `set` — when is a set the right structure for a lookup problem?
3. `defaultdict` vs `dict.get(key, default)` vs `setdefault()` — when to use each?
4. `Counter` — what does it give you over a manual frequency dict?
5. `deque` vs `list` for a queue — what's the time complexity difference on popleft?
6. `OrderedDict` vs plain `dict` in Python 3.7+ — is there still a use case?

### Strings

7. String immutability — why does repeated `+=` in a loop have poor performance?
8. `join()` vs `+=` for building strings — when does it matter?
9. `split()` vs `partition()` — what does partition preserve that split loses?
10. `strip()` vs `lstrip()` vs `rstrip()` — what does strip remove (not just whitespace)?
11. `startswith()` and `endswith()` with a tuple argument — what does this check?
12. String slicing with step: `s[::-1]` — what does a negative step do?
13. `ord()` / `chr()` — when do character-to-integer conversions appear in data problems?

### Iteration & Comprehensions

14. List comprehension vs `map()` vs a for loop — when to use each?
15. Generator expression vs list comprehension — when does lazy evaluation save memory?
16. `zip()` vs `enumerate()` — which to reach for when?
17. `zip()` on unequal-length iterables — what does it do? What does `zip_longest` do instead?
18. Nested list comprehension — reading order (`for x in outer for y in x`)?
19. `any()` and `all()` — short-circuit evaluation: when does it matter?
20. `itertools.chain()` — what does it let you avoid?

### Sorting & Searching

21. `sorted()` vs `.sort()` — which is in-place? What does each return?
22. `key=` argument in sort — how do you sort a list of dicts by a field?
23. `bisect.bisect_left()` vs `bisect_right()` — insertion point behavior on duplicates
24. Two-pointer technique — what class of array problems does it solve in O(n)?
25. Binary search on a sorted list — why is a linear scan sometimes still correct?

### Hash-Based Patterns

26. Two-sum with a hash map — why O(n) vs O(n²) for the nested-loop approach?
27. Complement search — detecting if a target − element has been seen
28. Frequency counting with `Counter` — finding the most common element in one line
29. Deduplication preserving order — why a `set` alone doesn't work; `dict.fromkeys()` pattern
30. Grouping by a key — `defaultdict(list)` as a poor-man's groupby

### Sliding Window & Intervals

31. Fixed-size sliding window — what state do you add on the right and remove on the left?
32. Variable-size sliding window — how do you decide when to shrink the window?
33. Interval merging — sort by start, then greedily extend: what's the invariant?
34. Overlapping intervals — detecting if any two overlap without checking all pairs
35. Minimum window substring — why do you need two pointers and a frequency map?

### Recursion & Iteration

36. Recursive vs iterative solution — when does recursion hit Python's default stack limit (~1000)?
37. Memoization with `@functools.lru_cache` — what does it cache and when does it break?
38. Tail recursion — does Python optimize it? What should you do instead?
39. Backtracking — what's the base case and how do you "undo" a choice?
40. Tree traversal (pre/in/post-order) — what does each ordering reveal?

### Greedy & Dynamic Programming

41. Greedy algorithm — when is a locally optimal choice globally optimal?
42. Greedy vs DP — how do you tell which a problem requires?
43. DP with a 1D array vs 2D table — when can you compress space?
44. `functools.reduce()` — what does it replace and when is it less readable?

### Functional & Pythonic Patterns

45. `lambda` vs a named function — when is a lambda a bad idea?
46. `*args` vs `**kwargs` — how does argument unpacking interact with them?
47. Unpacking: `a, *rest = lst` — what does `*rest` capture?
48. `zip(lst, lst[1:])` — the idiomatic way to iterate over adjacent pairs
49. `collections.namedtuple` vs `dataclass` — when to use each for a simple value object?
50. Context manager (`with` statement) — what do `__enter__` and `__exit__` give you?

### Complexity & Data Reasoning

51. O(n log n) vs O(n) — when is sorting a list the right first step even though it's not O(n)?
52. Hash table worst-case O(n) — when do collisions degrade a dict lookup?
53. Space vs time tradeoff — storing a frequency map to avoid a second pass
54. In-place vs new allocation — when does the problem require modifying the input vs returning new?
55. Flat list vs nested structure — converting between them (flatten, unnest)

### Data-Specific Python (No Pandas)

56. Reading a CSV with `csv.DictReader` — when do you skip the pandas import?
57. Parsing JSON with `json.loads()` — handling nested keys and missing fields safely
58. `datetime.strptime()` vs `datetime.fromisoformat()` — format flexibility tradeoffs
59. Aggregating without pandas: group-by with `defaultdict`, sum, mean, count
60. Detecting and handling duplicates in a list of dicts — which key uniquely identifies a record?

### Missing Topics To Add

- Heaps and priority queues — when `heapq` is the right structure for top-k, streaming median, and scheduler-style problems.
- BFS / DFS on graphs and grids — traversal patterns, visited-state handling, and shortest-path-vs-reachability distinctions.
- Union-Find / Disjoint Set Union — connectivity, component counting, and cycle detection with path compression.
- Trie / prefix tree — prefix lookup, autocomplete-style search, and word-search pruning.
- Topological sort — dependency ordering in DAGs and cycle detection.
- Shortest path algorithms — especially Dijkstra for weighted graphs.
- Monotonic stack and monotonic queue — next-greater, histogram, and sliding-window-maximum patterns.

---

## Data Engineering

### Fundamentals

1. ETL vs ELT — what changed architecturally to make ELT viable?
2. Data warehouse vs data lake vs lakehouse — what problem does each architecture solve?
3. OLTP vs OLAP — why do you typically not run analytics on the production database?
4. Batch processing vs stream processing — when is each appropriate?
5. Micro-batch vs true streaming — where does Spark Structured Streaming sit?
6. Push vs pull ingestion — which is better for rate-limited APIs?

### File Formats & Storage

7. Parquet vs CSV vs Avro vs ORC — what drives the choice for each?
8. Row-oriented vs columnar storage — which is faster for aggregation queries and why?
9. Snappy vs GZIP compression in Parquet — speed vs ratio tradeoff?
10. Splittable vs non-splittable formats — why does GZIP-compressed CSV hurt parallelism?
11. Small file problem — what causes it and what are the remediation strategies?
12. File compaction — when and how do you merge small files without downtime?

### Partitioning & Pruning

13. Partition by date vs by customer_id — how does query pattern drive the choice?
14. Over-partitioning — what happens when you partition on a high-cardinality column?
15. Partition pruning — how does the engine skip partitions it doesn't need?
16. Bucketing — how does it differ from partitioning and when does it help joins?
17. Z-ordering / clustering — what does it optimize beyond partition pruning?

### Pipeline Reliability

18. Idempotency — what makes a pipeline safe to re-run without duplicating data?
19. At-most-once vs at-least-once vs exactly-once delivery — which is hardest to achieve and why?
20. Deterministic vs non-deterministic pipelines — why does `CURRENT_TIMESTAMP` in a transform break reruns?
21. Checkpoint vs savepoint in streaming — what does each persist and when do you use each?
22. Dead letter queue — what goes there and what do you do with it?
23. Backfill vs rerun — what's the difference and which risks are higher for each?

### Schema & Data Contracts

24. Schema-on-read vs schema-on-write — what do you give up with each approach?
25. Schema evolution — backward, forward, and full compatibility: which changes break which consumers?
26. Adding a nullable column vs a non-nullable column — why is one a breaking change?
27. Data contracts — what should a contract specify beyond just column names and types?
28. Schema registry — what problem does it solve in a streaming architecture?
29. Breaking schema change in production — how do you migrate without downtime?

### Data Quality

30. Completeness vs accuracy vs freshness vs consistency — which is hardest to measure?
31. Null rate assertion vs row count assertion — which catches more classes of bugs?
32. Referential integrity check — how do you detect orphaned foreign keys in a data lake?
33. Data freshness SLA — how do you alert when a partition is late without a native scheduler?
34. Deduplication at ingest vs at query time — tradeoffs?
35. Silent data loss — how do you detect that rows are missing rather than wrong?

### Change Data Capture (CDC)

36. Log-based CDC vs query-based CDC — performance and completeness tradeoffs?
37. `INSERTED` vs `UPDATED` vs `DELETED` event types — how does each affect the downstream model?
38. Initial load + CDC — why is the sequencing between them critical?
39. DDL changes in CDC — what happens when the source table schema changes mid-stream?
40. Debezium vs Fivetran-style CDC — what does each abstract away?

### Orchestration

41. DAG vs linear pipeline — what does a DAG enable that sequential steps don't?
42. Task dependency: upstream failure — what are the options? (fail, skip, trigger rule)
43. Fan-out / fan-in patterns — what coordination problem does fan-in introduce?
44. Idempotent DAG runs — why is `execution_date` preferred over `now()` in Airflow tasks?
45. Retry vs backfill — when does retrying a failed task not help?
46. SLA vs SLO in a pipeline context — what triggers an alert vs a page?
47. Sensor vs trigger — when do you poll for upstream readiness vs subscribe to an event?

### Stream Processing

48. Event time vs processing time — why does the distinction matter for aggregations?
49. Watermark — what does it tell the engine and how does it affect late-arriving data?
50. Late data — what are the three options: drop, include, or upsert?
51. Session window vs tumbling window vs sliding window — which use case fits each?
52. Stateful streaming — what state is maintained per key and what's the memory risk?
53. Exactly-once in Kafka — what guarantees does the producer need and the consumer need separately?

### Data Lineage & Observability

54. Column-level lineage vs table-level lineage — what does each help you diagnose?
55. Data observability vs data monitoring — what's the difference?
56. Impact analysis — given a source table change, how do you find all affected downstream models?
57. Freshness anomaly vs volume anomaly vs distribution anomaly — different detection methods?
58. OpenLineage / Marquez — what standard do they implement and what tools emit it?

### Performance & Cost

59. Materialization vs live query — when does pre-aggregating save more than it costs in storage?
60. Hot vs cold storage tiering — what triggers moving data from hot to cold and what queries break?
61. Query cost in BigQuery / Snowflake — what drives bytes scanned, and how do partitions and clustering help?
62. Incremental model vs full refresh — when does incrementality introduce correctness risk?

### Missing Topics To Add

- Backpressure and flow control — what happens when downstream consumers cannot keep up with incoming volume.
- Privacy and compliance architecture — PII handling, deletion workflows, access boundaries, and auditability.
- Data contract operationalization — ownership, enforcement, versioning, and rollout mechanics beyond the contract definition itself.
- Warehouse cost modeling — how storage, compute, scan volume, and query shape drive spend.
- Incident containment patterns — limiting blast radius, isolating bad data, and staged recovery during active failures.

---

## Data Modeling

### Normalization

1. 1NF vs 2NF vs 3NF — what violation does each normal form eliminate?
2. BCNF vs 3NF — what case does BCNF fix that 3NF misses?
3. When is denormalization correct? — the case for OLAP vs OLTP schemas
4. Repeating groups — what makes a column violate 1NF even when stored in a single cell?
5. Partial dependency — what does it mean and which normal form addresses it?
6. Transitive dependency — why does `city → country` in a table that's keyed by `order_id` matter?

### Star vs Snowflake

7. Star schema vs snowflake schema — join count vs storage tradeoff
8. When does a snowflake schema add value beyond normalization purity?
9. Conformed dimensions — what makes a dimension "conformed" and why does it enable cross-subject-area reports?
10. Factless fact table — what business question does it answer?
11. Aggregate fact table — how does it relate to the base fact table and what query does it accelerate?

### Fact Tables

12. Transaction fact vs periodic snapshot fact vs accumulating snapshot fact — what process does each model?
13. Grain definition — what does "one row per X" actually mean and why is it the most important design decision?
14. Grain consistency — what breaks if you mix grains in a single fact table?
15. Additive vs semi-additive vs non-additive measures — which aggregate safely across all dimensions?
16. Degenerate dimension — what is it and when does it belong in the fact table rather than a dimension?
17. Junk dimension — what problem does it solve for low-cardinality flags?

### Dimension Tables

18. Surrogate key vs natural key — why do warehouses generate surrogate keys even when the source has a unique ID?
19. SCD Type 1 vs Type 2 vs Type 3 — what history is preserved by each?
20. SCD Type 2 — what columns does a Type 2 row need to support point-in-time queries?
21. SCD Type 4 (mini-dimension) — what problem does it solve that Type 2 can't handle efficiently?
22. SCD Type 6 — what's the hybrid it combines and what query pattern does it optimize?
23. Late-arriving dimension member — what do you do when a fact row arrives before the dimension row it references?
24. Late-arriving fact — how does an accumulating snapshot handle a process step that completes out of order?
25. Role-playing dimension — what's it called and how do you physically implement it?

### Relationships & Keys

26. Many-to-many relationship — why can't a fact table directly model it without a bridge table?
27. Bridge table — what's its grain and how does it affect measure aggregation (fan trap)?
28. Referential integrity — enforced vs informational constraints: what does each mean in a cloud warehouse?
29. Natural key from multiple sources — how do you handle identity resolution when the same entity has different IDs across systems?
30. Composite key vs surrogate key — when does a composite key create maintenance problems?

### Hierarchies

31. Ragged hierarchy — what's an example and why does a fixed-depth model break?
32. Closure table — how does it represent a hierarchy and what query does it make efficient?
33. Parent-child vs level-based hierarchy storage — tradeoffs?
34. Unbalanced hierarchy — how does it differ from a ragged hierarchy?
35. Bridge table for a many-to-many hierarchy (e.g., employee with multiple cost centers) — how do you weight allocation?

### Advanced Design Patterns

36. Heterogeneous supertype/subtype — when a single fact table holds events of fundamentally different shapes
37. Multi-currency fact table — where does the exchange rate live and at what grain?
38. Event-sourced model vs snapshot model — how do you rebuild current state from events?
39. Activity schema / wide event table — what it solves vs what it breaks for BI tools
40. One Big Table (OBT) vs normalized mart — when does flattening everything make sense?

### dbt & Modern Modeling

41. Staging → intermediate → mart layering — what belongs in each layer?
42. `view` vs `table` vs `incremental` vs `ephemeral` materialization — when to choose each?
43. Incremental model `unique_key` — what happens on a duplicate key: merge, error, or append?
44. `insert_overwrite` vs `merge` incremental strategy — which is safer for late-arriving data?
45. `ref()` vs `source()` in dbt — what does each resolve and why does the distinction matter for lineage?
46. dbt tests: `not_null` + `unique` + `relationships` — what gap do custom tests fill?
47. dbt snapshots — how do they implement SCD Type 2 and what column do they add?
48. Semantic layer — what does it prevent that a mart layer alone doesn't?

### Performance & Storage

49. Partitioning a fact table by date vs by customer segment — how does query pattern determine the right key?
50. Clustering / Z-ordering on a dimension key — when does it help vs when does partitioning suffice?
51. Pre-aggregated summary table vs live rollup — freshness vs cost tradeoff?
52. Wide table scalability — at what point does a 500-column OBT become a problem?
53. Materialized view vs dbt incremental model — which the warehouse controls vs which you control?

### Missing Topics To Add

- Bi-temporal modeling — valid time vs system time and when both timelines matter.
- Semantic-layer governance — centrally defined metrics, dimensions, and access rules above the mart layer.
- Semi-additive metric design in more depth — balances, inventory, and snapshot measures across time.
- More hierarchy design variants — ragged, recursive, alternate-rollup, and cross-hierarchy reporting patterns.

---

## Statistics

### Descriptive Statistics

1. Mean vs median — when does the median better represent "typical"?
2. Mode — when is it the most useful central tendency measure?
3. Variance vs standard deviation — why report standard deviation if variance is easier to compute?
4. Population variance vs sample variance — why divide by n−1 instead of n?
5. IQR vs standard deviation for spread — which is more robust to outliers?
6. Skewness — positive vs negative: which tail is longer?
7. Kurtosis — what does excess kurtosis above or below 0 tell you about tail behavior?
8. Coefficient of variation — when is it more useful than standard deviation alone?

### Probability

9. Independent events vs mutually exclusive events — can two events be both?
10. Conditional probability P(A|B) — how does it differ from P(A and B)?
11. Bayes' theorem — when does the base rate dominate the likelihood?
12. Law of total probability — when do you sum across a partition of the sample space?
13. Binomial vs Bernoulli distribution — what's the relationship?
14. Poisson distribution — what process does it model and what's the key assumption?
15. Geometric distribution — what question does it answer?
16. Uniform distribution — discrete vs continuous: what's different?
17. Expected value of a function of a random variable — E[g(X)] ≠ g(E[X]) in general: when does it matter?

### Distributions

18. Normal distribution — what does the 68-95-99.7 rule say?
19. When is a distribution approximately normal? (CLT)
20. Log-normal distribution — what real-world quantities are log-normally distributed and why?
21. Heavy-tailed vs thin-tailed — why does the distinction matter for risk modeling?
22. Exponential distribution — what's the memoryless property and what does it model?
23. t-distribution vs normal — when and why do you use t instead of z?
24. Chi-squared distribution — what is it and where does it appear?
25. F-distribution — what test uses it?

### Hypothesis Testing

26. Null hypothesis vs alternative hypothesis — what does "failing to reject H₀" mean?
27. One-tailed vs two-tailed test — when does directionality of the hypothesis matter?
28. p-value — what is it, and what does p < 0.05 not mean?
29. Type I error (α) vs Type II error (β) — false positive vs false negative in testing context
30. Statistical power (1−β) — what increases it and what's the cost?
31. Effect size — why can a result be statistically significant but practically meaningless?
32. Sample size calculation — what four inputs determine the required n?
33. z-test vs t-test vs chi-squared test vs ANOVA — when to use each?
34. Paired vs unpaired t-test — what makes a test paired?
35. Non-parametric test (Mann-Whitney, Wilcoxon) — when do you reach for these instead of t-tests?

### A/B Testing & Experimentation

36. Randomization unit — why user-level vs session-level vs page-level randomization gives different results?
37. Novelty effect — how does it inflate short-term experiment metrics?
38. Network effects / SUTVA violation — when does a user's treatment affect the control group?
39. Multiple comparisons problem — why does running 20 tests at α=0.05 almost guarantee a false positive?
40. Bonferroni correction vs Benjamini-Hochberg (FDR) — when is each appropriate?
41. Sequential testing / peeking — why is stopping an experiment early when you see significance wrong?
42. Minimum detectable effect (MDE) — what is it and how does it relate to sample size?
43. Metric sensitivity — why does median revenue per user behave differently from mean revenue per user in an A/B test?
44. Guardrail metric vs primary metric — what's the role of each?
45. CUPED / variance reduction — what pre-experiment covariate does it use and what does it buy you?

### Confidence Intervals & Estimation

46. Confidence interval — what does "95% confidence" actually mean?
47. CI vs credible interval — frequentist vs Bayesian interpretation
48. Margin of error — what determines its width?
49. Bootstrap confidence interval — when do you use it instead of parametric CI?
50. Point estimate vs interval estimate — when is an interval not enough?

### Correlation & Regression

51. Correlation vs causation — what structural condition (confounding, reverse causation) breaks causal claims?
52. Pearson vs Spearman correlation — when does rank-based correlation matter?
53. Correlation of 0 — does it mean no relationship?
54. Linear regression assumptions — LINE: linearity, independence, normality of residuals, equal variance (homoscedasticity)
55. R² vs adjusted R² — what does adding a useless predictor do to each?
56. Multicollinearity — how does it affect coefficient estimates vs predictions?
57. Overfitting — what's the bias-variance tradeoff in plain terms?
58. Regularization (Ridge vs Lasso) — what does each shrink and how do they handle correlated features?
59. Logistic regression — what does the output represent and why can't you use linear regression for a binary outcome?
60. Odds ratio vs relative risk — when can they diverge significantly?

### Sampling

61. Simple random sampling vs stratified vs cluster sampling — when does stratification reduce variance?
62. Sampling bias — how does a non-representative sample break inference?
63. Central Limit Theorem — what does it say about sample means and why does it matter for testing?
64. Law of large numbers — what does it guarantee and what does it not guarantee?
65. Survivorship bias — a classic example and how it distorts conclusions

### Bayesian Thinking

66. Prior vs likelihood vs posterior — how does Bayes update belief?
67. Conjugate prior — what makes one convenient and what's a common example?
68. Bayesian vs frequentist approach to A/B testing — what question does each answer?
69. Posterior predictive distribution — what does it let you do that a point estimate doesn't?
70. Sensitivity to prior — when does the prior dominate and when does the data dominate?

### Applied / Data Interview Contexts

71. Metrics spike or drop — systematic debugging framework: data issue vs product change vs external factor
72. Average vs median for business metrics — when does a product manager's "average order value" mislead?
73. Simpson's paradox — what makes an aggregate trend reverse within subgroups?
74. Berkson's bias — why hospital-based studies can show negative correlation between diseases that are actually independent
75. Regression to the mean — why the "Sports Illustrated cover jinx" has a statistical explanation
76. Selection bias in funnel analysis — why the users who reach step 3 are not representative of users at step 1
77. Survivorship bias in cohort analysis — why "users retained at day 30" look better-behaved than they were
78. Goodhart's Law — when a measure becomes a target, why does it cease to be a good measure?

### Missing Topics To Add

- Mann-Whitney and permutation tests — non-parametric alternatives when parametric assumptions fail.
- Kruskal-Wallis and two-way ANOVA — multi-group and multi-factor inference beyond one-way ANOVA.
- Logistic regression — binary outcomes, log-odds interpretation, and odds ratios.
- Diagnostic plots and assumption checks — QQ plots, residual plots, normality tests, and heteroscedasticity checks.
- Missing-data mechanisms — MCAR, MAR, MNAR, and how each changes analysis strategy.
- Causal DAGs — confounding, colliders, and adjustment logic for causal reasoning.
