# PySpark Curriculum Spec

Track: **PySpark**
Topic key: `pyspark`
ID range: easy 11001–11999, medium 12001–12999, hard 13001–13999
Sample IDs: easy 4501–4503, medium 4601–4603, hard 4701–4703

---

## What This Track Covers

Spark architecture, the PySpark DataFrame API, and real-world optimization. Questions are **conceptual only — no code is executed**. All questions are multiple-choice (4 options). Some include a read-only code snippet to read and reason about.

Question subtypes:
- **`mcq`** — choose the correct answer to a conceptual question
- **`predict_output`** — given a PySpark code snippet, predict what it returns or does
- **`debug`** — given broken code or an error message, identify the fix
- **`optimization`** — given a Spark job setup, choose the best optimization strategy

---

## Difficulty Standards

### Easy

- Single concept, no ambiguity
- Tests recall and understanding of fundamental Spark behavior
- Common in screening rounds and entry-level data engineering interviews

### Medium

- Requires reasoning about Spark internals (partitioning, shuffle, execution plans)
- Involves comparing two or more approaches
- Some questions require reading and interpreting a code snippet or `explain()` output

### Hard

- Multi-factor trade-off reasoning
- Requires understanding of memory model, AQE, or advanced optimization techniques
- May involve multi-select (pick all correct) or ordering questions

---

## Question JSON Schema

```json
{
  "id": 11001,
  "order": 1,
  "topic": "pyspark",
  "type": "mcq",
  "difficulty": "easy",
  "title": "Transformations vs Actions",
  "description": "Which of the following is a Spark **action** (triggers job execution)?",
  "code_snippet": null,
  "options": [
    "df.filter(df.age > 30)",
    "df.select('name', 'age')",
    "df.count()",
    "df.withColumn('senior', df.age > 60)"
  ],
  "correct_option": 2,
  "explanation": "`count()` triggers a full DAG evaluation and returns a Python integer to the driver. `filter()`, `select()`, and `withColumn()` are transformations — they are lazy and only build the logical plan without executing anything.",
  "hints": [
    "Think about which operation causes data to flow from executors back to the driver."
  ],
  "concepts": ["lazy evaluation", "transformations vs actions"]
}
```

### `predict_output` example

```json
{
  "id": 11005,
  "order": 5,
  "topic": "pyspark",
  "type": "predict_output",
  "difficulty": "easy",
  "title": "Chained Filter Output",
  "description": "Given the code snippet below, what does the final call return?",
  "code_snippet": "from pyspark.sql import SparkSession\nspark = SparkSession.builder.getOrCreate()\ndata = [(1, 'Alice', 'US'), (2, 'Bob', 'UK'), (3, 'Carol', 'US')]\ndf = spark.createDataFrame(data, ['id', 'name', 'country'])\nresult = df.filter(df.country == 'US').filter(df.id > 1)\nresult.count()",
  "options": [
    "0",
    "1",
    "2",
    "3"
  ],
  "correct_option": 1,
  "explanation": "The first filter keeps Alice (1, US) and Carol (3, US). The second filter keeps only rows where id > 1, which eliminates Alice. Only Carol remains, so count() returns 1.",
  "hints": ["Apply the filters in sequence to the sample data mentally."],
  "concepts": ["filter chaining", "predict output"]
}
```

### `debug` example

```json
{
  "id": 12001,
  "order": 1,
  "topic": "pyspark",
  "type": "debug",
  "difficulty": "medium",
  "title": "AnalysisException on Column Access",
  "description": "The following code raises `AnalysisException: Resolved attribute(s) ... missing from child`. What is the most likely cause?",
  "code_snippet": "df1 = spark.table('orders')\ndf2 = spark.table('users')\njoined = df1.join(df2, df1.user_id == df2.user_id)\nresult = joined.select(df1.user_id, df2.name, df1.total)\nresult.show()",
  "options": [
    "df1 and df2 have different schemas so join is not allowed",
    "Selecting columns using the original DataFrame references after a join can cause ambiguity — use column name strings or alias the DataFrames instead",
    "spark.table() cannot be used inside a join; use spark.sql() instead",
    "The join condition should use a string column name, not df1.user_id == df2.user_id"
  ],
  "correct_option": 1,
  "explanation": "After a join, column references from the original DataFrames can become ambiguous or invalid. The safest fix is to alias the DataFrames (`df1.alias('o')`) and use the alias in select, or use column name strings. Referencing `df1.user_id` after the join may not resolve correctly depending on the Spark version and join type.",
  "hints": ["What happens to column lineage after a join?"],
  "concepts": ["join column ambiguity", "AnalysisException", "column resolution"]
}
```

