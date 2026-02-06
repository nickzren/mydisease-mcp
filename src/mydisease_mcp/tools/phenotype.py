"""Phenotype and clinical feature tools."""

from typing import Any, Dict, Optional, List
import mcp.types as types
from ..client import MyDiseaseClient
from ._query_utils import quote_lucene_phrase


class PhenotypeApi:
    """Tools for phenotype and clinical features."""
    
    async def get_disease_phenotypes(
        self,
        client: MyDiseaseClient,
        disease_id: str,
        include_frequency: bool = True
    ) -> Dict[str, Any]:
        """Get phenotypes/clinical features for a disease."""
        params = {
            "fields": "hpo,phenotype_related_to_disease,clinical_features"
        }
        
        result = await client.get(f"disease/{disease_id}", params=params)
        
        phenotypes = {
            "disease_id": disease_id,
            "hpo_phenotypes": [],
            "clinical_features": []
        }
        
        # Extract HPO phenotypes
        if "hpo" in result:
            hpo_data = result["hpo"]
            if isinstance(hpo_data, list):
                phenotypes["hpo_phenotypes"] = hpo_data
            elif isinstance(hpo_data, dict) and "phenotype" in hpo_data:
                phenotypes["hpo_phenotypes"] = hpo_data["phenotype"]
        
        # Extract phenotype relations
        if "phenotype_related_to_disease" in result:
            pheno_rel = result["phenotype_related_to_disease"]
            pheno_rel = pheno_rel if isinstance(pheno_rel, list) else [pheno_rel]
            
            for rel in pheno_rel:
                phenotypes["clinical_features"].append({
                    "hpo_id": rel.get("hpo_id"),
                    "hpo_term": rel.get("hpo_phenotype"),
                    "frequency": rel.get("frequency") if include_frequency else None,
                    "source": rel.get("source")
                })
        
        # Extract general clinical features
        if "clinical_features" in result:
            features = result["clinical_features"]
            features = features if isinstance(features, list) else [features]
            phenotypes["clinical_features"].extend(features)
        
        return {
            "success": True,
            "phenotypes": phenotypes
        }
    
    async def search_by_hpo_term(
        self,
        client: MyDiseaseClient,
        hpo_id: str,
        include_descendants: bool = False,
        size: int = 20
    ) -> Dict[str, Any]:
        """Search diseases by HPO term."""
        # Build query
        hpo_term = quote_lucene_phrase(hpo_id)
        if hpo_id.startswith("HP:"):
            q = f"hpo.hpo_id:{hpo_term} OR phenotype_related_to_disease.hpo_id:{hpo_term}"
        else:
            q = (
                f"hpo.phenotype_name:{hpo_term} "
                f"OR phenotype_related_to_disease.hpo_phenotype:{hpo_term}"
            )
        
        params = {
            "q": q,
            "fields": "_id,name,hpo,phenotype_related_to_disease",
            "size": size
        }
        
        result = await client.get("query", params=params)
        
        # Process results
        diseases = []
        for hit in result.get("hits", []):
            disease_info = {
                "disease_id": hit.get("_id"),
                "disease_name": hit.get("name"),
                "phenotype_matches": []
            }
            
            # Check HPO matches
            if "hpo" in hit:
                hpo = hit["hpo"]
                if isinstance(hpo, dict) and hpo.get("hpo_id") == hpo_id:
                    disease_info["phenotype_matches"].append({
                        "source": "hpo",
                        "hpo_id": hpo_id,
                        "match_type": "exact"
                    })
                elif isinstance(hpo, list):
                    for item in hpo:
                        if item.get("hpo_id") == hpo_id or item.get("phenotype_name") == hpo_id:
                            disease_info["phenotype_matches"].append({
                                "source": "hpo",
                                "hpo_id": item.get("hpo_id"),
                                "match_type": "exact"
                            })
            
            # Check phenotype relations
            if "phenotype_related_to_disease" in hit:
                relations = hit["phenotype_related_to_disease"]
                relations = relations if isinstance(relations, list) else [relations]
                
                for rel in relations:
                    if rel.get("hpo_id") == hpo_id or rel.get("hpo_phenotype") == hpo_id:
                        disease_info["phenotype_matches"].append({
                            "source": "phenotype_relation",
                            "hpo_id": rel.get("hpo_id"),
                            "frequency": rel.get("frequency"),
                            "match_type": "exact"
                        })
            
            if disease_info["phenotype_matches"]:
                diseases.append(disease_info)
        
        return {
            "success": True,
            "hpo_term": hpo_id,
            "total_diseases": len(diseases),
            "diseases": diseases
        }
    
    async def get_phenotype_similarity(
        self,
        client: MyDiseaseClient,
        phenotype_list: List[str],
        algorithm: str = "jaccard",
        min_similarity: float = 0.5,
        size: int = 20
    ) -> Dict[str, Any]:
        """Find diseases with similar phenotype profiles."""
        # First, search for diseases with any of the phenotypes
        phenotype_queries = []
        for phenotype in phenotype_list:
            phenotype_term = quote_lucene_phrase(phenotype)
            if phenotype.startswith("HP:"):
                phenotype_queries.append(f"hpo.hpo_id:{phenotype_term}")
                phenotype_queries.append(f"phenotype_related_to_disease.hpo_id:{phenotype_term}")
            else:
                phenotype_queries.append(f"hpo.phenotype_name:{phenotype_term}")
                phenotype_queries.append(
                    f"phenotype_related_to_disease.hpo_phenotype:{phenotype_term}"
                )
        
        q = " OR ".join(phenotype_queries)
        
        params = {
            "q": q,
            "fields": "_id,name,hpo,phenotype_related_to_disease",
            "size": 100  # Get more results for similarity calculation
        }
        
        result = await client.get("query", params=params)
        
        # Calculate similarity scores
        disease_scores = []
        
        for hit in result.get("hits", []):
            disease_phenotypes = set()
            
            # Extract all phenotypes for this disease
            if "hpo" in hit:
                hpo = hit["hpo"]
                if isinstance(hpo, dict):
                    disease_phenotypes.add(hpo.get("hpo_id") or hpo.get("phenotype_name"))
                elif isinstance(hpo, list):
                    for h in hpo:
                        disease_phenotypes.add(h.get("hpo_id") or h.get("phenotype_name"))
            
            if "phenotype_related_to_disease" in hit:
                relations = hit["phenotype_related_to_disease"]
                relations = relations if isinstance(relations, list) else [relations]
                for rel in relations:
                    disease_phenotypes.add(rel.get("hpo_id") or rel.get("hpo_phenotype"))
            
            # Calculate similarity
            if algorithm == "jaccard":
                intersection = len(set(phenotype_list) & disease_phenotypes)
                union = len(set(phenotype_list) | disease_phenotypes)
                similarity = intersection / union if union > 0 else 0
            else:  # dice
                intersection = len(set(phenotype_list) & disease_phenotypes)
                similarity = (2 * intersection) / (len(phenotype_list) + len(disease_phenotypes))
            
            if similarity >= min_similarity:
                disease_scores.append({
                    "disease_id": hit.get("_id"),
                    "disease_name": hit.get("name"),
                    "similarity_score": round(similarity, 3),
                    "matching_phenotypes": list(set(phenotype_list) & disease_phenotypes),
                    "total_phenotypes": len(disease_phenotypes)
                })
        
        # Sort by similarity
        disease_scores.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return {
            "success": True,
            "query_phenotypes": phenotype_list,
            "algorithm": algorithm,
            "min_similarity": min_similarity,
            "total_matches": len(disease_scores),
            "diseases": disease_scores[:size]
        }
    
    async def get_phenotype_frequency(
        self,
        client: MyDiseaseClient,
        disease_id: str,
        phenotype_id: str
    ) -> Dict[str, Any]:
        """Get frequency information for a phenotype in a disease."""
        params = {
            "fields": "phenotype_related_to_disease,hpo"
        }
        
        result = await client.get(f"disease/{disease_id}", params=params)
        
        frequency_data = {
            "disease_id": disease_id,
            "phenotype_id": phenotype_id,
            "frequency_info": None
        }
        
        # Check phenotype relations
        if "phenotype_related_to_disease" in result:
            relations = result["phenotype_related_to_disease"]
            relations = relations if isinstance(relations, list) else [relations]
            
            for rel in relations:
                if rel.get("hpo_id") == phenotype_id or rel.get("hpo_phenotype") == phenotype_id:
                    frequency_data["frequency_info"] = {
                        "frequency": rel.get("frequency"),
                        "frequency_hp": rel.get("frequency_hp"),
                        "source": rel.get("source"),
                        "evidence": rel.get("evidence")
                    }
                    break
        
        return {
            "success": True,
            "frequency": frequency_data
        }


