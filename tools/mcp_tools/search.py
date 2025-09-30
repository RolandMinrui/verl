import arxiv
from ddgs import DDGS
import json
import requests
from semanticscholar import SemanticScholar
import wikipediaapi
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Search")

SEARCH_ERR_MSG = "Search operation failed for query '{query}'. Error: {error}. Please try using a different search engine or adjusting your query."

@mcp.tool()
def duckduckgo_search(query: str, max_results: int=3, timeout: int=5) -> str:
    """
    Search DuckDuckGo for general question.
    
    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        timeout: Timeout in seconds for the each search operation.
    """
    try:
        with DDGS(timeout=timeout) as ddgs:
            result_text = ""
            results_count = 0
            
            for i, result in enumerate(ddgs.text(query, max_results=max_results), 1):
                title = result.get('title', 'No title')
                body = result.get('body', 'No description')
                
                result_text += f"Title {i}: {title}\n"
                result_text += f"Description: {body}\n\n"
                results_count += 1
            
            if results_count == 0:
                return f"No results found for: '{query}'"
            else:
                return f"Found {results_count} results for '{query}':\n\n{result_text}"
                
    except Exception as e:
        return SEARCH_ERR_MSG.format(query=query, error=str(e))

@mcp.tool()
def arxiv_search(query: str, max_results: int=3) -> str:
    """
    Search ArXiv for academic preprints.
    
    Args:
        query: Search query for academic papers.
        max_results: Maximum number of results to return.
    """
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        result_text = ""
        results_count = 0
        
        for paper in client.results(search):
            result_text += f"Title: {paper.title}\n"
            result_text += f"Authors: {', '.join([str(author) for author in paper.authors])}\n"
            result_text += f"Published: {paper.published.strftime('%Y-%m-%d')}\n"
            result_text += f"Summary: {paper.summary[:200]}...\n"
            result_text += f"PDF URL: {paper.pdf_url}\n"
            result_text += f"Primary Category: {paper.primary_category}\n\n"
            results_count += 1
        
        if results_count == 0:
            return f"No ArXiv papers found for: '{query}'"
        else:
            return f"Found {results_count} ArXiv papers for '{query}':\n\n{result_text}"
            
    except Exception as e:
        return str(e)

@mcp.tool()
def semantic_scholar_search(query: str, limit: int=3, timeout: int=10) -> str:
    """
    Search Semantic Scholar for academic papers.
    
    Args:
        query: Search query string for academic papers.
        limit: Maximum number of results to return.
    """
    try:
        # fields = ['title', 'authors', 'abstract', 'url', 'year', 'citationCount']
        fields = ['title', 'abstract']
        scholar = SemanticScholar(timeout=timeout) # FIXME: it seems that the timeout here doesn't work
        responses = scholar.search_paper(
            query = query,
            limit = limit,
            fields = fields,
        )
        result_text = ""
        result_count = 0
        for paper in responses.items:
            result_text += f"Title: {paper['title']}\n"
            result_text += f"Abstract: {paper['abstract']}\n\n"
            result_count +- 1

        return f"{result_count} academic paper found for {query}:\n{result_text}"

    except Exception as e:
        return SEARCH_ERR_MSG.format(query=query, error=str(e))

@mcp.tool()
def wikipedia_search(query: str) -> str:
    """
    Fetch Wikipedia information for a given search query.

    Args:
        query: The search query string.
    """
    wiki = wikipediaapi.Wikipedia(
        user_agent="Tool Agent (rolandminrui@gmail.com)",
        language="en"
    )
    try:
        page = wiki.page(query)
        if page.exists():
            result = {
                "query": query,
                "title": page.title,
                "summary": page.summary
            }
            return json.dumps(result, ensure_ascii=False, indent=2)
        return f"No results found for query: {query}"
    except Exception as e:
        return f"An error occurred while processing query: {e}"


if __name__ == "__main__":
    mcp.run(transport='stdio')