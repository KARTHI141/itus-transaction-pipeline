# Take-Home Assignment: Client Transaction Data Pipeline

**Itus Capital — Backend Engineer Role**

\---

## Context

You are given a CSV file (`client\_transactions\_may\_oct\_2026.csv`) containing 6 months of client transaction data from a portfolio management platform. The data covers two fund structures — PMS (Portfolio Management Services) and AIF (Alternative Investment Fund) — across multiple distributors.

The data is messy. Expect the kind of problems you would find in real operational data: inconsistent formatting, missing fields, duplicates, and values that don't add up. Part of this exercise is seeing how you handle that.

## What to build

Use Python (Django or FastAPI preferred, but anything that runs is fine) with PostgreSQL.

### 1\. Ingest and clean

Load the CSV into a PostgreSQL database. Write a pipeline that handles the data quality issues — normalise dates, deduplicate transactions, flag or fix the bad rows. **Document every cleaning decision you make and why.**

### 2\. API endpoints

Build three endpoints:

* **Distributor summary:** Number of clients, total invested value, total current value, and net flows (purchases minus redemptions) for the period — grouped by distributor.
* **Client transaction history:** For a given client ID, return their transaction history with a running portfolio value after each transaction.
* **Data quality report:** Return all data quality issues found during ingestion — the row number, the problem, and what was done about it.

### 3\. One business query

The business team asks: *"Which distributors had net negative flows this month, and which of their clients redeemed?"*

Build this as an endpoint or a standalone script that answers the question clearly — the output should be readable by someone who doesn't write code.

### 4\. README

Your README should cover:

* How to set up and run the project (assume the reviewer has Python and PostgreSQL installed)
* Your schema design and why you structured it that way
* Your data cleaning decisions — what you found, what you did, and why
* One thing you would build next if this were going into production
* Anything in the data that surprised you or that you think the business team should know about

## What to submit

A Git repository (GitHub, GitLab, or a zip). The README is part of the evaluation — treat it as a document a colleague would read, not a formality.

## What we're evaluating

* **Data cleaning judgment** — did you make sensible decisions, and can you explain them?
* **Schema design** — does it reflect how the business works?
* **Code quality** — is it readable, not just functional?
* **The business query** — can you translate a plain-English question into working code and present the answer clearly?
* **The README** — can you write clearly about engineering decisions?
* 

