from urllib.parse import urlparse
from collections import defaultdict
from typing import Dict
from datetime import datetime
import json
from loguru import logger


def get_most_common_category(resource: Dict) -> str:
    """Determine the most common category for a resource."""
    category_counts = defaultdict(int)
    for occurrence in resource["occurrences"]:
        category_counts[occurrence["category"]] += 1
    most_common = max(category_counts.items(), key=lambda x: x[1])[0]
    logger.trace(f"Most common category for resource: {most_common}")
    return most_common


def get_domain(url: str) -> str:
    """Extract and clean domain from URL."""
    domain = urlparse(url).netloc
    clean_domain = domain.replace("www.", "")
    logger.trace(f"Extracted domain {clean_domain} from {url}")
    return clean_domain


def format_reference_count(count: int) -> str:
    """Format the reference count string."""
    if count == 1:
        return ""
    return f" ({count} references)"


def get_latest_date(resource: Dict) -> datetime:
    """Get the most recent occurrence date for a resource."""
    return max(
        datetime.strptime(occ["date"], "%Y-%m-%d") for occ in resource["occurrences"]
    )


def write_metadata_section(f, data: Dict):
    """Write metadata section at the top of the markdown file."""
    logger.debug("Writing metadata section")
    total_resources = len(data["resources"])
    total_references = sum(resource["count"] for resource in data["resources"].values())

    # Calculate date range
    all_dates = [
        datetime.strptime(occ["date"], "%Y-%m-%d")
        for resource in data["resources"].values()
        for occ in resource["occurrences"]
    ]
    start_date = min(all_dates).strftime("%Y-%m-%d")
    end_date = max(all_dates).strftime("%Y-%m-%d")

    # Calculate unique domains
    domains = {get_domain(url) for url in data["resources"].keys()}

    logger.info(
        f"Metadata summary: {total_resources} resources, {total_references} references, {len(domains)} domains"
    )

    f.write("# BitDevs Resources Report\n\n")
    f.write("## Metadata\n\n")
    f.write(f"- **Total Unique Resources**: {total_resources}\n")
    f.write(f"- **Total References**: {total_references}\n")
    f.write(f"- **Date Range**: {start_date} to {end_date}\n")
    f.write(f"- **Unique Domains**: {len(domains)}\n")
    if data["metadata"].get("excluded_domains"):
        f.write("- **Excluded Domains**:\n")
        for domain in sorted(data["metadata"]["excluded_domains"]):
            f.write(f"  - {domain}\n")


def generate_domain_view(data: Dict, output_file: str):
    """Generate a view organized by root domains."""
    logger.info(f"Generating domain view to {output_file}")

    # Group resources by domain
    domain_resources = defaultdict(list)
    domain_stats = defaultdict(lambda: {"total_refs": 0, "unique_resources": 0})

    for url, resource in data["resources"].items():
        domain = get_domain(url)
        latest_date = get_latest_date(resource)
        domain_resources[domain].append(
            {
                "url": url,
                "titles": resource["titles"],
                "count": resource["count"],
                "category": get_most_common_category(resource),
                "latest_date": latest_date,
            }
        )
        domain_stats[domain]["total_refs"] += resource["count"]
        domain_stats[domain]["unique_resources"] += 1

    # Sort domains by total references
    sorted_domains = sorted(
        domain_stats.items(),
        key=lambda x: (x[1]["total_refs"], x[1]["unique_resources"]),
        reverse=True,
    )

    logger.debug(f"Processing {len(sorted_domains)} domains")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # Write metadata section
            write_metadata_section(f, data)

            f.write("# Resources by Domain\n\n")

            for domain, stats in sorted_domains:
                logger.debug(f"Writing domain section: {domain}")
                f.write(
                    f"## {domain} ({stats['unique_resources']} resources, {stats['total_refs']} total references)\n\n"
                )

                # Sort resources by latest date
                resources = sorted(
                    domain_resources[domain],
                    key=lambda x: x["latest_date"],
                    reverse=True,
                )

                # Write all resources directly
                for resource in resources:
                    titles_str = " | ".join(
                        f'"{title}"' for title in resource["titles"]
                    )
                    ref_count = format_reference_count(resource["count"])
                    f.write(
                        f"- [{titles_str}]({resource['url']}){ref_count} "
                        f"(Category: {resource['category']})\n"
                    )
                f.write("\n")

        logger.success(f"Successfully generated domain view at {output_file}")
    except Exception as e:
        logger.error(f"Error generating domain view: {e}")
        raise


