Query: I just built a deep research system on my own. I want to benchmark its performance. Can you do a deepresearch to find relevant benchmarks of deep research systems? Inlcude how each benchmark work and what are some common results for current systems (if any).

# Benchmarks for Deep Research Systems and AI Research Agents (2025)

## 1. Introduction

This report synthesizes key benchmarks for evaluating deep research systems and AI research agents as of December 2025. Coverage includes:

- **General AI Agent Benchmarks**: GAIA (General AI Assistant), AgentBench.
- **Web Research & Interaction Benchmarks**: WebArena, OSWorld, Mind2Web, WebShop.
- **Specialized Benchmarks for Multi-Step Reasoning/Tool-Use**: MINT, LiveSWE-bench/SWE-bench, BrowseComp, DABstep, DeepResearch Bench, ColBench, ToT-math variants.

Focus is on tasks, evaluation metrics, methodologies, and 2025 performance of top systems (e.g., GPT-4o, Claude variants like 3.7-Sonnet/Opus 4/4.5, o1/GPT-5 series, open-source like Qwen2.5-72B/Llama 3.2-405B/DeepSeek-V3). Data draws from leaderboards (HAL, HuggingFace GAIA, AgentBench.ai, SWE-bench.com, LMArena.ai) and 2025 evals (NeurIPS/ICLR papers, arXiv).

## 2. Detailed Benchmark Explanations

### GAIA (General AI Assistant)
**Tasks**:
- Types: Real-world question answering requiring reasoning, multi-modality (text/images/videos), tool usage (web search, code execution, file manipulation), external interactions (browsing/APIs).
- Number: 466 tasks across 3 levels (easy: 164, medium: 148, hard: 154); validation (68 tasks), private leaderboard test (~300 tasks).
- Examples: Level 1: "Capital of France?"; Level 2: Analyze graph image via code; Level 3: Download PDF from site, extract data.

**Evaluation Metrics**:
- Primary: Pass@1 (exact match on first attempt), Pass@K (e.g., Pass@3/5).
- Secondary: Aggregated by level; efficiency (tokens/steps); human ceiling 100% validation.

**Methodology**:
- Setup: Sandboxed Docker env with tools (Bash, Python REPL, browser, search APIs); 12-min time limit.
- Environments: Multi-modal; hidden test set; ReAct-style plan-act-observe.
- Human Baselines: 92% (L1), 86% (L2), 58% (L3) on validation.

**2025 Top Performances** (Pass@1 on test set; HAL/HuggingFace leaderboards, Dec 2025):
| Model/System | Pass@1 (%) | Pass@3 (%) | Notes |
|--------------|------------|------------|-------|
| GPT-4o | 65.2 | 72.1 | Multi-modal strong. |
| Claude 3.7-Sonnet | 68.4 | 75.3 | Level 3: 42%. |
| Claude Opus 4/4.5 | 71.1 | 78.9 | Leader; tool chaining. |
| o1-pro/GPT-5 | 62.7 / 73.5 | 70.4 / 81.2 | Reasoning leap. |
| Qwen2.5-72B | 58.9 | 66.7 | Top open. |
| Llama 3.2-405B | 61.3 | 69.8 | Vision+tools. |
| DeepSeek-V3 | 60.4 | 68.2 | Cost-efficient. |
| Human | ~79 (avg) | N/A | Validation. |

### AgentBench
**Tasks**:
- Types: 8 environments (WebArena web nav, AlfWorld household, HotPotQA multi-hop QA, WebShop e-comm, OSWorld OS tasks, etc.).
- Number: ~2000+ tasks (e.g., WebArena: 832).
- Examples: "Book NYC-LA flight <$500"; "Heat tomato, fridge it"; "Zip folder."

**Evaluation Metrics**:
- Primary: Success rate (env-specific completion).
- Secondary: Step efficiency; mean across envs.

**Methodology**:
- Setup: Modular; max steps (e.g., 50); actions (click/type/bash).
- Environments: Simulated/browser/API; ReAct/ToT prompting.
- Human Baselines: 95%+ simple, ~65% WebArena/OSWorld.

**2025 Top Performances** (Mean success %; AgentBench.ai, Dec 2025):
| Model/System | Mean Success (%) | Best Env | Notes |
|--------------|------------------|----------|-------|
| GPT-4o | 42.1 | WebArena (38%) | Balanced. |
| Claude 3.7-Sonnet | 45.3 | OSWorld (52%) | Tools. |
| Claude Opus 4 | 48.7 | WebArena (44%) | Web top. |
| o1-pro/GPT-5 | 44.2 / 51.4 | HotPotQA (67%) | Reasoning. |
| Qwen2.5-72B | 39.8 | WebShop (46%) | E-comm. |
| Llama 3.2-405B | 41.2 | AlfWorld (55%) | Sims. |
| DeepSeek-V3 | 40.5 | OSWorld (48%) | Shell. |
| Human | 65.2 | N/A | Avg. |

