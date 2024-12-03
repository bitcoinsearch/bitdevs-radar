# BitDevs Resource Radar

A discovery tool that monitors BitDevs meetups worldwide to surface relevant Bitcoin technical content by leveraging community curation.

BitDevs meetups naturally filter high-quality resources through their curated discussions of technical content. This tool complements other efforts in the discovery stage of [our data infrastructure](https://github.com/bitcoinsearch/infrastructure/wiki), which curates, processes, and provides access to the depths of bitcoin's technical ecosystem.

## Features

- Scans multiple BitDevs repositories
- Tracks resources across different categories based on context
- Identifies frequently referenced resources
- Provides [multiple organized views](#output-formats)
- Resources within each group are sorted by most recent occurrence date
- Handles multiple titles/references for the same resource
- Allows direct input of pre-existing JSON data for quick view generation

## Installation

1. Clone the repository:

```bash
git clone https://github.com/bitcoinsearch/bitdevs-radar.git
cd bitdevs-radar
```

2. Install requirements:

```bash
pip install -r requirements.txt
```

## Configuration

The tool uses two YAML configuration files:

1. `bitdevs.yaml`: Lists the BitDevs repositories to scan
2. `exclude_domains.yaml`: Specifies domains to exclude from tracking, helping focus on discovering new sources by filtering out domains that are already part of our regular monitoring process

## Usage

Run the tool with default settings:

```bash
python main.py
```

Filter by start date:

```bash
python main.py --start-date 2023-01-01
```

Use pre-existing JSON data to generate views:

```bash
python main.py --detailed-input bitdevs_resources.json
```

Enable debug logging:

```bash
python main.py --debug
```

## Output Formats

The tool generates four different views of the data:

### 1. Detailed JSON View (bitdevs_resources.json)

Provides complete reference data in JSON format:

```json
{
  "metadata": {
    "total_unique_urls": 150,
    "start_date": "2023-01-01",
    "excluded_domains": ["github.com/bitcoin/bitcoin", ...]
  },
  "resources": {
    "https://example.com/article": {
      "url": "https://example.com/article",
      "titles": ["Article Title", "Alternative Title"],
      "count": 3,
      "occurrences": [
        {
          "date": "2023-03-15",
          "source": "github.com/BitDevsNYC/...",
          "category": "Research / Layer 2",
          "title_used": "Article Title"
        }
      ]
    }
  }
}
```

### 2. Category-based Markdown View (bitdevs_resources.md)

Organizes resources by category and domain, with resources sorted by most recent occurrence:

```markdown
# Resources by Category

## Security/CVEs/InfoSec/Research

### arxiv.org

- ["Channel Balance Interpolation in the Lightning Network via Machine Learning"](https://arxiv.org/abs/2405.12087) (2 references)
- ["SoK: Bitcoin Layer Two (L2)"](https://arxiv.org/abs/2409.02650) (2 references)

### Other Resources

- ["BitVM2: Bridging Bitcoin to Second Layers"](https://bitvm.org/bitvm_bridge.pdf)
- ["Bitcoin research price by Chaincode labs"](https://brd.chaincode.com/prize)

...
```

### 3. Domain-focused View (bitdevs_domains.md)

Groups resources by root domain with statistics:

```markdown
# Resources by Domain

## b10c.me (12 resources, 16 total references)

- ["Block Template Similarities between Mining Pools"](https://b10c.me/observations/12-template-similarity/) (3 references) (Category: Network Data)
- ["Vulnerability Disclosure: Wasting ViaBTC's 60 EH/s hashrate"](https://b10c.me/blog/012-viabtc-spv-vulnerability-disclosure/) (2 references) (Category: CVEs and Research / InfoSec)
```

### 4. Date-focused View (bitdevs_dates.md)

Organizes resources by month, with domain subgroups:

```markdown
# Resources by Date

## December 2024

### b10c.me

- ["Block Template Similarities between Mining Pools"](https://b10c.me/observations/12-template-similarity/) (3 references) (Category: Network Data)
- ["Vulnerability Disclosure: Wasting ViaBTC's 60 EH/s hashrate"](https://b10c.me/blog/012-viabtc-spv-vulnerability-disclosure/) (2 references) (Category: CVEs and Research / InfoSec)

### Other Resources

- ["BitVM2: Bridging Bitcoin to Second Layers"](https://bitvm.org/bitvm_bridge.pdf) (Category: Research, Domain: bitvm.org)
```

Note: In the date view, resources from domains with 5 or fewer entries are grouped under "Other Resources" for better organization.
