---
name: memory
description: Query and manage project memory to understand past decisions, architectural choices, and coding patterns before making changes. Use this skill when starting new tasks or when you need context about existing code.
---

# Memory Skill

This skill helps you query and understand the project's memory and history before making changes.

## When to Use

Use this skill:
- Before starting any new task or feature implementation
- When modifying existing code to understand past decisions
- When you need context about architectural patterns
- To check for existing solutions or similar implementations

## How to Use

1. **Query Git History**: Check recent commits and changes related to your task
   ```bash
   git log --oneline --all -20
   git log --grep="keyword" --oneline
   ```

2. **Search for Patterns**: Look for similar implementations
   ```bash
   # Use Grep tool to search for relevant patterns
   # Use Glob tool to find related files
   ```

3. **Review CLAUDE.md**: Always check the project guidelines in CLAUDE.md

4. **Check Documentation**: Review any existing documentation in the codebase

## Memory Query Workflow

1. Check CLAUDE.md for project-specific guidelines
2. Search git history for related changes
3. Grep codebase for similar patterns or implementations
4. Review relevant files identified
5. Document your findings before proceeding with changes

## Example Queries

- "What was the last change to the LLM service?"
- "How are MongoDB queries typically structured in this project?"
- "What patterns are used for API endpoints?"
- "Are there existing streaming implementations?"

## Important Notes

- Always query memory BEFORE making changes
- Document your understanding of existing patterns
- Respect established architectural decisions
- Update memory (via commits and docs) when you make significant changes
