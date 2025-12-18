# Research Workbench

> **⚠️ Work in Progress**: This project is currently under active development. Features, APIs, and documentation may change.

An AI-powered research assistant that uses multi-agent coordination to perform comprehensive, autonomous research tasks. Built with LangChain, LangGraph, and XAI's Grok model.

## Overview

Research Workbench is a sophisticated research system that intelligently routes queries between quick information retrieval and deep, multi-step research workflows. It employs a hierarchical agent architecture to plan, execute, and synthesize research findings into comprehensive reports.

## Architecture

The system uses a multi-agent architecture with four specialized components:

### 1. General Assistant
- **Role**: Research Coordinator and Router
- **Responsibilities**:
  - Evaluates user queries to determine the appropriate response strategy
  - Routes between direct answers, quick web searches, and deep research workflows
  - Manages the main conversation flow

### 2. Planner (Principal Investigator)
- **Role**: Research Strategy Architect
- **Responsibilities**:
  - Breaks down complex research queries into manageable sub-tasks
  - Delegates research tasks to specialized researcher agents
  - Reviews findings and determines when research is complete
  - Coordinates parallel or sequential research execution

### 3. Researcher
- **Role**: Specialized Research Analyst
- **Responsibilities**:
  - Executes specific research proposals assigned by the Planner
  - Performs iterative web searches using a ReAct (Reasoning + Acting) loop
  - Synthesizes findings into structured reports

### 4. Report Writer
- **Role**: Final Report Synthesizer
- **Responsibilities**:
  - Compiles research trajectory into polished, comprehensive reports
  - Formats findings using Markdown with proper structure
  - Ensures accuracy and completeness based on gathered evidence

## Features

- **Intelligent Query Routing**: Automatically determines whether a query needs quick search or deep research
- **Multi-Agent Coordination**: Hierarchical agent system for complex research tasks
- **Iterative Research**: ReAct-based research agents that persist until comprehensive answers are found
- **Structured Output**: Well-formatted research reports with proper citations and organization
- **Web Search Integration**: Powered by Tavily Search API for real-time, accurate results

## Requirements

- Python >= 3.13
- API keys for:
  - XAI (Grok model)
  - Tavily Search

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd research_workbench
```

2. Install dependencies using `uv`:
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

3. Set up environment variables:
```bash
export TAVILY_API_KEY="your-tavily-api-key"
export XAI_API_KEY="your-xai-api-key"
```

## Usage

Run the interactive CLI:

```bash
python -m research_workbench.deep_research
```

The system will prompt you for queries. You can:
- Ask simple questions for quick answers
- Request deep research reports on complex topics
- Type `exit` or `quit` to end the session

### Example Queries

**Quick Search:**
- "What's the current stock price of Apple?"
- "Who won the game last night?"

**Deep Research:**
- "Write a comprehensive report on the impact of AI on healthcare over the next decade"
- "Compare the features and pricing of the top 5 CRM tools"

## Project Structure

```
research_workbench/
├── research_workbench/
│   ├── __init__.py
│   ├── deep_research.py      # Main agent orchestration logic
│   └── prompts.py            # System prompts for all agents
├── notebooks/
│   └── reasoning_and_toolcalls.ipynb
├── pyproject.toml            # Project dependencies
└── README.md
```

## Dependencies

- `langchain` - LLM framework and agent tools
- `langgraph` - State management and workflow orchestration
- `langchain-tavily` - Tavily search integration
- `langchain-xai` - XAI Grok model integration
- `loguru` - Logging
- `tavily-python` - Tavily API client

## Development Status

This project is actively being developed. Current areas of focus include:
- Refining agent coordination logic
- Improving research quality and completeness
- Optimizing cost and latency
- Enhancing report formatting

## Future Work

This project is designed as a personal research system with an ambitious roadmap:

### Agent Paradigms
- **Debate-Verifier Agent**: Extend ReAct paradigm with an additional verifier/debator agent that performs adversarial debates to validate research findings and identify potential weaknesses or biases in conclusions.

### Idea Generation & Synthesis
- **Idea Generator**: Build an agent that generates new ideas based on previous ideas, creating an iterative ideation loop.
- **Synthesis Engine**: Combine deep research and debate capabilities to synthesize ideas, ensuring generated concepts are well-researched and critically examined.

### Specialized Research Agents
- **Paper Reading Agent**: Develop specialized agents for reading, understanding, and extracting insights from academic papers.
- **Literature Search Agent**: Create a specialized research agent focused on finding and evaluating relevant academic papers and scholarly sources.

### Development & Tooling
- **Coding Agent**: Integrate a coding agent/tool to facilitate idea prototyping, data analysis, and research automation, enabling the system to build and test hypotheses programmatically.

### Observability & Evaluation
- **Enhanced Observability**: Implement comprehensive logging, tracing, and monitoring for all agent interactions and decision points. **(High Priority)**
- **Evaluation Framework**: Build robust evaluation systems to measure research quality, agent performance, and system reliability. **(High Priority)**

## License

[Add your license here]

## Contributing

Contributions are welcome! Please note that this is a work-in-progress project, so expect frequent changes.
