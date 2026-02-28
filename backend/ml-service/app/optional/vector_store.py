"""
Vector Database Integration for RAG and Semantic Search

Supports multiple vector database backends:
- Pinecone (cloud-hosted)
- Weaviate (self-hosted or cloud)
- Chroma (local/embedded)

Usage:
    from app.vector_store import VectorStore, get_vector_store
    
    # Initialize vector store
    vector_store = get_vector_store()
    
    # Index documents
    await vector_store.add_documents([
        {"id": "doc1", "text": "Clinical guidelines for IIT treatment...", "metadata": {"source": "guidelines"}}
    ])
    
    # Search for similar documents
    results = await vector_store.search("treatment protocols for IIT", top_k=5)
"""

import logging
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStoreType(Enum):
    """Supported vector database types"""
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    CHROMA = "chroma"
    FAISS = "faiss"


@dataclass
class Document:
    """Document for vector storage"""
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Result from vector similarity search"""
    document: Document
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStoreBackend(ABC):
    """Abstract base class for vector store backends"""
    
    @abstractmethod
    async def initialize(self):
        """Initialize the vector store connection"""
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector store"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    async def delete(self, document_ids: List[str]) -> bool:
        """Delete documents by ID"""
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the vector store is healthy"""
        pass


class PineconeBackend(VectorStoreBackend):
    """Pinecone vector store implementation"""
    
    def __init__(
        self,
        api_key: str,
        environment: str,
        index_name: str,
        dimension: int = 1536,
        metric: str = "cosine"
    ):
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric
        self._index = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Pinecone connection"""
        try:
            import pinecone  # type: ignore
            
            # Initialize Pinecone
            pinecone.init(
                api_key=self.api_key,
                environment=self.environment
            )
        except ImportError:
            logger.error("pinecone-client not installed. Install with: pip install pinecone-client")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
            
            # Get or create index
            if self.index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric
                )
                logger.info(f"Created Pinecone index: {self.index_name}")
            
            self._index = pinecone.Index(self.index_name)
            self._initialized = True
            logger.info(f"Pinecone backend initialized: {self.index_name}")
        
        except ImportError:
            logger.error("pinecone-client not installed. Install with: pip install pinecone-client")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to Pinecone"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate embeddings (would use OpenAI/Cohere/etc.)
            embeddings = await self._generate_embeddings([doc.text for doc in documents])
            
            # Prepare vectors for upsert
            vectors = []
            for doc, embedding in zip(documents, embeddings):
                vectors.append({
                    "id": doc.id,
                    "values": embedding,
                    "metadata": {
                        "text": doc.text,
                        **doc.metadata
                    }
                })
            
            # Upsert to Pinecone
            self._index.upsert(vectors=vectors)
            
            logger.info(f"Added {len(documents)} documents to Pinecone")
            return [doc.id for doc in documents]
        
        except Exception as e:
            logger.error(f"Failed to add documents to Pinecone: {e}")
            raise
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search Pinecone for similar documents"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embeddings([query])
            query_embedding = query_embedding[0]
            
            # Search Pinecone
            search_params = {"top_k": top_k, "include_metadata": True}
            if filter:
                search_params["filter"] = filter
            
            results = self._index.query(
                vector=query_embedding,
                **search_params
            )
            
            # Convert to SearchResult objects
            search_results = []
            for match in results.get("matches", []):
                doc = Document(
                    id=match["id"],
                    text=match["metadata"].get("text", ""),
                    metadata={k: v for k, v in match["metadata"].items() if k != "text"}
                )
                search_results.append(SearchResult(
                    document=doc,
                    score=match["score"]
                ))
            
            return search_results
        
        except Exception as e:
            logger.error(f"Failed to search Pinecone: {e}")
            raise
    
    async def delete(self, document_ids: List[str]) -> bool:
        """Delete documents from Pinecone"""
        if not self._initialized:
            await self.initialize()
        
        try:
            self._index.delete(ids=document_ids)
            logger.info(f"Deleted {len(document_ids)} documents from Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from Pinecone: {e}")
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document from Pinecone by ID"""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = self._index.fetch(ids=[document_id])
            if document_id in result.get("vectors", {}):
                vector_data = result["vectors"][document_id]
                return Document(
                    id=document_id,
                    text=vector_data["metadata"].get("text", ""),
                    metadata={k: v for k, v in vector_data["metadata"].items() if k != "text"}
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get document from Pinecone: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check Pinecone health"""
        try:
            if not self._initialized:
                await self.initialize()
            self._index.describe_index_stats()
            return True
        except Exception as e:
            logger.warning(f"Pinecone health check failed: {e}")
            return False
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts (placeholder)"""
        # In production, use OpenAI, Cohere, or local embedding model
        # For now, return dummy embeddings
        import random
        return [[random.random() for _ in range(self.dimension)] for _ in texts]


class WeaviateBackend(VectorStoreBackend):
    """Weaviate vector store implementation"""
    
    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        class_name: str = "Document",
        dimension: int = 1536
    ):
        self.url = url
        self.api_key = api_key
        self.class_name = class_name
        self.dimension = dimension
        self._client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Weaviate connection"""
        try:
            import weaviate  # type: ignore
            
            # Create Weaviate client
            auth_config = None
            if self.api_key:
                auth_config = weaviate.auth.AuthApiKey(api_key=self.api_key)
            
            self._client = weaviate.Client(
                url=self.url,
                auth_client_secret=auth_config
            )
        except ImportError:
            logger.error("weaviate-client not installed. Install with: pip install weaviate-client")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {e}")
            raise
            
            # Check if class exists, create if not
            if not self._client.schema.exists(self.class_name):
                self._client.schema.create_class({
                    "class": self.class_name,
                    "properties": [
                        {"name": "text", "dataType": ["text"]},
                        {"name": "metadata", "dataType": ["object"]}
                    ],
                    "vectorizer": "none"  # We'll provide our own embeddings
                })
                logger.info(f"Created Weaviate class: {self.class_name}")
            
            self._initialized = True
            logger.info(f"Weaviate backend initialized: {self.class_name}")
        
        except ImportError:
            logger.error("weaviate-client not installed. Install with: pip install weaviate-client")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {e}")
            raise
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to Weaviate"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate embeddings
            embeddings = await self._generate_embeddings([doc.text for doc in documents])
            
            # Batch import to Weaviate
            with self._client.batch as batch:
                for doc, embedding in zip(documents, embeddings):
                    batch.add_object(
                        class_name=self.class_name,
                        properties={
                            "text": doc.text,
                            "metadata": doc.metadata
                        },
                        vector=embedding
                    )
            
            logger.info(f"Added {len(documents)} documents to Weaviate")
            return [doc.id for doc in documents]
        
        except Exception as e:
            logger.error(f"Failed to add documents to Weaviate: {e}")
            raise
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search Weaviate for similar documents"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embeddings([query])
            query_embedding = query_embedding[0]
            
            # Build query
            near_vector = {"vector": query_embedding, "certainty": 0.7}
            
            # Execute search
            results = self._client.query.get(
                self.class_name,
                ["text", "metadata"]
            ).with_near_vector(near_vector).with_limit(top_k).do()
            
            # Convert to SearchResult objects
            search_results = []
            for result in results.get("data", {}).get("Get", {}).get(self.class_name, []):
                doc = Document(
                    id=result.get("_additional", {}).get("id", ""),
                    text=result.get("text", ""),
                    metadata=result.get("metadata", {})
                )
                search_results.append(SearchResult(
                    document=doc,
                    score=result.get("_additional", {}).get("certainty", 0)
                ))
            
            return search_results
        
        except Exception as e:
            logger.error(f"Failed to search Weaviate: {e}")
            raise
    
    async def delete(self, document_ids: List[str]) -> bool:
        """Delete documents from Weaviate"""
        if not self._initialized:
            await self.initialize()
        
        try:
            for doc_id in document_ids:
                self._client.data_object.delete(
                    doc_id,
                    class_name=self.class_name
                )
            logger.info(f"Deleted {len(document_ids)} documents from Weaviate")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from Weaviate: {e}")
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document from Weaviate by ID"""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = self._client.data_object.get_by_id(
                document_id,
                class_name=self.class_name
            )
            if result:
                return Document(
                    id=document_id,
                    text=result.get("text", ""),
                    metadata=result.get("metadata", {})
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get document from Weaviate: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check Weaviate health"""
        try:
            if not self._initialized:
                await self.initialize()
            self._client.schema.get()
            return True
        except Exception as e:
            logger.warning(f"Weaviate health check failed: {e}")
            return False
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts (placeholder)"""
        import random
        return [[random.random() for _ in range(self.dimension)] for _ in texts]


class ChromaBackend(VectorStoreBackend):
    """Chroma vector store implementation (local/embedded)"""
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "documents"
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._collection = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Chroma connection"""
        try:
            import chromadb  # type: ignore
            
            # Create Chroma client
            client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Get or create collection
            self._collection = client.get_or_create_collection(
                name=self.collection_name
            )
        except ImportError:
            logger.error("chromadb not installed. Install with: pip install chromadb")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise
            
            self._initialized = True
            logger.info(f"Chroma backend initialized: {self.collection_name}")
        
        except ImportError:
            logger.error("chromadb not installed. Install with: pip install chromadb")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to Chroma"""
        if not self._initialized:
            await self.initialize()
        
        try:
            ids = [doc.id for doc in documents]
            texts = [doc.text for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            
            self._collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(documents)} documents to Chroma")
            return ids
        
        except Exception as e:
            logger.error(f"Failed to add documents to Chroma: {e}")
            raise
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search Chroma for similar documents"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Query Chroma
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter
            )
            
            # Convert to SearchResult objects
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    doc = Document(
                        id=doc_id,
                        text=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                    )
                    # Chroma doesn't return scores by default, use 1.0
                    search_results.append(SearchResult(document=doc, score=1.0))
            
            return search_results
        
        except Exception as e:
            logger.error(f"Failed to search Chroma: {e}")
            raise
    
    async def delete(self, document_ids: List[str]) -> bool:
        """Delete documents from Chroma"""
        if not self._initialized:
            await self.initialize()
        
        try:
            self._collection.delete(ids=document_ids)
            logger.info(f"Deleted {len(document_ids)} documents from Chroma")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from Chroma: {e}")
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document from Chroma by ID"""
        if not self._initialized:
            await self.initialize()
        
        try:
            results = self._collection.get(ids=[document_id])
            if results["ids"]:
                return Document(
                    id=results["ids"][0],
                    text=results["documents"][0],
                    metadata=results["metadatas"][0] if results["metadatas"] else {}
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get document from Chroma: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check Chroma health"""
        try:
            if not self._initialized:
                await self.initialize()
            self._collection.count()
            return True
        except Exception as e:
            logger.warning(f"Chroma health check failed: {e}")
            return False


