# AgentOS

### Multi-Agent AI Research & Software Engineering Platform

AgentOS is a production-style AI platform that combines **RAG, LangChain, LangGraph, MCP, AI Agents, Vector Databases, and LLM evaluation** to help developers and teams analyze technical knowledge, GitHub repositories, documentation, and codebases.

Instead of relying on a single LLM response, AgentOS uses a **multi-agent workflow** where different AI agents handle planning, retrieval, repository analysis, reasoning, verification, and report generation.

The system can understand a complex request, break it into smaller tasks, retrieve relevant information from a knowledge base or GitHub repository, use MCP tools when required, verify the findings, and generate a structured final report with supporting evidence.

---

## What Problem Does AgentOS Solve?

Developers often need to understand large repositories and technical documentation before making decisions.

For example:

- How is this repository structured?
- Where is authentication implemented?
- Which APIs are connected to the database?
- Are there inconsistencies between documentation and code?
- What could be improved in the architecture?
- What are the potential security or maintainability concerns?
- Which files are responsible for a particular feature?

Finding these answers manually requires searching through documentation, source code, GitHub issues, commits, and multiple files.

AgentOS brings these sources together into a single AI-powered workspace.

---

# How AgentOS Works

A typical request follows this flow:

```text
                    User
                      │
                      ▼
               User Question
                      │
                      ▼
              LangGraph Planner
                      │
              ┌───────┴────────┐
              ▼                ▼
         RAG Agent        GitHub Agent
              │                │
              ▼                ▼
       Vector Database      MCP Tools
              │                │
              └───────┬────────┘
                      ▼
                Analyst Agent
                      │
                      ▼
               Verifier Agent
                      │
                      ▼
                Report Agent
                      │
                      ▼
          Final Answer + Evidence
```

The important part is that the system does not blindly ask an LLM to answer the entire question.

The request is **planned, executed, verified, and then synthesized**.

---

# Example User Request

A user can connect a GitHub repository and ask:

> Analyze this repository architecture, identify how authentication works, find the APIs responsible for user management, check the relevant documentation, and generate a technical report with source references.

AgentOS can then:

```text
1. Planner Agent
   └── Breaks request into multiple tasks

2. GitHub Agent
   └── Uses GitHub MCP to inspect repository

3. RAG Agent
   └── Searches indexed documentation

4. Code Analysis
   └── Examines relevant source files

5. Analyst Agent
   └── Combines findings

6. Verifier Agent
   └── Checks findings against evidence

7. Report Agent
   └── Generates final technical report
```

The user receives a structured answer instead of a simple chatbot response.

---

# Core AI Capabilities

## 1. RAG — Retrieval Augmented Generation

AgentOS provides a complete RAG pipeline for technical documents and codebases.

```text
Documents / Code
       │
       ▼
Document Processing
       │
       ▼
Chunking + Metadata
       │
       ▼
Embeddings
       │
       ▼
Vector Database
       │
       ▼
Hybrid Retrieval
       │
       ▼
Reranking
       │
       ▼
Relevant Context
       │
       ▼
LLM
```

The retrieval system can combine:

- Semantic vector search
- BM25 keyword search
- Reciprocal Rank Fusion
- Reranking
- Metadata filtering
- Source citations

This allows AgentOS to retrieve relevant information before generating an answer.

---

# 2. Vector Database

AgentOS uses a vector database to store embeddings of:

- Technical documentation
- PDFs
- Markdown files
- Repository documentation
- Source code
- Architecture documents

The initial implementation uses **Qdrant**.

Example:

```text
User Question
      │
      ▼
Embedding
      │
      ▼
Qdrant Search
      │
      ▼
Relevant Chunks
      │
      ▼
Reranker
      │
      ▼
LLM Context
```

Metadata can be used to filter results by:

```text
workspace
repository
document
file
language
branch
access scope
```

---

# 3. LangChain

LangChain is used as the application framework for LLM-powered components.

It handles areas such as:

