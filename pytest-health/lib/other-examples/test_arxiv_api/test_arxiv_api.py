import atoma
import pytest
from os import environ
import requests


search_query: str = environ["SEARCH_QUERY"]
max_results: int = environ["MAX_RESULTS"]

query: str = f"search_query={search_query}&max_results={max_results}"
url: str = f"http://export.arxiv.org/api/query?{query}"


def arxiv_api_response():
    response = requests.get(url)
    return response


RESPONSE = arxiv_api_response()


def arxiv_feed():
    if RESPONSE.status_code == 200:
        feed = atoma.parse_atom_bytes(RESPONSE.content)
        return feed
    else:
        return []


FEED = arxiv_feed()


def doi_links():
    doi_links = []
    for entry in FEED.entries:
        doi_href = [link.href for link in entry.links if link.title == "doi"]
        doi_links.extend(doi_href)
    return doi_links


DOI_LINKS = doi_links()


def test_arxiv_api_status():
    """Test to check if the arXiv API responded successfully."""
    assert RESPONSE.status_code == 200, "arXiv API did not return a 200 response"


def test_arxiv_feed_has_entries():
    """Test to check if the arXiv feed has at least one entry."""
    assert len(FEED.entries) > 0, "arXiv feed does not contain any entries"


@pytest.mark.parametrize("doi", DOI_LINKS)
def test_doi_link_status(doi):
    """Test to check if the DOI link return a 200 response."""
    response = requests.get(doi)
    assert response.status_code == 200, f"DOI link {doi} did not return a 200 response"
