"""MyDisease MCP Server implementation."""

import asyncio
import json
from typing import Any, Dict, Optional
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from .client import MyDiseaseClient
from .tools import (
    QUERY_TOOLS, QueryApi,
    ANNOTATION_TOOLS, AnnotationApi,
    BATCH_TOOLS, BatchApi,
    GENE_ASSOCIATION_TOOLS, GeneAssociationApi,
    VARIANT_TOOLS, VariantApi,
    PHENOTYPE_TOOLS, PhenotypeApi,
    CLINICAL_TOOLS, ClinicalApi,
    ONTOLOGY_TOOLS, OntologyApi,
    GWAS_TOOLS, GWASApi,
    PATHWAY_TOOLS, PathwayApi,
    DRUG_TOOLS, DrugApi,
    EPIDEMIOLOGY_TOOLS, EpidemiologyApi,
    EXPORT_TOOLS, ExportApi,
    MAPPING_TOOLS, MappingApi,
    METADATA_TOOLS, MetadataApi
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Combine all tools
ALL_TOOLS = (
    QUERY_TOOLS +
    ANNOTATION_TOOLS +
    BATCH_TOOLS +
    GENE_ASSOCIATION_TOOLS +
    VARIANT_TOOLS +
    PHENOTYPE_TOOLS +
    CLINICAL_TOOLS +
    ONTOLOGY_TOOLS +
    GWAS_TOOLS +
    PATHWAY_TOOLS +
    DRUG_TOOLS +
    EPIDEMIOLOGY_TOOLS +
    EXPORT_TOOLS +
    MAPPING_TOOLS +
    METADATA_TOOLS
)

# Create API class mapping
API_CLASS_MAP = {
    # Query tools
    "search_disease": QueryApi,
    "search_by_field": QueryApi,
    "get_field_statistics": QueryApi,
    "search_by_phenotype": QueryApi,
    "build_complex_query": QueryApi,
    # Annotation tools
    "get_disease_by_id": AnnotationApi,
    # Batch tools
    "batch_query_diseases": BatchApi,
    "batch_get_diseases": BatchApi,
    # Gene association tools
    "get_diseases_by_gene": GeneAssociationApi,
    "get_disease_genes": GeneAssociationApi,
    "search_by_gene_panel": GeneAssociationApi,
    "get_gene_disease_score": GeneAssociationApi,
    # Variant tools
    "get_diseases_by_variant": VariantApi,
    "get_disease_variants": VariantApi,
    "get_variant_pathogenicity": VariantApi,
    "search_by_variant_type": VariantApi,
    # Phenotype tools
    "get_disease_phenotypes": PhenotypeApi,
    "search_by_hpo_term": PhenotypeApi,
    "get_phenotype_similarity": PhenotypeApi,
    "get_phenotype_frequency": PhenotypeApi,
    # Clinical tools
    "get_clinical_significance": ClinicalApi,
    "get_diagnostic_criteria": ClinicalApi,
    "get_disease_prognosis": ClinicalApi,
    "get_treatment_options": ClinicalApi,
    "get_clinical_trials": ClinicalApi,
    # Ontology tools
    "get_disease_ontology": OntologyApi,
    "get_disease_classification": OntologyApi,
    "get_related_diseases": OntologyApi,
    "navigate_disease_hierarchy": OntologyApi,
    # GWAS tools
    "get_gwas_associations": GWASApi,
    "search_gwas_by_trait": GWASApi,
    "get_gwas_variants": GWASApi,
    "get_gwas_statistics": GWASApi,
    # Pathway tools
    "get_disease_pathways": PathwayApi,
    "search_diseases_by_pathway": PathwayApi,
    "get_pathway_genes": PathwayApi,
    "get_pathway_enrichment": PathwayApi,
    # Drug tools
    "get_disease_drugs": DrugApi,
    "search_drugs_by_indication": DrugApi,
    "get_drug_targets": DrugApi,
    "get_pharmacogenomics": DrugApi,
    # Epidemiology tools
    "get_disease_prevalence": EpidemiologyApi,
    "get_disease_incidence": EpidemiologyApi,
    "get_demographic_data": EpidemiologyApi,
    "get_geographic_distribution": EpidemiologyApi,
    # Export tools
    "export_disease_list": ExportApi,
    "export_disease_comparison": ExportApi,
    "export_gene_disease_matrix": ExportApi,
    "export_phenotype_profile": ExportApi,
    # Mapping tools
    "map_disease_ids": MappingApi,
    "validate_disease_ids": MappingApi,
    "find_common_diseases": MappingApi,
    # Metadata tools
    "get_mydisease_metadata": MetadataApi,
    "get_available_fields": MetadataApi,
    "get_database_statistics": MetadataApi
}


class MyDiseaseMcpServer:
    """MCP Server for MyDisease.info data."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.server_name = "mydisease-mcp"
        self.server_version = "0.1.0"
        self.config = config or {}
        self.mcp_server = Server(self.server_name, self.server_version)
        
        # Initialize client with configuration
        self.client = MyDiseaseClient(
            timeout=self.config.get("timeout", 30.0),
            cache_enabled=self.config.get("cache_enabled", True),
            cache_ttl=self.config.get("cache_ttl", 3600),
            rate_limit=self.config.get("rate_limit", 10)
        )
        
        self._api_instances: Dict[type, Any] = {}
        self._setup_handlers()
        logger.info(f"{self.server_name} v{self.server_version} initialized.")
    
    def _setup_handlers(self):
        """Register MCP handlers."""
        
        @self.mcp_server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """Returns the list of all available tools."""
            logger.info(f"Listing {len(ALL_TOOLS)} available tools")
            return ALL_TOOLS
        
        @self.mcp_server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> list[types.TextContent]:
            """Handles a tool call request."""
            logger.info(f"Handling call for tool: '{name}' with args: {list(arguments.keys())}")
            
            try:
                if name not in API_CLASS_MAP:
                    raise ValueError(f"Unknown tool: {name}")
                
                api_class = API_CLASS_MAP[name]
                
                if api_class not in self._api_instances:
                    self._api_instances[api_class] = api_class()
                
                api_instance = self._api_instances[api_class]
                
                if not hasattr(api_instance, name):
                    raise ValueError(f"Tool method '{name}' not found")
                
                func_to_call = getattr(api_instance, name)
                result_data = await func_to_call(self.client, **arguments)
                
                # Handle export tools that return strings directly
                if isinstance(result_data, str):
                    return [types.TextContent(type="text", text=result_data)]
                
                result_json = json.dumps(result_data, indent=2)
                return [types.TextContent(type="text", text=result_json)]
            
            except Exception as e:
                logger.error(f"Error calling tool '{name}': {str(e)}", exc_info=True)
                error_response = {
                    "error": type(e).__name__,
                    "message": str(e),
                    "tool_name": name
                }
                return [types.TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    async def run(self):
        """Starts the MCP server."""
        logger.info(f"Starting {self.server_name} v{self.server_version}...")
        logger.info(f"Configuration: cache_enabled={self.config.get('cache_enabled', True)}, "
                   f"rate_limit={self.config.get('rate_limit', 10)}/s")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.mcp_server.run(
                read_stream, 
                write_stream,
                self.mcp_server.create_initialization_options()
            )


def main():
    """Main entry point with optional configuration."""
    import os
    
    # Load configuration from environment variables
    config = {
        "cache_enabled": os.environ.get("MYDISEASE_CACHE_ENABLED", "true").lower() == "true",
        "cache_ttl": int(os.environ.get("MYDISEASE_CACHE_TTL", "3600")),
        "rate_limit": int(os.environ.get("MYDISEASE_RATE_LIMIT", "10")),
        "timeout": float(os.environ.get("MYDISEASE_TIMEOUT", "30.0"))
    }
    
    server = MyDiseaseMcpServer(config)
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user.")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()