- LLM integration
- Prompt management
- Structured outputs
- Retrievers
- Tool integration
- Document processing
- Agent components

LangChain provides the building blocks used by the AgentOS AI system.

---

# 4. LangGraph

LangGraph is responsible for **agent orchestration and workflow management**.

Instead of having one large agent, AgentOS uses specialized agents.

### Planner Agent

Understands the user's request and creates a plan.

### RAG Agent

Searches the knowledge base and retrieves relevant evidence.

### GitHub Agent

Uses GitHub MCP tools to inspect repositories.

### Code Analysis Agent

Analyzes relevant source code and relationships.

### Analyst Agent

Combines information from multiple agents.

### Verifier Agent

Checks whether important findings are supported by evidence.

### Report Agent

Creates the final structured response.

---

# 5. MCP — Model Context Protocol

MCP provides a standardized way for agents to interact with external tools.

AgentOS can integrate the official GitHub MCP Server for repository operations.

Example tools can include:

```text
Search repository
Read repository files
Search code
Inspect commits
Inspect issues
Inspect pull requests
Retrieve repository metadata
```

The LangGraph agent decides when a tool is required.

Example:

```text
User:
"Find where JWT authentication is implemented."

        ↓

Planner Agent

        ↓

GitHub Agent

        ↓

GitHub MCP

        ↓

Search Repository

        ↓

Relevant Files

        ↓

Code Analysis

        ↓

Verified Answer
```

AgentOS can also contain custom MCP servers for its own capabilities.

For example:

```text
Knowledge Base MCP
Code Analysis MCP
Report Generation MCP
```

This demonstrates both **MCP integration** and **custom tool development**.

---

# 6. Multi-Agent Collaboration

The agents are not independent chatbots.

They share a workflow state managed by LangGraph.

Example state:

```python
{
    "user_query": "...",
    "plan": [...],
    "retrieved_context": [...],
    "github_results": [...],
    "analysis": [...],
    "verification": [...],
    "final_report": "..."
}
```

This allows agents to build on the work performed by previous agents.

---

# 7. Agent Memory

AgentOS maintains multiple types of memory.

### Conversation Memory

Stores relevant conversation context.

### Knowledge Memory

Stores information that can be retrieved from the vector database.

### Execution Memory

Stores workflow state, tool results, and checkpoints.

This allows long-running workflows to be paused and resumed.

---

# 8. Human-in-the-Loop

Some operations should not be executed automatically.

For example:

```text
Agent wants to create GitHub issue

        ↓

Prepare proposed issue

        ↓

Ask user for approval

        ↓

User approves

        ↓

Execute MCP tool
```

This provides a safer architecture for agents that can perform write operations.

---

# 9. Verification

A major part of AgentOS is preventing unsupported answers.

The Verifier Agent checks:

```text
Claim
  ↓
Supporting Evidence?
  ↓
Source Available?
  ↓
Consistent with Retrieved Context?
  ↓
Verified / Needs Review
```

If evidence is insufficient, the system can explicitly indicate that the information could not be verified from the available sources.

---

# 10. Example Use Cases

### Repository Architecture Analysis

> Analyze the architecture of this repository and explain how the frontend, backend, database, and APIs interact.

### Authentication Analysis

> Find how authentication is implemented and identify the files responsible for login, token generation, and authorization.

### Documentation vs Code

> Compare the API documentation with the actual implementation and identify inconsistencies.

### Bug Investigation

> Analyze these logs, find the relevant code, and identify possible causes of the API failure.

### Technical Research

> Search my uploaded documentation and compare the different technologies used in the project.

### Codebase Understanding

> Explain how the payment workflow works from the frontend request to database persistence.

### Technical Report

> Analyze the repository and generate a complete architecture report with evidence from the source code.

---

# 11. Final Output

The final answer generated by AgentOS can contain:

```text
Technical Analysis Report

1. Summary

2. Architecture

3. Key Components

4. Findings

5. Evidence

6. Source References

7. Potential Issues

8. Recommendations

9. Agent Execution Summary
```

The UI can also show the execution trace:

