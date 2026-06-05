# KIS4 Project Proposal  
## AI-Assisted Software Engineering  
### Project Title  
**Emergent Rule Evolution Game with Autonomous AI Agents**

---

# Team Members

| Name | Responsibilities |
|---|---|
| Student 1 | Agent architecture, backend implementation |
| Student 2 | Game logic, communication protocol |
| Student 3 | Evaluation, documentation, testing |

---

# Goal of the Project

The goal of this project is to explore how autonomous AI agents can collaboratively and competitively participate in software-driven game environments while dynamically modifying the game rules themselves.

We will develop a turn-based game system in which:

- Two AI agents play against each other
- The game starts with a minimal predefined rule set
- During each turn, an agent may:
  - perform a normal game action
  - or either:
    - add a new rule
    - modify an existing rule
    - remove a rule

The project focuses on understanding:

- how AI agents can be created and orchestrated
- how agents maintain shared context
- how agents communicate game state and rules
- how rule evolution affects gameplay behavior
- how generative AI tools support the software engineering process

The project combines:
- AI-assisted software engineering
- autonomous agents
- prompt engineering
- dynamic rule systems
- multi-agent communication

---

# Research Questions

## Main Questions

1. How can we set up autonomous AI agents?
2. How can multiple AI agents communicate while maintaining a shared understanding of the game context?
3. How do dynamically changing rules influence agent behavior and game stability?
4. Which AI-assisted development tools are most useful during implementation?

---

# Project Scope

The system will include:

- A game engine
- A dynamic rule management system
- Two AI agents
- Shared context/state handling
- Logging and visualization of rule evolution
- AI-assisted development workflow documentation

The agents will interact using structured prompts and shared game state representations.

---

# Proposed Technical Architecture

## Core Components

### 1. Game Engine
Responsible for:
- turn handling
- rule validation
- score tracking
- game state management

### 2. Rule Engine
Responsible for:
- storing active rules
- applying modified rules
- validating rule consistency
- preventing invalid or contradictory rules

### 3. AI Agents
Each agent:
- receives the current game state
- interprets active rules
- decides on actions
- optionally changes rules

Possible implementation:
- OpenAI API
- Gemini API
- local LLMs using Ollama

### 4. Shared Context Layer
Maintains:
- current game state
- active rules
- turn history
- communication format

Possible formats:
- JSON
- structured prompts
- shared memory object

### 5. Logging & Evaluation
Stores:
- prompts
- agent decisions
- rule changes
- game outcomes

---

# AI Assistance in the Development Process

The project itself studies AI agents, but AI tools will also support the development process.

## AI Tools Used

| Tool | Usage |
|---|---|
| ChatGPT | architecture discussion, prompt engineering, debugging |
| GitHub Copilot | code generation and autocomplete |
| Gemini | alternative code suggestions and documentation |
| AI image/diagram tools | architecture diagrams |

---

# Development Workflow

## AI-Assisted Activities

- generating boilerplate code
- discussing software architecture
- generating documentation
- debugging implementation issues
- improving prompts for agent behavior
- generating test cases

---

# Validation of the Project

The project will be considered successful if:

- Two agents can autonomously play the game
- Agents can successfully modify rules
- Both agents maintain a consistent understanding of the current rules
- Rule changes affect future gameplay
- The system remains stable during multiple rounds

Additional evaluation:
- compare different prompting strategies
- analyze emergent gameplay behavior
- analyze communication consistency between agents

---

# Example Gameplay Flow

1. Initial rules are loaded
2. Agent A performs a move
3. Agent A modifies a rule
4. Updated rule set is shared
5. Agent B interprets updated rules
6. Agent B performs a move
7. Agent B modifies another rule
8. Process repeats

---

# Preliminary Technology Stack

| Category | Technology |
|---|---|
| Programming Language | Python |
| AI APIs | OpenAI / Gemini / Ollama |
| Backend | Python FastAPI or Flask |
| Communication Format | JSON |
| Version Control | Git + GitHub |
| Containerization | Docker |
| Development Environment | VS Code |

---

# Development / Architecture Diagram

```text
+-------------------+
|   Shared Context  |
|  Game State JSON  |
+---------+---------+
          |
          v
+---------+---------+
|     Game Engine   |
+---------+---------+
          |
  -------------------
  |                 |
  v                 v
+------+         +------+
|AgentA| <-----> |AgentB|
+------+         +------+
  |                 |
  -------------------
          |
          v
+-------------------+
|    Rule Engine    |
+-------------------+