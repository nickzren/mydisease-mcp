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

## Quick Start

1. **Install UV**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Setup**
   ```bash
   cd mydisease-mcp
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```

3. **Configure Claude Desktop**
   ```bash
   python scripts/configure_claude.py
   ```
   Then restart Claude Desktop.

## Usage

### Running the Server

```bash
mydisease-mcp
```

### Development

```bash
# Run tests
pytest tests/ -v
```
