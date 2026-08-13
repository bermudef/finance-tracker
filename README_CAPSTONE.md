# AI Capstone: Finance Tracker

## Project Title

Finance Tracker: AI-Assisted Personal Finance Dashboard and Analytics Web App

## Problem Statement

Many people can record transactions, but still struggle to understand their real month-to-month financial position. Inconsistent treatment of pending transactions, unclear cash-flow visualizations, fragmented debt tracking, and poor recurring-payment visibility make it hard to answer simple questions like:

- How much cash do I actually have left this month?
- How much have I really spent so far?
- How heavy is my debt burden relative to my income?
- Which recurring charges are automatic and which are manual?

This project solves that problem by building a web application that keeps balances, statements, debt, recurring payments, and dashboard analytics consistent across the product.

## Successful Outcome

A successful solution would:

- show accurate balances and statements
- exclude pending transactions from official totals while still displaying them in the transaction feed
- present debt, mortgage, and recurring-payment data consistently across pages
- provide a clear current-month cash-flow visualization
- support realistic demo data for multiple household profiles

## AI Tools Used

- AI coding assistant for architecture review, prompt iteration, implementation, refactoring, and debugging
- Terminal/database tools for verifying live PostgreSQL data and API behavior
- Git/GitHub workflow for version control and final delivery

## Why These Tools Were Selected

- The AI assistant was useful for iterative prompt-based software development, code review, UI refinement, and cross-file consistency checks.
- Live database and API verification were necessary to confirm that fixes were not only correct in code, but also correct in runtime behavior.

## Prompt Development and Iteration

The project was built through iterative prompting rather than a single one-shot instruction. Representative prompt patterns included:

1. Initial diagnosis
- identify why statements, charts, and transactions were inconsistent
- inspect frontend and backend data flow before changing code

2. Refinement and correction
- align dashboard, statement, and health-score calculations
- define a consistent rule for pending transactions
- correct debt-burden logic so status matched actual DTI bands

3. Product-level iteration
- remove unnecessary frontend sections (Tools and Bills)
- move auto-pay into Recurring Transactions
- improve chart semantics and transaction status UX
- update seed data and documentation so the app matched the intended product scope

## Results

The final system now includes:

- consistent pending-transaction behavior across balances, dashboard, statements, budgets, health, and net worth
- current-month running cash-flow chart showing remaining cash and cumulative expenses
- mortgage included in debt tracking and debt summaries
- recurring transactions with auto-pay support
- improved transaction status visibility (`posted`, `pending`, `cleared`)
- updated seed data with more realistic insurance values and mortgage debt for the Parker profile
- frontend cleanup removing Bills and Tools from the shipped webapp scope

## Output / Evidence

Evidence of the workflow and results includes:

- backend tests covering dashboard, reports, health, notifications, accounts, tools, and recurring logic
- frontend typechecking across the updated UI
- seeded demo households with realistic financial profiles
- commit history in the GitHub repository documenting incremental changes

## Reflection

This project showed that the most valuable use of AI was not just code generation, but structured iteration:

- define the problem clearly
- inspect the real data flow first
- change one rule at a time
- verify the result with tests and live data

The biggest lesson was that small inconsistencies in sign conventions, date bounds, status handling, and UI wording can make a finance app feel untrustworthy even when most of the code is technically correct. AI was most effective when used as a collaborator for repeated diagnosis, implementation, and verification cycles rather than as a shortcut.

## Future Improvements

- add full migrations for every schema change automatically in the development workflow
- reintroduce advanced tools only when their scope clearly fits the core product
- expand automated tests around visual/reporting semantics and seeded demo expectations
- add user-facing reporting exports and deeper analytics once the core financial model is stable