class VectorStore:
    """
    Main VectorStore class that provides a unified interface
    for working with different vector database backends
    """
    
    def __init__(self, backend: VectorStoreBackend):
        self.backend = backend
        self._initialized = False
    
    async def initialize(self):
        """Initialize the vector store"""
        if not self._initialized:
            await self.backend.initialize()
            self._initialized = True
    
    async def add_documents(self, documents: List[Union[Document, Dict[str, Any]]]) -> List[str]:
        """Add documents to the vector store"""
        await self.initialize()
        
        # Convert dicts to Document objects
        doc_objects = []
        for doc in documents:
            if isinstance(doc, dict):
                doc_objects.append(Document(
                    id=doc.get("id", str(hash(doc["text"]))),
                    text=doc["text"],
                    metadata=doc.get("metadata", {})
                ))
            else:
                doc_objects.append(doc)
        
        return await self.backend.add_documents(doc_objects)
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar documents"""
        await self.initialize()
        return await self.backend.search(query, top_k=top_k, filter=filter)
    
    async def delete(self, document_ids: List[str]) -> bool:
        """Delete documents"""
        await self.initialize()
        return await self.backend.delete(document_ids)
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        await self.initialize()
        return await self.backend.get_document(document_id)
    
    async def health_check(self) -> bool:
        """Check vector store health"""
        return await self.backend.health_check()


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> Optional[VectorStore]:
    """Get the singleton VectorStore instance"""
    global _vector_store
    
    if _vector_store is None:
        # Determine backend type from settings
        backend_type = getattr(settings, 'vector_store_type', 'chroma').lower()
        
        try:
            if backend_type == VectorStoreType.PINECONE.value:
                backend = PineconeBackend(
                    api_key=getattr(settings, 'pinecone_api_key', ''),
                    environment=getattr(settings, 'pinecone_environment', 'us-west1-gcp'),
                    index_name=getattr(settings, 'pinecone_index_name', 'ml-documents')
                )
            elif backend_type == VectorStoreType.WEAVIATE.value:
                backend = WeaviateBackend(
                    url=getattr(settings, 'weaviate_url', 'http://localhost:8080'),
                    api_key=getattr(settings, 'weaviate_api_key', None),
                    class_name=getattr(settings, 'weaviate_class_name', 'Document')
                )
            else:  # Default to Chroma
                backend = ChromaBackend(
                    persist_directory=getattr(settings, 'chroma_persist_dir', './chroma_db'),
                    collection_name=getattr(settings, 'chroma_collection_name', 'documents')
                )
            
            _vector_store = VectorStore(backend)
            logger.info(f"Vector store initialized with {backend_type} backend")
        
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            _vector_store = None
    
    return _vector_store