```text
✓ Planner Agent
✓ RAG Agent
✓ GitHub MCP
✓ Code Analysis Agent
✓ Verifier Agent
✓ Report Agent
```

This makes the AI workflow visible instead of hiding everything behind a chatbot response.

---

# 12. Evaluation & Observability

AgentOS will measure the quality of the AI system instead of only demonstrating that it works.

### RAG Metrics

- Faithfulness
- Answer Relevancy
- Context Precision
- Context Recall

### Agent Metrics

- Tool-call success rate
- Agent execution time
- Workflow completion rate
- Retry count

### LLM Metrics

- Token usage
- Latency
- Estimated cost
- Model usage

### Retrieval Metrics

- Retrieval precision
- Retrieval recall
- Reranking effectiveness

Ragas can be used for evaluation and Langfuse can be used for LLM and agent observability.

---

# 13. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js + TypeScript |
| Backend | Python + FastAPI |
| LLM Framework | LangChain |
| Agent Orchestration | LangGraph |
| Agent Tools | MCP |
| LLM | Gemini / configurable provider |
| Vector Database | Qdrant |
| Database | PostgreSQL |
| Retrieval | Hybrid Search + RRF + Reranking |
| Embeddings | Configurable embedding model |
| Evaluation | Ragas |
| Observability | Langfuse |
| Background Jobs | Redis + Celery |
| Deployment | Docker |
| GitHub Integration | GitHub MCP Server |

---

# 14. High-Level Architecture

```text
                         ┌─────────────────────┐
                         │      Next.js UI     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │       Backend       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     LangGraph       │
                         │   Agent Workflow    │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌────────────┐        ┌────────────┐        ┌────────────┐
       │ RAG Agent  │        │ GitHub     │        │ Research   │
       │            │        │ Agent      │        │ Agent      │
       └─────┬──────┘        └─────┬──────┘        └────────────┘
             │                     │
             ▼                     ▼
       ┌────────────┐       ┌──────────────┐
       │   Qdrant   │       │ GitHub MCP   │
       │ Vector DB  │       │   Server     │
       └────────────┘       └──────────────┘
             │
             └─────────────────┬─────────────────┐
                               ▼                 ▼
                        ┌─────────────┐   ┌─────────────┐
                        │ PostgreSQL  │   │   Redis     │
                        └─────────────┘   └─────────────┘

                               │
                               ▼
                     ┌──────────────────┐
                     │ Verifier + Report│
                     │      Agents      │
                     └────────┬─────────┘
                              │
                              ▼
                     Final Answer + Sources
```

---

# 15. Project Goals

The project is designed to demonstrate practical AI engineering skills across:

- RAG architecture
- Vector databases
- Hybrid retrieval
- Reranking
- LangChain
- LangGraph
- Multi-agent systems
- MCP
- Tool calling
- Agent memory
- Human-in-the-loop workflows
- LLM evaluation
- Observability
- FastAPI
- PostgreSQL
- Docker
- Production-oriented AI architecture

The objective is not simply to build another chatbot.

The objective is to build a **complete AI engineering system where agents can retrieve knowledge, use tools, reason over multiple sources, verify their findings, and produce traceable results**.

---

# 16. Final Portfolio Deliverables

At completion, the project should contain:

```text
✓ Live web application
✓ GitHub repository
✓ Multi-agent LangGraph workflow
✓ RAG pipeline
✓ Qdrant vector database
✓ GitHub MCP integration
✓ Custom MCP tools
✓ Agent execution visualization
✓ Source citations
✓ Human approval workflow
✓ Ragas evaluation
✓ Langfuse observability
✓ Dockerized deployment
✓ Architecture diagram
✓ API documentation
✓ Demo video
✓ Complete README
```

## One-Line Resume Description

> **AgentOS — Built a multi-agent AI platform using LangGraph, LangChain, MCP, hybrid RAG, Qdrant, and LLM evaluation to analyze GitHub repositories and technical knowledge, execute tools, verify evidence, and generate traceable technical reports.**