### `optimization` example

```json
{
  "id": 13001,
  "order": 1,
  "topic": "pyspark",
  "type": "optimization",
  "difficulty": "hard",
  "title": "Skewed Join Optimization",
  "description": "You have a join between a 500GB fact table and a 50MB dimension table. The fact table has severe data skew on the join key. What is the most effective optimization?",
  "code_snippet": null,
  "options": [
    "Increase spark.sql.shuffle.partitions to 2000",
    "Use a broadcast join to send the 50MB dimension table to all executors",
    "Repartition the fact table by the join key before joining",
    "Enable AQE and set spark.sql.adaptive.skewJoin.skewedPartitionFactor to 2"
  ],
  "correct_option": 1,
  "explanation": "Broadcasting the 50MB dimension table eliminates the shuffle entirely for the join. Since the dimension table fits in memory, every executor gets a local copy and no data movement is needed. This is the single most impactful optimization and also resolves the skew issue since there's no partition-based shuffle. AQE skew join handling (option D) helps but is secondary; broadcast join is strictly better when the smaller side fits in memory.",
  "hints": ["Which approach eliminates the shuffle entirely?"],
  "concepts": ["broadcast join", "data skew", "join optimization"]
}
```

### Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | int | Yes | easy 11001–11999, medium 12001–12999, hard 13001–13999 |
| `order` | int | Yes | 1-based display order |
| `topic` | string | Yes | Always `"pyspark"` |
| `type` | string | Yes | `"mcq"` / `"predict_output"` / `"debug"` / `"optimization"` |
| `difficulty` | string | Yes | `"easy"` / `"medium"` / `"hard"` |
| `title` | string | Yes | ≤ 60 chars |
| `description` | string | Yes | The question text. Markdown supported. |
| `code_snippet` | string \| null | Yes | Code shown read-only above the options. `null` for pure MCQ. Use `\n` for newlines. |
| `options` | array | Yes | Exactly 4 strings. Options A/B/C/D in order. No option should be "All of the above" — avoid it. |
| `correct_option` | int | Yes | 0–3 (index into `options`). |
| `explanation` | string | Yes | Why the correct option is right AND why the others are wrong (briefly). |
| `hints` | array | No | 0–1 hints. A hint should redirect thinking, not reveal the answer. |
| `concepts` | array | No | 1–3 tags. Lowercase. E.g. `"lazy evaluation"`, `"broadcast join"`, `"AQE"`. |

---

## MVP Question Bank — 30 Questions

### Easy (10) — IDs 11001–11010 — Spark Fundamentals

| ID | Title | Type | Topic |
|---|---|---|---|
| 11001 | Transformations vs Actions | mcq | Lazy evaluation — filter/select are transformations; count/collect/show are actions |
| 11002 | What is a DAG? | mcq | Directed Acyclic Graph — how Spark models computation |
| 11003 | RDD vs DataFrame | mcq | DataFrame is schema-aware, optimized by Catalyst; RDD is unstructured |
| 11004 | Spark Driver vs Executor | mcq | Driver: orchestrates. Executor: runs tasks. |
| 11005 | Predict Output of Chained Filters | predict_output | Sequential filter application on small sample data |
| 11006 | When Does .cache() Help? | mcq | Reused DataFrames (e.g., in iterative algorithms); not for one-time scans |
| 11007 | Wide vs Narrow Transformation | mcq | Narrow: map/filter (no shuffle). Wide: groupBy/join (shuffle required). |
| 11008 | Spark SQL — createOrReplaceTempView | mcq | Registers a DataFrame as a temp view for spark.sql() queries |
| 11009 | What Does .persist(StorageLevel.DISK_ONLY) Do? | mcq | Spills to disk, not memory — tradeoff between speed and memory |
| 11010 | Reading a CSV — inferSchema Trade-off | mcq | inferSchema scans entire file for types — slow; explicit schema is faster |

### Medium (10) — IDs 12001–12010 — Internals and Common Patterns

