"""
RAG (Retrieval-Augmented Generation) for Clinical Decision Support

Provides intelligent clinical decision support by combining:
1. Vector similarity search for relevant clinical documents
2. LLM generation for contextual answers
3. Citation tracking for evidence-based recommendations

Usage:
    from app.rag import ClinicalRAG, get_clinical_rag
    
    rag = get_clinical_rag()
    
    # Ask a clinical question
    response = await rag.ask_clinical_question(
        question="What are the treatment guidelines for IIT?",
        patient_context={"age": 35, "gender": "F", "symptoms": ["fever", "rash"]}
    )
    
    print(response.answer)
    print(response.sources)
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

from .vector_store import VectorStore, Document, SearchResult, get_vector_store
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class ClinicalQuestion:
    """Clinical question with context"""
    question: str
    patient_context: Optional[Dict[str, Any]] = None
    specialty: Optional[str] = None
    urgency: str = "routine"  # routine, urgent, emergent
    max_sources: int = 5
    include_guidelines: bool = True
    include_research: bool = True


@dataclass
class SourceCitation:
    """Citation for a source document"""
    document_id: str
    title: str
    text: str
    relevance_score: float
    source_type: str  # guideline, research, clinical_note, etc.
    publication_date: Optional[datetime] = None
    authors: Optional[List[str]] = None
    url: Optional[str] = None


@dataclass
class ClinicalResponse:
    """Response to a clinical question"""
    answer: str
    sources: List[SourceCitation] = field(default_factory=list)
    confidence: float = 0.0
    disclaimer: str = "This AI-generated response is for informational purposes only and should not replace professional medical judgment."
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClinicalRAG:
    """
    RAG system for clinical decision support
    
    Combines vector similarity search with LLM generation
    to provide evidence-based clinical recommendations.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        llm_api_key: Optional[str] = None,
        llm_model: str = "gpt-4"
    ):
        self.vector_store = vector_store or get_vector_store()
        self.llm_api_key = llm_api_key or getattr(settings, 'openai_api_key', None)
        self.llm_model = llm_model
        self._initialized = False
    
    async def initialize(self):
        """Initialize the RAG system"""
        if self.vector_store:
            await self.vector_store.initialize()
        self._initialized = True
        logger.info("Clinical RAG system initialized")
    
    async def ask_clinical_question(
        self,
        question: str,
        patient_context: Optional[Dict[str, Any]] = None,
        specialty: Optional[str] = None,
        max_sources: int = 5,
        include_guidelines: bool = True,
        include_research: bool = True
    ) -> ClinicalResponse:
        """
        Ask a clinical question and get an evidence-based answer
        
        Args:
            question: The clinical question
            patient_context: Patient demographics and clinical data
            specialty: Medical specialty for filtering
            max_sources: Maximum number of sources to retrieve
            include_guidelines: Include clinical guidelines
            include_research: Include research papers
            
        Returns:
            ClinicalResponse with answer, sources, and recommendations
        """
        await self.initialize()
        
        try:
            # Step 1: Retrieve relevant documents
            sources = await self._retrieve_sources(
                question=question,
                patient_context=patient_context,
                specialty=specialty,
                max_sources=max_sources,
                include_guidelines=include_guidelines,
                include_research=include_research
            )
            
            # Step 2: Generate answer using LLM
            answer = await self._generate_answer(
                question=question,
                patient_context=patient_context,
                sources=sources
            )
            
            # Step 3: Extract recommendations and warnings
            recommendations = await self._extract_recommendations(answer, sources)
            warnings = await self._extract_warnings(answer, patient_context)
            
            # Step 4: Calculate confidence
            confidence = self._calculate_confidence(sources)
            
            return ClinicalResponse(
                answer=answer,
                sources=sources,
                confidence=confidence,
                recommendations=recommendations,
                warnings=warnings,
                metadata={
                    "question": question,
                    "model": self.llm_model,
                    "sources_count": len(sources),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to process clinical question: {e}")
            return ClinicalResponse(
                answer=f"I apologize, but I encountered an error processing your question: {str(e)}",
                confidence=0.0,
                warnings=["System error occurred. Please consult with a healthcare professional directly."]
            )
    
    async def _retrieve_sources(
        self,
        question: str,
        patient_context: Optional[Dict[str, Any]],
        specialty: Optional[str],
        max_sources: int,
        include_guidelines: bool,
        include_research: bool
    ) -> List[SourceCitation]:
        """Retrieve relevant sources from vector store"""
        sources = []
        
        if not self.vector_store:
            return sources
        
        try:
            # Build search query with context
            search_query = question
            if patient_context:
                context_str = ", ".join([f"{k}: {v}" for k, v in patient_context.items()])
                search_query = f"{question} (Context: {context_str})"
            
            # Build filter
            filter_dict = {}
            if specialty:
                filter_dict["specialty"] = specialty
            if include_guidelines and not include_research:
                filter_dict["source_type"] = "guideline"
            elif include_research and not include_guidelines:
                filter_dict["source_type"] = "research"
            
            # Search vector store
            search_results = await self.vector_store.search(
                query=search_query,
                top_k=max_sources,
                filter=filter_dict if filter_dict else None
            )
            
            # Convert to SourceCitation objects
            for result in search_results:
                sources.append(SourceCitation(
                    document_id=result.document.id,
                    title=result.document.metadata.get("title", "Untitled"),
                    text=result.document.text[:500],  # Truncate for display
                    relevance_score=result.score,
                    source_type=result.document.metadata.get("source_type", "unknown"),
                    publication_date=self._parse_date(result.document.metadata.get("publication_date")),
                    authors=result.document.metadata.get("authors", []),
                    url=result.document.metadata.get("url")
                ))
        
        except Exception as e:
            logger.error(f"Failed to retrieve sources: {e}")
        
        return sources
    
    async def _generate_answer(
        self,
        question: str,
        patient_context: Optional[Dict[str, Any]],
        sources: List[SourceCitation]
    ) -> str:
        """Generate answer using LLM"""
        if not self.llm_api_key:
            # Fallback to template-based answer
            return self._generate_template_answer(question, patient_context, sources)
        
        try:
            import openai  # type: ignore
            
            # Build context from sources
            context_parts = []
            for i, source in enumerate(sources, 1):
                context_parts.append(f"Source {i}: {source.text}")
        except ImportError:
            logger.warning("OpenAI not installed, using template-based answer")
            return self._generate_template_answer(question, patient_context, sources)
        except Exception as e:
            logger.error(f"Failed to generate LLM answer: {e}")
            return self._generate_template_answer(question, patient_context, sources)
            
            context = "\n\n".join(context_parts)
            
            # Build patient context string
            patient_str = ""
            if patient_context:
                patient_str = "\nPatient Context:\n" + json.dumps(patient_context, indent=2)
            
            # Create prompt
            prompt = f"""You are a clinical decision support AI assistant. Answer the following clinical question based on the provided sources.

Question: {question}{patient_str}

Relevant Sources:
{context}

Instructions:
1. Provide a clear, evidence-based answer
2. Cite specific sources when making recommendations
3. Highlight any conflicting information in sources
4. Include appropriate disclaimers
5. If sources don't contain sufficient information, state this clearly

Answer:"""
            
            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful clinical decision support assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
    
    def _generate_template_answer(
        self,
        question: str,
        patient_context: Optional[Dict[str, Any]],
        sources: List[SourceCitation]
    ) -> str:
        """Generate template-based answer without LLM"""
        if not sources:
            return f"No relevant clinical sources found for: {question}\n\nPlease consult with a healthcare professional for guidance on this question."
        
        # Build answer from sources
        answer_parts = [f"Based on {len(sources)} relevant clinical sources:\n"]
        
        for i, source in enumerate(sources, 1):
            answer_parts.append(f"\n{i}. {source.title}")
            answer_parts.append(f"   Relevance: {source.relevance_score:.2%}")
            answer_parts.append(f"   {source.text[:200]}...")
        
        answer_parts.append(f"\n\nQuestion: {question}")
        
        if patient_context:
            answer_parts.append("\n\nConsiderations for this patient:")
            for key, value in patient_context.items():
                answer_parts.append(f"  - {key}: {value}")
        
        answer_parts.append("\n\nPlease review the full sources and consult with clinical guidelines for complete information.")
        
        return "\n".join(answer_parts)
    
    async def _extract_recommendations(
        self,
        answer: str,
        sources: List[SourceCitation]
    ) -> List[str]:
        """Extract actionable recommendations from answer and sources"""
        recommendations = []
        
        # Extract from sources
        for source in sources:
            if "recommend" in source.text.lower():
                # Simple extraction - in production use NLP
                sentences = source.text.split(". ")
                for sentence in sentences:
                    if "recommend" in sentence.lower():
                        recommendations.append(f"From {source.title}: {sentence}")
        
        return recommendations[:5]  # Limit to top 5
    
    async def _extract_warnings(
        self,
        answer: str,
        patient_context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Extract warnings based on patient context and answer"""
        warnings = []
        
        # Check for common contraindications
        if patient_context:
            # Age-related warnings
            age = patient_context.get("age")
            if age and age < 18:
                warnings.append("Pediatric patient: Ensure dosages and treatments are age-appropriate.")
            elif age and age > 65:
                warnings.append("Geriatric patient: Consider renal/hepatic function and polypharmacy.")
            
            # Pregnancy warning
            if patient_context.get("pregnancy"):
                warnings.append("Pregnant patient: Consult specialized guidelines for medication safety.")
            
            # Allergy warning
            if patient_context.get("allergies"):
                warnings.append(f"Patient allergies: {patient_context['allergies']}. Review all medications for interactions.")
        
        return warnings
    
    def _calculate_confidence(self, sources: List[SourceCitation]) -> float:
        """Calculate confidence score based on sources"""
        if not sources:
            return 0.0
        
        # Average relevance score
        avg_relevance = sum(s.relevance_score for s in sources) / len(sources)
        
        # Boost for guideline sources
        guideline_boost = sum(0.1 for s in sources if s.source_type == "guideline")
        
        # Cap at 1.0
        confidence = min(avg_relevance + guideline_boost, 1.0)
        
        return round(confidence, 2)
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str)
        except:
            return None


class ClinicalGuidelinesIndexer:
    """
    Indexer for clinical guidelines and research papers
    
    Provides utilities for ingesting and indexing clinical documents
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or get_vector_store()
    
    async def index_guideline(
        self,
        title: str,
        content: str,
        specialty: str,
        publication_date: Optional[str] = None,
        authors: Optional[List[str]] = None,
        url: Optional[str] = None
    ) -> str:
        """Index a clinical guideline"""
        doc_id = f"guideline_{hash(content)}"
        
        document = Document(
            id=doc_id,
            text=content,
            metadata={
                "title": title,
                "source_type": "guideline",
                "specialty": specialty,
                "publication_date": publication_date,
                "authors": authors or [],
                "url": url
            }
        )
        
        await self.vector_store.add_documents([document])
        logger.info(f"Indexed guideline: {title}")
        return doc_id
    
    async def index_research_paper(
        self,
        title: str,
        abstract: str,
        specialty: str,
        publication_date: Optional[str] = None,
        authors: Optional[List[str]] = None,
        journal: Optional[str] = None,
        doi: Optional[str] = None
    ) -> str:
        """Index a research paper"""
        doc_id = f"research_{hash(abstract)}"
        
        document = Document(
            id=doc_id,
            text=abstract,
            metadata={
                "title": title,
                "source_type": "research",
                "specialty": specialty,
                "publication_date": publication_date,
                "authors": authors or [],
                "journal": journal,
                "doi": doi
            }
        )
        
        await self.vector_store.add_documents([document])
        logger.info(f"Indexed research paper: {title}")
        return doc_id
    
    async def index_clinical_note(
        self,
        patient_id: str,
        note_text: str,
        note_type: str,
        date: Optional[str] = None
    ) -> str:
        """Index a clinical note (for similar case retrieval)"""
        doc_id = f"note_{patient_id}_{hash(note_text)}"
        
        document = Document(
            id=doc_id,
            text=note_text,
            metadata={
                "source_type": "clinical_note",
                "note_type": note_type,
                "patient_id": patient_id,
                "date": date
            }
        )
        
        await self.vector_store.add_documents([document])
        logger.info(f"Indexed clinical note for patient {patient_id}")
        return doc_id


# Singleton instance
_clinical_rag: Optional[ClinicalRAG] = None


def get_clinical_rag() -> Optional[ClinicalRAG]:
    """Get the singleton ClinicalRAG instance"""
    global _clinical_rag
    
    if _clinical_rag is None:
        _clinical_rag = ClinicalRAG()
        logger.info("Clinical RAG system created")
    
    return _clinical_rag
