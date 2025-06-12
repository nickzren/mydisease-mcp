# MyDisease MCP Server

A Model Context Protocol (MCP) server that provides access to the [MyDisease.info API](https://mydisease.info/).

## Features

### Core Capabilities
- **Disease Search**: Search by name, ID, symptom, or any text field
- **Gene Associations**: Find diseases associated with specific genes
- **Variant Analysis**: Get disease associations for genetic variants
- **Phenotype Mapping**: Search diseases by HPO terms and clinical features
- **Clinical Data**: Access ClinVar annotations and clinical significance
- **Disease Ontology**: Navigate disease classifications and relationships
- **GWAS Data**: Explore genome-wide association studies
- **Pathway Analysis**: Find diseases affecting specific biological pathways
- **Drug Information**: Get treatment options and drug-disease relationships
- **Epidemiology**: Access prevalence, incidence, and demographic data
- **Batch Processing**: Query up to 1000 diseases in a single request
- **Data Export**: Export results in TSV, CSV, JSON, or Markdown formats

### Data Sources
- **OMIM**: Online Mendelian Inheritance in Man
- **Orphanet**: Rare disease database
- **DisGeNET**: Gene-disease associations
- **ClinVar**: Clinical variant interpretations
- **HPO**: Human Phenotype Ontology
- **GWAS Catalog**: NHGRI-EBI GWAS studies
- **CTD**: Comparative Toxicogenomics Database
- **KEGG**: Disease pathways
- **UniProt**: Protein-disease associations

## Installation

```bash
git clone https://github.com/yourusername/mydisease-mcp
cd mydisease-mcp
mamba env create -f environment.yml
mamba activate mydisease-mcp
```

## Usage

### As an MCP Server

```bash
mydisease-mcp
```

### Configure with Claude Desktop

```bash
python scripts/configure_claude.py
```