PHENOTYPE_TOOLS = [
    types.Tool(
        name="get_disease_phenotypes",
        description="Get phenotypes and clinical features for a disease",
        inputSchema={
            "type": "object",
            "properties": {
                "disease_id": {
                    "type": "string",
                    "description": "Disease ID"
                },
                "include_frequency": {
                    "type": "boolean",
                    "description": "Include frequency information",
                    "default": True
                }
            },
            "required": ["disease_id"]
        }
    ),
    types.Tool(
        name="search_by_hpo_term",
        description="Search diseases by HPO (Human Phenotype Ontology) term",
        inputSchema={
            "type": "object",
            "properties": {
                "hpo_id": {
                    "type": "string",
                    "description": "HPO ID (e.g., 'HP:0001250') or term name"
                },
                "include_descendants": {
                    "type": "boolean",
                    "description": "Include descendant terms",
                    "default": False
                },
                "size": {
                    "type": "integer",
                    "description": "Number of results",
                    "default": 20
                }
            },
            "required": ["hpo_id"]
        }
    ),
    types.Tool(
        name="get_phenotype_similarity",
        description="Find diseases with similar phenotype profiles",
        inputSchema={
            "type": "object",
            "properties": {
                "phenotype_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of phenotypes (HPO IDs or terms)"
                },
                "algorithm": {
                    "type": "string",
                    "description": "Similarity algorithm",
                    "default": "jaccard",
                    "enum": ["jaccard", "dice"]
                },
                "min_similarity": {
                    "type": "number",
                    "description": "Minimum similarity score (0-1)",
                    "default": 0.5
                },
                "size": {
                    "type": "integer",
                    "description": "Number of results",
                    "default": 20
                }
            },
            "required": ["phenotype_list"]
        }
    ),
    types.Tool(
        name="get_phenotype_frequency",
        description="Get frequency information for a phenotype in a disease",
        inputSchema={
            "type": "object",
            "properties": {
                "disease_id": {
                    "type": "string",
                    "description": "Disease ID"
                },
                "phenotype_id": {
                    "type": "string",
                    "description": "Phenotype ID (HPO ID or term)"
                }
            },
            "required": ["disease_id", "phenotype_id"]
        }
    )
]