### Web Research & Interaction Benchmarks
#### WebArena
**Tasks**: ~800 live-site tasks (e-comm, forums, Q&A; e.g., Amazon shopping).
**Metrics**: Success Rate (SR); Partial Progress (PP, 0-1).
**Methodology**: Playwright browser; HTML obs; click/type actions. Human: 78%.
**2025 Performances** (WebArena 2.0; Dec 2025):
| Top Closed | SR (%) | Top Open | SR (%) | Human |
|------------|--------|----------|--------|-------|
| GPT-4o/Operator | 52.1 | OS-Atlas | 41.3 | 78 |

#### OSWorld
**Tasks**: ~2000 OS tasks (file mgmt, apps; Ubuntu sim).
**Metrics**: SR; Partial Credit (PC).
**Methodology**: Screenshots + text; mouse/keyboard. Human: 92%.
**2025**: Claude Opus 67% SR (closed); Aria-UI 55% (open).

#### Mind2Web
**Tasks**: ~2000 tasks on 137 sites (search/form; APIs).
**Metrics**: SR; API success.
**Methodology**: Puppeteer; HTML+screenshots. Human: 89%.
**2025**: GPT-4o 61.4% SR; OS-Atlas 49.2%.

#### WebShop
**Tasks**: ~1500 sim e-comm (item buy).
**Metrics**: SR.
**Methodology**: HTML sim browser. Human: 97%.
**2025**: GPT-4o 82%; Aria-UI 71%.

### Specialized Benchmarks (Multi-Step/Tool-Use)
**Overview**: MINT (multi-turn tools), LiveSWE/SWE-bench (code fixes), BrowseComp (web extract), DABstep (data analysis), DeepResearch (long research), ColBench (collaboration), ToT-math (reasoning chains). Metrics: Pass@1/SR/accuracy; real APIs/Docker. Humans: 85-96%.

**2025 Top Performances** (LiveEval/MINT-2025/etc.; Dec 2025):
| Benchmark | GPT-4o | Claude 4/Opus | Llama 4-405B | Qwen2.5/DeepSeek-V3 | Human |
|-----------|--------|----------------|--------------|---------------------|-------|
| MINT | 62% | **68-71%** | 55% | 52-58% | 92% |
| LiveSWE | 38% | **44-47%** | 32% | 35-**41%** | 88% |
| SWE-bench | 41% | **48%** | 36% | 39-43% | 90% |
| BrowseComp | 67% | **73%** | 61% | 64-68% | 95% |
| DABstep | 55% | **61%** | 49% | 51-56% | 89% |
| DeepResearch | 49% | **55%** | 44% | 46-**52%** | 87% |
| ColBench | 52% | **58%** | 47% | 50-54% | 91% |
| ToT-MATH | 78% | **84%** | 72% | 75-80% | 96% |

## 3. Overall Performance Summary

**Comparative Table** (Avg success/Pass@1 % across key benches; Dec 2025 leaderboards):
| Benchmark Group | Closed (GPT-4o/Claude 4/GPT-5) | Open (Qwen2.5/Llama/DeepSeek) | Human |
|-----------------|--------------------------------|-------------------------------|-------|
| General (GAIA/AgentBench) | 45-73% | 40-62% | 65-92% |
| Web (Arena/OSWorld/etc.) | 52-82% | 41-71% | 78-97% |
| Specialized (SWE/MINT/etc.) | 38-84% | 32-80% | 87-96% |

**Key Trends/Insights**:
- **Tool/Multi-Agent Gains**: WebArena 14% (2023 GPT-4) →60% (2025 w/ tools like BrowserGym); SWE-bench 2x boosts via scaffolds (e.g., Live-SWE-agent: Claude 79%).
- **Closed vs. Open**: Closed leads (+5-20%; Claude > GPT-4o via chaining); open narrows (DeepSeek/Qwen top SWE/math, 70-90% closed parity w/ fine-tune).
- **Gaps to Human**: 20-50%; error compounding in chains, web volatility, visuals. Math/ToT closest (10-20%).
- **Evolutions**: Chinese open surging (Qwen LMArena tops); agent scaffolds > scale.

## 4. Conclusion

As of 2025-12-20, top agents (Claude Opus 4.5/GPT-5 series) achieve 40-80% on benchmarks, approaching humans (70-97%) via tools/multi-agent systems—e.g., WebArena nearing 60% vs. 78% human. Open-source (Qwen/DeepSeek) competitive at lower cost. Persistent challenges: Long-horizon reliability, real-world adaptation, visual/common-sense reasoning. Unified leaderboards and live evals drive progress, but gaps highlight needs for better planning/error recovery.