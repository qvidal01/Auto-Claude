# Spec 001: Core Infrastructure Setup

## Context

**Project:** Subjectly Backend (FastAPI + SQLAlchemy + PostgreSQL)
**Goal:** Integrate Auto-Claude's autonomous agent framework into existing Subjectly backend
**Reference Implementation:** `/Users/qvidal01/projects/auto-claude` (forked for patterns)

## Current State

### Existing Architecture
- **Framework:** FastAPI 0.109.0 with Uvicorn
- **Database:** PostgreSQL 15 (SQLAlchemy 2.0 ORM)
- **Vector Store:** ChromaDB (document Q&A)
- **Task Queue:** Celery 5.3.4 + Redis
- **LLM Providers:** Gemini (primary), Claude, OpenAI, Ollama
- **Auth:** JWT + OAuth2 (Google, GitHub, Microsoft)
- **Multi-tenant:** Tenant isolation via middleware

### Existing Structure
```
app/
├── main.py
├── config.py
├── database.py
├── middleware/
├── models/
├── routers/
├── services/
├── repositories/
├── tasks/
└── utils/
```

## Task: Phase 1 - Core Infrastructure

Create the foundational infrastructure for autonomous agent system:

### 1. Agent Framework (`app/agents/`)

Create agent system following Auto-Claude patterns:

**Files to create:**
- `app/agents/__init__.py` - Package exports
- `app/agents/base.py` - BaseAgent abstract class with plan(), execute(), validate() methods
- `app/agents/registry.py` - AgentRegistry factory for creating agents by type
- `app/agents/context.py` - AgentContext dataclass (tenant, user, LLM provider, memory, RAG access)
- `app/agents/types.py` - Type definitions and enums (AgentType, AgentStatus, etc.)
- `app/agents/builtin/__init__.py` - Built-in agents package
- `app/agents/builtin/research_agent.py` - Placeholder for research agent
- `app/agents/builtin/qa_agent.py` - Placeholder for Q&A agent
- `app/agents/builtin/synthesis_agent.py` - Placeholder for synthesis agent

**Key requirements:**
- BaseAgent must be async-compatible (use async def)
- Integrate with existing `app/services/llm_provider.py`
- Support tenant isolation (use current_user.tenant_id)
- Error handling with retry logic (max 3 attempts)

### 2. Spec System (`app/specs/`)

Implement spec-driven workflow system:

**Files to create:**
- `app/specs/__init__.py` - Package exports
- `app/specs/models.py` - SQLAlchemy ORM models (Spec, SpecPhase, SpecTask)
- `app/specs/schema.py` - Pydantic schemas for API validation
- `app/specs/runner.py` - SpecRunner class for executing specs
- `app/specs/phases/__init__.py` - Phase implementations package
- `app/specs/phases/discovery.py` - Discovery phase (analyze context)
- `app/specs/phases/requirements.py` - Requirements extraction
- `app/specs/phases/planning.py` - Task planning and breakdown
- `app/specs/phases/execution.py` - Agent execution orchestration
- `app/specs/phases/validation.py` - Result validation
- `app/specs/templates/__init__.py` - Spec templates package
- `app/specs/templates/research.json` - Research workflow template
- `app/specs/templates/spec_contract.json` - Copy from Auto-Claude

**Database models:**
```python
class Spec(Base):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    subject_id: UUID (optional)
    name: str
    description: str
    workflow_type: str  # 'research', 'synthesis', 'qa'
    status: str  # 'pending', 'running', 'completed', 'failed'
    spec_data: JSONB
    created_at: datetime
    updated_at: datetime

class SpecPhase(Base):
    id: UUID
    spec_id: UUID
    phase_name: str
    status: str
    output_data: JSONB
    started_at: datetime
    completed_at: datetime

class SpecTask(Base):
    id: UUID
    spec_id: UUID
    phase_id: UUID
    agent_type: str
    task_data: JSONB
    result_data: JSONB
    status: str
    created_at: datetime
    completed_at: datetime
```

### 3. Memory System (`app/memory/`)

Integrate Graphiti graph database for conversation memory:

**Files to create:**
- `app/memory/__init__.py` - Package exports
- `app/memory/graphiti_client.py` - GraphitiClient wrapper with tenant isolation
- `app/memory/memory_manager.py` - MemoryManager high-level API
- `app/memory/episodic.py` - Episodic memory operations
- `app/memory/entity.py` - Entity memory operations
- `app/memory/search.py` - Semantic search interface

**Key requirements:**
- Tenant-scoped databases: `data/graphiti/{tenant_id}/`
- Use Ollama for embeddings: `nomic-embed-text:latest`
- Integrate with existing `app/services/rag.py`
- Store Q&A interactions, insights, and relationships

### 4. WebSocket Infrastructure (`app/websockets/`)

