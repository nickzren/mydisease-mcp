"""Disease identifier mapping tools."""

from typing import Any, Dict, List, Optional
import mcp.types as types
from ..client import MyDiseaseClient, MyDiseaseError


class MappingApi:
    """Tools for mapping between disease identifiers."""
    
    async def map_disease_ids(
        self,
        client: MyDiseaseClient,
        input_ids: List[str],
        from_type: str,
        to_types: List[str],
        missing_ok: bool = True
    ) -> Dict[str, Any]:
        """Map disease identifiers from one type to others.
        
        Supported ID types:
        - mondo: MONDO ID
        - omim: OMIM number
        - orphanet: Orphanet ID
        - doid: Disease Ontology ID
        - umls: UMLS CUI
        - mesh: MeSH ID
        - icd10: ICD-10 code
        - icd11: ICD-11 code
        - hp: HPO ID (for phenotypes)
        """
        # Define field mappings
        field_map = {
            "mondo": "mondo.mondo,mondo.id",
            "omim": "omim",
            "orphanet": "orphanet.id,orphanet.orphanet",
            "doid": "disease_ontology.doid",
            "umls": "umls.cui",
            "mesh": "mesh",
            "icd10": "icd10",
            "icd11": "icd11",
            "hp": "hpo.hpo_id"
        }
        
        # Build scope for searching
        scope = field_map.get(from_type)
        if not scope:
            raise MyDiseaseError(f"Unsupported from_type: {from_type}")
        
        # Build fields to return
        return_fields = ["_id", "name"]
        for to_type in to_types:
            if to_type in field_map:
                return_fields.append(field_map[to_type])
        
        # Query for all identifiers
        post_data = {
            "ids": input_ids,
            "scopes": scope,
            "fields": ",".join(return_fields)
        }
        
        results = await client.post("query", post_data)
        
        # Process results
        mappings = []
        unmapped = []
        
        for result in results:
            if result.get("found", False):
                mapping = {
                    "input": result.get("query"),
                    "from_type": from_type,
                    "disease_name": result.get("name"),
                    "mappings": {}
                }
                
                # Extract each requested identifier type
                for to_type in to_types:
                    value = None
                    
                    if to_type == "mondo":
                        if "mondo" in result:
                            mondo = result["mondo"]
                            value = mondo.get("mondo") or mondo.get("id")
                    elif to_type == "omim":
                        value = result.get("omim")
                    elif to_type == "orphanet":
                        if "orphanet" in result:
                            orph = result["orphanet"]
                            value = orph.get("id") or orph.get("orphanet")
                    elif to_type == "doid":
                        if "disease_ontology" in result:
                            value = result["disease_ontology"].get("doid")
                    elif to_type == "umls":
                        if "umls" in result:
                            value = result["umls"].get("cui")
                    elif to_type == "mesh":
                        value = result.get("mesh")
                    elif to_type == "icd10":
                        value = result.get("icd10")
                    elif to_type == "icd11":
                        value = result.get("icd11")
                    elif to_type == "hp":
                        if "hpo" in result:
                            hpo = result["hpo"]
                            if isinstance(hpo, list) and hpo:
                                value = hpo[0].get("hpo_id")
                            elif isinstance(hpo, dict):
                                value = hpo.get("hpo_id")
                    
                    if value:
                        mapping["mappings"][to_type] = value
                
                mappings.append(mapping)
            else:
                unmapped.append(result.get("query", "Unknown"))
        
        return {
            "success": True,
            "total_input": len(input_ids),
            "mapped": len(mappings),
            "unmapped": len(unmapped),
            "mappings": mappings,
            "unmapped_ids": unmapped
        }
    
    async def validate_disease_ids(
        self,
        client: MyDiseaseClient,
        identifiers: List[str],
        identifier_type: str
    ) -> Dict[str, Any]:
        """Validate a list of disease identifiers."""
        # Use mapping to check validity
        result = await self.map_disease_ids(
            client=client,
            input_ids=identifiers,
            from_type=identifier_type,
            to_types=["mondo"],  # Just need to check if found
            missing_ok=True
        )
        
        valid = []
        invalid = []
        
        for mapping in result["mappings"]:
            valid.append({
                "identifier": mapping["input"],
                "disease_name": mapping["disease_name"],
                "mondo_id": mapping["mappings"].get("mondo")
            })
        
        invalid = result.get("unmapped_ids", [])
        
        return {
            "success": True,
            "identifier_type": identifier_type,
            "total": len(identifiers),
            "valid_count": len(valid),
            "invalid_count": len(invalid),
            "valid_identifiers": valid,
            "invalid_identifiers": invalid
        }
    
    async def find_common_diseases(
        self,
        client: MyDiseaseClient,
        identifier_lists: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Find diseases common across multiple identifier lists.
        
        Example input:
        {
            "omim_ids": ["104300", "114480"],
            "orphanet_ids": ["ORPHA:15", "ORPHA:166"]
        }
        """
        all_diseases = {}
        
        # Map all identifiers to internal disease IDs
        for id_type, id_list in identifier_lists.items():
            # Determine the identifier type
            if "omim" in id_type.lower():
                from_type = "omim"
            elif "orphanet" in id_type.lower():
                from_type = "orphanet"
            elif "mondo" in id_type.lower():
                from_type = "mondo"
            elif "doid" in id_type.lower() or "disease_ontology" in id_type.lower():
                from_type = "doid"
            elif "umls" in id_type.lower():
                from_type = "umls"
            elif "icd10" in id_type.lower():
                from_type = "icd10"
            else:
                raise ValueError(f"Cannot determine identifier type from: {id_type}")
            
            mapping_result = await self.map_disease_ids(
                client=client,
                input_ids=id_list,
                from_type=from_type,
                to_types=["mondo", "omim", "orphanet"]
            )
            
            for mapping in mapping_result["mappings"]:
                # Use internal _id or MONDO as canonical ID
                disease_id = mapping.get("_id") or mapping["mappings"].get("mondo")
                if disease_id:
                    if disease_id not in all_diseases:
                        all_diseases[disease_id] = {
                            "name": mapping["disease_name"],
                            "found_in": []
                        }
                    all_diseases[disease_id]["found_in"].append({
                        "list": id_type,
                        "identifier": mapping["input"]
                    })
        
        # Find common diseases
        common_diseases = []
        list_names = list(identifier_lists.keys())
        
        for disease_id, data in all_diseases.items():
            found_lists = [item["list"] for item in data["found_in"]]
            if all(list_name in found_lists for list_name in list_names):
                common_diseases.append({
                    "disease_id": disease_id,
                    "disease_name": data["name"],
                    "identifiers": data["found_in"]
                })
        
        return {
            "success": True,
            "input_lists": list_names,
            "total_unique_diseases": len(all_diseases),
            "common_diseases_count": len(common_diseases),
            "common_diseases": common_diseases
        }


MAPPING_TOOLS = [
    types.Tool(
        name="map_disease_ids",
        description="Map disease identifiers from one type to others (MONDO, OMIM, Orphanet, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "input_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of input identifiers"
                },
                "from_type": {
                    "type": "string",
                    "enum": ["mondo", "omim", "orphanet", "doid", "umls", "mesh", "icd10", "icd11", "hp"],
                    "description": "Type of input identifiers"
                },
                "to_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["mondo", "omim", "orphanet", "doid", "umls", "mesh", "icd10", "icd11", "hp"]
                    },
                    "description": "Types to map to"
                },
                "missing_ok": {
                    "type": "boolean",
                    "description": "Include unmapped IDs in response",
                    "default": True
                }
            },
            "required": ["input_ids", "from_type", "to_types"]
        }
    ),
    types.Tool(
        name="validate_disease_ids",
        description="Validate a list of disease identifiers",
        inputSchema={
            "type": "object",
            "properties": {
                "identifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of identifiers to validate"
                },
                "identifier_type": {
                    "type": "string",
                    "enum": ["mondo", "omim", "orphanet", "doid", "umls", "mesh", "icd10", "icd11"],
                    "description": "Type of identifiers"
                }
            },
            "required": ["identifiers", "identifier_type"]
        }
    ),
    types.Tool(
        name="find_common_diseases",
        description="Find diseases common across multiple identifier lists",
        inputSchema={
            "type": "object",
            "properties": {
                "identifier_lists": {
                    "type": "object",
                    "description": "Named lists of identifiers (e.g., {'omim_ids': [...], 'orphanet_ids': [...]})"
                }
            },
            "required": ["identifier_lists"]
        }
    )
]