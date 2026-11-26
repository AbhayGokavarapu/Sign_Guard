"""Single source of truth for the four-page investigation workspace."""
PAGES = {
    'Document analysis': 'document_analysis',
    'Document comparison': 'comparison',
    'Attack lab': 'attack_lab',
    'Evidence viewer': 'forensic_visualization',
}
DEFAULT_PAGE = 'Document analysis'


def valid_page(value):
    """Old sessions may still reference a page removed by a deployment."""
    return value if isinstance(value, str) and value in PAGES else DEFAULT_PAGE