Real-time streaming for agent progress:

**Files to create:**
- `app/websockets/__init__.py` - Package exports
- `app/websockets/manager.py` - WebSocketManager for connection handling
- `app/websockets/handlers.py` - Message handlers
- `app/websockets/events.py` - Event type definitions (AgentEvent, SpecEvent)

**WebSocket channels:**
- `ws://api/v1/ws/agents/{agent_id}` - Agent progress updates
- `ws://api/v1/ws/specs/{spec_id}` - Spec execution updates
- `ws://api/v1/ws/chat/{subject_id}` - Real-time chat with memory

**Event types:**
- `phase_started`, `task_progress`, `result`, `error`

### 5. Configuration Updates

**Update `app/config.py`:**
```python
# Graphiti settings
GRAPHITI_DB_PATH: str = "data/graphiti"
GRAPHITI_EMBEDDER_PROVIDER: str = "ollama"
GRAPHITI_EMBEDDER_MODEL: str = "nomic-embed-text:latest"
GRAPHITI_ENABLE: bool = True

# Agent settings
MAX_CONCURRENT_AGENTS: int = 5
AGENT_TIMEOUT_SECONDS: int = 300
ENABLE_PARALLEL_EXECUTION: bool = True

# WebSocket settings
WS_HEARTBEAT_INTERVAL: int = 30
WS_MAX_CONNECTIONS_PER_USER: int = 10
```

### 6. Dependencies

**Add to `requirements.txt`:**
```
graphiti-core>=0.3.0
kuzudb>=0.0.9
websockets>=12.0
aiofiles>=23.2.1
asyncio-throttle>=1.0.2
```

### 7. Database Migration

**Create Alembic migration:**
```bash
alembic revision --autogenerate -m "Add agent spec and memory tables"
```

**New tables:**
- `specs` (tenant_id, user_id, subject_id, workflow_type, status, spec_data)
- `spec_phases` (spec_id, phase_name, status, output_data)
- `spec_tasks` (spec_id, phase_id, agent_type, task_data, result_data, status)

## Success Criteria

1. ✅ All new modules import without errors
2. ✅ `BaseAgent` can be instantiated with AgentContext
3. ✅ `GraphitiClient` connects to Ollama embedder
4. ✅ `WebSocketManager` accepts and manages connections
5. ✅ Database migration applies successfully
6. ✅ No breaking changes to existing endpoints
7. ✅ All existing tests still pass

## Files to Modify

- `app/config.py` - Add new configuration settings
- `app/models/__init__.py` - Export new models (Spec, SpecPhase, SpecTask)
- `requirements.txt` - Add new dependencies

## Files to Reference (Auto-Claude)

Study these files from `/Users/qvidal01/projects/auto-claude/apps/backend/`:
- `spec_contract.json` - Spec structure and validation schema
- `query_memory.py` - Graphiti integration pattern
- `phase_config.py` - Phase execution patterns
- `project_analyzer.py` - Document analysis patterns

## Implementation Notes

1. **Maintain existing patterns:**
   - Use existing `TenantRepository` base class for tenant isolation
   - Follow existing FastAPI dependency injection patterns
   - Use existing `create_provider_for_user()` for LLM access

2. **Type safety:**
   - Use Pydantic models for all API schemas
   - Type hints on all functions
   - SQLAlchemy 2.0 declarative style

3. **Async patterns:**
   - All I/O operations should be async
   - Use `asyncio.gather()` for parallel operations
   - Proper exception handling in async contexts

4. **Testing:**
   - Create unit tests in `tests/agents/`, `tests/specs/`, `tests/memory/`
   - Mock external dependencies (Ollama, Graphiti)
   - Test tenant isolation

## Validation Steps

After implementation:

```bash
# 1. Check imports
python -c "from app.agents import BaseAgent, AgentRegistry; print('✓ Agents')"
python -c "from app.specs import Spec, SpecRunner; print('✓ Specs')"
python -c "from app.memory import GraphitiClient, MemoryManager; print('✓ Memory')"
python -c "from app.websockets import WebSocketManager; print('✓ WebSockets')"

# 2. Run migrations
alembic upgrade head

# 3. Test database models
python -c "from app.specs.models import Spec; print(Spec.__table__)"

# 4. Test Graphiti connection
python -c "from app.memory import GraphitiClient; client = GraphitiClient('test-tenant'); print('✓ Connected')"

# 5. Run existing tests
pytest tests/ -v
```

## Estimated Time

- Agent framework: 30 minutes
- Spec system: 45 minutes
- Memory integration: 30 minutes
- WebSocket infrastructure: 20 minutes
- Configuration & migration: 15 minutes
- Testing & validation: 20 minutes

**Total: ~2.5 hours autonomous build time**
