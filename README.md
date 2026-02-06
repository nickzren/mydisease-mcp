# MyDisease MCP Server
[![CI](https://github.com/nickzren/mydisease-mcp/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/nickzren/mydisease-mcp/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastMCP 2.14.5](https://img.shields.io/badge/FastMCP-2.14.5-4B32C3)](https://github.com/jlowin/fastmcp)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-0A7B83)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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

## Prerequisites

- Python 3.12+ with pip

## Quick Start

### 1. Install UV
UV is a fast Python package and project manager.

```bash
pip install uv
```

### 2. Install MCPM (MCP Manager)
MCPM is a package manager for MCP servers that simplifies installation and configuration.

```bash
pip install mcpm
```

### 3. Setup the MCP Server
```bash
cd mydisease-mcp
uv sync
```

### 4. Add the Server to Claude Desktop
```bash
# Make sure you're in the project directory
cd mydisease-mcp

# Set Claude as the target client
mcpm target set @claude-desktop

# Add the MyDisease MCP server
mcpm import stdio mydisease \
  --command "$(uv run which python)" \
  --args "-m mydisease_mcp.server"
```
Then restart Claude Desktop.

## Usage

### Running the Server

```bash
uv run python -m mydisease_mcp.server
```

You can choose a specific transport when starting the FastMCP server:

```bash
uv run python -m mydisease_mcp.server --transport stdio        # default (Claude Desktop)
uv run python -m mydisease_mcp.server --transport sse --host 0.0.0.0 --port 8000
uv run python -m mydisease_mcp.server --transport http --host 0.0.0.0 --port 8000
```

When running with `--transport sse` or `--transport http`, the server exposes a discovery document at `/.well-known/mcp.json` and a health check at `/`.

### Development

```bash
# Run tests
uv run --extra test pytest tests/ -v
```
