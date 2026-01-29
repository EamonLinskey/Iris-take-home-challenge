# Take-Home Challenge: RFP Answer Generation Tool

## Overview

A 3 to 5-hour AI-assisted development challenge for senior/staff backend/fullstack engineers that evaluates how candidates use AI tools, their architectural thinking, documentation quality, and ability to explain their decisions.

## Candidate Instructions

### RFP Answer Generator Challenge

**Time Limit:** 3-5 hours (honor system - we trust you)

**Required Tools:** AI-assisted development (Cursor, Claude Code, Copilot, etc.)

### Setup and Submission

1. Fork this repo
2. Do the work (see Challenge Specification below)
3. Add @noahpeden, @emirbirlik-dev, @Muhammad-Talha-Hashmi, and @mrkhalil6 to it
4. Email noah@heyiris.ai, khalil@heyiris.ai, emir@heyiris.ai, talha@heyiris.ai and gadi@heyiris.ai when you've finished with the github repo link

## Challenge Specification

### The Problem

Build a simplified RFP (Request for Proposal) Answer Generator - a tool that takes questions from an RFP document and generates answers using a knowledge base of company documents.

**Time Limit:** 3-5 Hours

Candidates must use AI-assisted development tools (Cursor, Claude Code, GitHub Copilot, etc.) and document their AI collaboration throughout.

## Requirements

### Core Functionality (Must Complete)

- Document Ingestion API
- Question Answering API
- Basic RAG Implementation
- Delightful Frontend allowing a user to upload documents, an RFP, and a place to review answers to the RFP from the system you build.

### Documentation Requirements (Critical)

- Purpose
- System design decisions and why
- How AI tools were used, what worked/didn't
- What you'd do differently with more time
- API documentation (or OpenAPI spec)

### Stretch Goals (If Time Permits)

- Async processing with Celery/Redis
- Vector embeddings for semantic search
- Batch question processing
- Answer caching
- Confidence scoring logic
- Frontend/Backend Testing

## Tips
- Our stack is Django Rest Framework on the backend and Next.js on the Frontend, but if you're more comfortable in a different stack feel free to use it!
- Prioritize working core features over stretch goals
- Document as you go, not at the end
- It's okay to not finish everything
- We care more about your thinking than your typing
