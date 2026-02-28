"""
Optional Advanced Features for IIT ML Service

This directory contains advanced features that are implemented but not integrated
into the main application. These features can be enabled by moving them back to
the main app directory and updating imports.

Features:
- Vector Store: Vector database support (Pinecone, Weaviate, Chroma)
- RAG: Clinical decision support using Retrieval-Augmented Generation
- AI Observability: Model drift detection and bias monitoring
- Multi-Tenancy: Multi-tenant isolation architecture
- Cost Monitoring: Per-tenant cost tracking and budgeting
- Incident Response: Structured runbooks for incident handling
- A/B Testing: Framework for A/B testing predictions
- Ensemble Methods: Ensemble prediction strategies

To enable any of these features:
1. Move the module from optional/ to app/
2. Update imports in app/main.py
3. Add API routes if applicable
"""

# Optional features are not imported by default
# To enable a feature, uncomment the appropriate import:
# from .vector_store import VectorStore, get_vector_store
# from .rag import ClinicalRAG, get_clinical_rag
# from .ai_observability import DriftDetector, BiasMonitor
# from .multi_tenancy import TenantContext, get_current_tenant
# from .cost_monitoring import CostTracker, get_cost_tracker
# from .incident_response import Runbook, get_runbook
# from .ab_testing import ABTestingFramework, get_ab_testing_framework
# from .ensemble_methods import EnsembleEngine, get_ensemble_engine