| ID | Title | Type | Topic |
|---|---|---|---|
| 12001 | AnalysisException: Column Ambiguity | debug | Column resolution after join — use aliases |
| 12002 | repartition vs coalesce | mcq | repartition: increases or decreases (with shuffle). coalesce: decrease only (no shuffle). |
| 12003 | What Triggers a Shuffle? | mcq | groupBy, join, distinct, repartition trigger shuffles; filter/select/map do not |
| 12004 | Broadcast Join — When to Use | optimization | Small table (< spark.sql.autoBroadcastJoinThreshold) → broadcast to avoid shuffle |
| 12005 | Reading explain() Output | predict_output | Given a physical plan, identify which operator causes the most data movement |
| 12006 | OOM in Executor — Most Likely Cause | debug | Large groupBy collecting all data to one executor; skewed join key |
| 12007 | RANK vs DENSE_RANK vs ROW_NUMBER | mcq | Difference in gap handling for tied values |
| 12008 | Broadcast Variable vs Accumulator | mcq | Broadcast: read-only large data to executors. Accumulator: write-only counter from executors. |
| 12009 | Schema Inference vs Explicit Schema | mcq | inferSchema requires reading the file twice; explicit schema avoids this |
| 12010 | Kryo vs Java Serialization | mcq | Kryo is faster and produces smaller output; Java serialization is default but slower |

### Hard (10) — IDs 13001–13010 — Optimization and Debugging

| ID | Title | Type | Topic |
|---|---|---|---|
| 13001 | Skewed Join — Best Optimization | optimization | Broadcast the smaller side; if not possible, use salting or AQE skew join |
| 13002 | Memory Config — executor.memory vs memoryOverhead | mcq | memoryOverhead is off-heap (native libs, Python workers); executor.memory is JVM heap |
| 13003 | Dynamic Partition Pruning | mcq | Filter on partitioned column propagates through join to avoid scanning unneeded partitions |
| 13004 | AQE — When Does It Help? | mcq | Skewed joins, sub-optimal join strategies, dynamic partition coalescing |
| 13005 | Identify Bottleneck in explain() | predict_output | Given a full physical plan, identify the SortMergeJoin causing performance issues |
| 13006 | .collect() on 10GB DataFrame | debug | Causes OOM on driver — driver collects ALL rows; use .limit() or write to storage instead |
| 13007 | reduceByKey vs groupByKey | mcq | reduceByKey: combines locally before shuffle (less data movement). groupByKey: all data shuffled then reduced. |
| 13008 | Parquet vs CSV for Production | optimization | Parquet: columnar, compressed, supports predicate pushdown — always prefer for analytics |
| 13009 | End-to-End Slow Job — 3 Optimizations | optimization | Given job description with 3 issues, pick 3 of 4 options (multi-correct) |
| 13010 | Checkpoint vs Cache | mcq | Checkpoint: materializes to reliable storage, breaks lineage. Cache: in memory, lineage preserved. |

---

## Authoring Rules

1. **Always provide exactly 4 options.** No "All of the above", "None of the above", or "A and B". These are weak distractors and make questions too easy or ambiguous.

2. **`correct_option` is 0-indexed.** Option A = 0, B = 1, C = 2, D = 3.

3. **Distractors must be plausible.** Wrong options should represent common misconceptions or partial truths, not obvious nonsense.

4. **`explanation` must address all 4 options.** Explain why the correct answer is right and briefly why each incorrect option is wrong.

5. **`code_snippet` for `predict_output` must be minimal.** No more than 10 lines. Use `spark.createDataFrame()` with inline data so the snippet is self-contained and the output is determinable without running Spark.

6. **`debug` questions must include the error message** in the description or code_snippet. The question should be diagnosable from reading the error + code, not from running it.

7. **`optimization` questions must frame a realistic scenario** with enough context (data sizes, shapes, constraints) to justify the correct choice over the distractors.

8. **Concepts are specific and lowercase:** `"broadcast join"`, `"AQE"`, `"lazy evaluation"`, `"shuffle"`, `"data skew"`. Not `"Spark"`, `"optimization"`, `"performance"` alone.

9. **Avoid questions that require knowing specific Spark version defaults** (e.g., "what is the default value of `spark.sql.shuffle.partitions`?"). These are trivia. Instead test understanding of *why* the configuration exists.

10. **Hard questions may have nuanced correct answers.** The explanation must be thorough enough that a reader understands the reasoning, not just the answer.
