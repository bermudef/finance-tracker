# Finance Tracker Roadmap

## Current Webapp Scope
- Bills and Financial Tools are no longer exposed in the frontend navigation.
- Auto-pay now lives under Recurring Transactions.
- Dashboard cash flow is a current-month running chart (remaining cash vs. cumulative expenses).
- Pending transactions stay visible in Transactions but are excluded from balances, dashboard totals, statements, budgets, health, and net worth.

## Version 1 (Shipped)
- Authentication (register, login, password reset)
- Accounts (checking, savings, high-yield savings, cash)
- Income tracking (salary, bonus, side income, dividends, interest)
- Expense tracking (categorized, search, filters, monthly summaries)
- Credit cards (balance, limit, APR, payment dates)
- Debt tracking (mortgage, auto loan, student loan, credit cards)
- Investments (stocks, ETFs, retirement accounts)
- Savings goals (emergency fund, home purchase, vacation, retirement)
- Dashboard (net worth, cash flow, spending by category, budgets, debt summary, investment summary, savings progress)
- Financial health score (six weighted components, gauge, recommendations)
- Investment analytics (allocation, performance, dividend yield)
- Notifications (bill reminders, budget alerts, savings-goal milestones, UI + unread badge)
- CSV import/export (transactions, accounts, budgets)
- Multi-user support (households, invites, role-based access, UI)
- Recurring transactions (weekly/monthly/yearly, auto-post due items, auto-pay flag)
- Budget rollover (unused amounts carry into next month)
- Net worth trend (12-month monthly series on dashboard)
- Investment benchmark (S&P 500 comparison, 1/3/5/10-year windows)
- Email verification (single-use token, dev banner flow)

## Planned Features

### Plaid Bank Integration
- Automatic transaction import
- Balance sync
- Account categorization

### Mobile Application
- React Native or Capacitor wrapper
- Push notifications
- Offline support