def generate_date_view(data: Dict, output_file: str):
    """Generate a view organized by date and then by domain."""
    logger.info(f"Generating date view to {output_file}")

    # Group resources by month and domain
    monthly_resources = defaultdict(lambda: defaultdict(list))

    for url, resource in data["resources"].items():
        latest_date = get_latest_date(resource)
        month_key = latest_date.strftime("%Y-%m")
        domain = get_domain(url)

        monthly_resources[month_key][domain].append(
            {
                "url": url,
                "titles": resource["titles"],
                "count": resource["count"],
                "category": get_most_common_category(resource),
                "latest_date": latest_date,
            }
        )

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # Write metadata section
            write_metadata_section(f, data)

            f.write("# Resources by Date\n\n")

            # Sort months in reverse chronological order
            for month in sorted(monthly_resources.keys(), reverse=True):
                month_display = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
                f.write(f"## {month_display}\n\n")

                # Collect all resources for domains with <= 5 resources
                ungrouped_resources = []
                domains_to_group = {}

                # Sort domains by total references within the month
                for domain, resources in monthly_resources[month].items():
                    if len(resources) <= 5:
                        ungrouped_resources.extend(resources)
                    else:
                        domains_to_group[domain] = resources

                # Handle domains with more than 5 resources
                if domains_to_group:
                    # Sort domains by total references
                    domain_refs = {
                        domain: sum(r["count"] for r in resources)
                        for domain, resources in domains_to_group.items()
                    }
                    sorted_domains = sorted(
                        domains_to_group.items(),
                        key=lambda x: domain_refs[x[0]],
                        reverse=True,
                    )

                    for domain, resources in sorted_domains:
                        f.write(f"### {domain}\n\n")

                        # Sort resources by date
                        sorted_resources = sorted(
                            resources, key=lambda x: x["latest_date"], reverse=True
                        )

                        for resource in sorted_resources:
                            titles_str = " | ".join(
                                f'"{title}"' for title in resource["titles"]
                            )
                            ref_count = format_reference_count(resource["count"])
                            f.write(
                                f"- [{titles_str}]({resource['url']}){ref_count} "
                                f"(Category: {resource['category']})\n"
                            )
                        f.write("\n")

                # Handle ungrouped resources
                if ungrouped_resources:
                    if domains_to_group:
                        f.write("### Other Resources\n\n")

                    # Sort ungrouped resources by date
                    sorted_resources = sorted(
                        ungrouped_resources,
                        key=lambda x: x["latest_date"],
                        reverse=True,
                    )

                    for resource in sorted_resources:
                        titles_str = " | ".join(
                            f'"{title}"' for title in resource["titles"]
                        )
                        ref_count = format_reference_count(resource["count"])
                        domain = get_domain(resource["url"])
                        f.write(
                            f"- [{titles_str}]({resource['url']}){ref_count} "
                            f"(Category: {resource['category']}, Domain: {domain})\n"
                        )
                    f.write("\n")

        logger.success(f"Successfully generated date view at {output_file}")
    except Exception as e:
        logger.error(f"Error generating date view: {e}")
        raise


def generate_category_view(data: Dict, output_file: str):
    """Generate the organized markdown view."""
    logger.info(f"Generating category view to {output_file}")

    # Group resources by category and domain
    categorized = defaultdict(lambda: defaultdict(list))

    for url, resource in data["resources"].items():
        if resource["occurrences"]:
            category = get_most_common_category(resource)
            domain = get_domain(url)
            latest_date = get_latest_date(resource)

            categorized[category][domain].append(
                {
                    "url": url,
                    "titles": resource["titles"],
                    "count": resource["count"],
                    "latest_date": latest_date,
                }
            )

    # Sort resources within each domain by latest date
    categorized = {
        category: {
            domain: sorted(resources, key=lambda x: x["latest_date"], reverse=True)
            for domain, resources in domains.items()
        }
        for category, domains in categorized.items()
    }

    # Sort categories by total references
    sorted_categories = sorted(
        categorized.items(),
        key=lambda x: sum(
            sum(r["count"] for r in resources) for domain, resources in x[1].items()
        ),
        reverse=True,
    )

    logger.debug(f"Processing {len(sorted_categories)} categories")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # Write metadata section
            write_metadata_section(f, data)

            f.write("# Resources by Category\n\n")

            for category, domains in sorted_categories:
                logger.debug(f"Writing category section: {category}")
                f.write(f"## {category}\n\n")

                # Sort domains by total references
                sorted_domains = sorted(
                    domains.items(),
                    key=lambda x: sum(r["count"] for r in x[1]),
                    reverse=True,
                )

                # First, handle domains with multiple resources
                for domain, resources in sorted_domains:
                    if len(resources) > 1:
                        f.write(f"### {domain}\n\n")
                        for resource in resources:  # Already sorted by date
                            titles_str = " | ".join(
                                f'"{title}"' for title in resource["titles"]
                            )
                            ref_count = format_reference_count(resource["count"])
                            f.write(f"- [{titles_str}]({resource['url']}){ref_count}\n")
                        f.write("\n")

                # Then, handle domains with single resources
                single_resources = []
                for domain, resources in sorted_domains:
                    if len(resources) == 1:
                        single_resources.extend(resources)

                if single_resources:
                    # Sort single resources by date
                    single_resources.sort(key=lambda x: x["latest_date"], reverse=True)

                    if any(len(resources) > 1 for domain, resources in sorted_domains):
                        f.write("### Other Resources\n\n")

                    for resource in single_resources:
                        titles_str = " | ".join(
                            f'"{title}"' for title in resource["titles"]
                        )
                        ref_count = format_reference_count(resource["count"])
                        f.write(f"- [{titles_str}]({resource['url']}){ref_count}\n")
                    f.write("\n")

        logger.success(f"Successfully generated category view at {output_file}")
    except Exception as e:
        logger.error(f"Error generating category view: {e}")
        raise


def save_detailed_view(data: Dict, output_file: str):
    """Save the detailed JSON view."""
    logger.info(f"Saving detailed view to {output_file}")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.success(f"Successfully saved detailed view to {output_file}")
    except Exception as e:
        logger.error(f"Error saving detailed view: {e}")
        raise
