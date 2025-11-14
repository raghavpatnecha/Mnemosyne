---
name: swarm
description: Orchestrate parallel task execution and coordinate multiple concurrent operations. Use this skill when you have multiple independent tasks that can be executed simultaneously to maximize efficiency.
---

# Swarm Orchestration Skill

This skill helps you orchestrate parallel execution of tasks and coordinate concurrent operations efficiently.

## When to Use

Use this skill:
- When you have multiple independent tasks to execute
- For concurrent file operations (reading, writing, editing multiple files)
- When running multiple bash commands that don't depend on each other
- To parallelize testing, linting, and building operations
- When gathering information from multiple sources simultaneously

## Core Principles

**Always Execute Concurrently**: Batch all independent operations in a single message with multiple tool calls.

**Never Sequential When Parallel is Possible**: If tasks don't depend on each other, run them in parallel.

## Orchestration Patterns

### Pattern 1: Parallel File Operations
When reading/writing multiple unrelated files, use multiple tool calls in one message:
```
Read file A + Read file B + Read file C (in parallel)
```

### Pattern 2: Parallel Information Gathering
```
Grep for pattern A + Glob for files B + Read config C (in parallel)
```

### Pattern 3: Parallel Build Operations
```
Run linter + Run tests + Run build (in parallel when safe)
```

### Pattern 4: Parallel Editing
When editing multiple independent files:
```
Edit file A + Edit file B + Edit file C (in parallel)
```

## Workflow

1. **Identify Independent Tasks**: Break down your work into independent units
2. **Group by Dependencies**: Separate tasks that depend on results from those that don't
3. **Execute Parallel Batch**: Run all independent tasks in a single message
4. **Sequential Follow-up**: Only for tasks that depend on previous results
5. **Verify Results**: Check all parallel operations completed successfully

## Examples

### Good: Parallel Execution
```
# Single message with multiple tool calls:
- Read src/service/LLMService.py
- Read src/service/MongoService.py
- Read src/api/search.py
- Grep for "async" pattern
```

### Bad: Sequential Execution
```
# Multiple messages:
Message 1: Read src/service/LLMService.py
Message 2: Read src/service/MongoService.py
Message 3: Read src/api/search.py
Message 4: Grep for "async" pattern
```

## Task Coordination Rules

1. **Maximize Parallelism**: Always prefer parallel execution
2. **Batch Operations**: Combine multiple tool calls in single messages
3. **Clear Dependencies**: Only execute sequentially when results are needed
4. **Verify Success**: Check all parallel operations before proceeding
5. **Error Handling**: If any parallel task fails, handle appropriately

## Common Swarm Patterns for Mnemosyne

### Pattern: Service Analysis
```
Read LLMService.py + Read MongoService.py + Read MnemsoyneService.py (parallel)
```

### Pattern: Multi-file Refactoring
```
Edit file1.py + Edit file2.py + Edit file3.py (parallel)
```

### Pattern: Comprehensive Testing
```
Run pytest + Run lint + Check types (parallel when independent)
```

## Important Notes

- Use swarm orchestration for ALL tasks with multiple independent operations
- Always identify what can run in parallel vs what must be sequential
- Batch tool calls in single messages for maximum efficiency
- Document your orchestration strategy for complex tasks
