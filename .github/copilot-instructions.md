# Agent Workflow and Coding Standards

## Purpose

This document guides agents (human or AI) working on software to follow these steps to ensure consistency, maintainability, and clear communication.

## Coding Standards

1. **Simplicity**: Write the simplest code that solves the problem, prioritising readability and maintainability over cleverness.

2. **Intent**: Clearly express the intent of code using meaningful names for variables, functions, and classes to convey their purpose. No hidden control flow.

3. **Comments**: Use comments to explain _why_ the code exists, not what it does. Assume the reader can understand the code itself.

4. **Error Handling**: Use error handling to manage exceptions and unexpected behaviour, ensuring that errors are caught and communicated clearly. Fail fast rather than swallowing errors silently.

5. **Pragmatism**: Use design patterns only when necessary, preferring straightforward solutions over complex abstractions.

6. **Task Decomposition**: Break work into small, manageable pieces, seeking feedback early and often.

7. **Abstractions**: Encapsulate complexity in logical, focused abstractions. Each abstraction should be understandable in isolation, and allow some reading of the code to black box that part and understand the logic around it.

8. **Codebase**: Look at some of the other local files and keep the style of those files consistent when adding code.

9. **File Size**: If a file exceeds 500 lines, consider splitting it into separate modules. This is not a hard and fast rule, just something to think about if you see a file this size.

10. **Communication**: Keep the user informed of progress and blockers. Always document questions and assumptions.

11. **Testing**: Tests should be at the public interface level.

12. **Realistic Data**: Avoid testing implementation details. The best tests are those that test critical logic. Think of tests as the developer's specification into the project.

## Remember

Never guess requirements—ask for clarification if anything is ambiguous. Be as pedantic as you need to be.

Remember, you're the software engineer, not the product manager. It is up to you to find the ambiguity, and the user to resolve it.
