# Autonomous AI Researcher 🔬🤖

An autonomous multi-agent AI system designed to conduct comprehensive scientific research. It autonomously navigates technical domains, synthesizes academic literature, generates rigorous experiments, executes code, and produces structured research reports.

This project is a modular, extensible framework for building autonomous agents capable of complex problem-solving and scientific discovery.

---

## 🚀 Key Capabilities

- **Autonomous Research Synthesis**: Automatically discovers and summarizes relevant academic papers via the arXiv API.
- **Hypothesis-Driven Experimentation**: Proposes and writes Python code to test research hypotheses.
- **Verified Code Execution**: Runs experiments in controlled environments to validate theories.
- **Collaborative Multi-Agent Brain**: Employs a decentralized architecture of specialized agents (Planner, Researcher, Coder, Critic).
- **Long-Term Context Memory**: Utilizes vector embeddings to store and retrieve research history for iterative reasoning.

---

## 🏗️ Multi-Agent Architecture

The system operates through a collaborative loop of four specialized agents:

| Agent | Responsibility |
| :--- | :--- |
| **Planner** | Decomposes high-level research questions into actionable tasks and milestones. |
| **Researcher** | Performs deep-dives into literature, retrieving and synthesizing technical information. |
| **Coder** | Translates research insights into executable Python code and experimental setups. |
| **Critic** | Evaluates results, identifies flaws, and synthesizes final conclusions. |

---

## 🛠️ Technology Stack

- **Core**: Python 3.10+
- **LLM Context**: Structured multi-agent reasoning loops.
- **Information Retrieval**: arXiv API integration and semantic search.
- **Memory**: Vector database (Simple or Pinecone/Chroma-ready).
- **Execution**: Isolated Python sandbox for code experiments.
- **UI**: Streamlit-based dashboard for real-time monitoring.

---

## 📖 Getting Started

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file with your API keys:
```env
OPENAI_API_KEY=your_key_here
```

### 3. Usage
Launch the research dashboard:
```bash
streamlit run ui/app.py
```

---

## 🔬 Example Research Workflow
1. **Goal**: "Analyze the impact of different activation functions on Transformer convergence speed."
2. **Planner**: Creates a plan involving literature review of SwiGLU, GELU, and ReLU.
3. **Researcher**: Retrieves 5 relevant papers and summarizes their findings on convergence.
4. **Coder**: Generates a PyTorch script to bench these functions.
5. **Critic**: Analyzes the benchmark results and produces a structured PDF report.