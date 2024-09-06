from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchIndex,
    VectorSearch,
    HnswVectorSearchAlgorithmConfiguration
)
from azure.search.documents.models import Vector
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient, SearchIndexingBufferedSender
from azure.search.documents.indexes import SearchIndexClient
from config import EMBEDDING_DIMENSION, COGNITIVE_SEARCH_CONFIG
from utils.utils import get_embedding


fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
    SearchableField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True),
    SimpleField(name="total_page_count", type=SearchFieldDataType.Int32, searchable=True, filterable=True),
    SearchableField(name="chunk", type=SearchFieldDataType.String, searchable=True),
    SearchField(name="chunk_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, vector_search_dimensions=EMBEDDING_DIMENSION,
                vector_search_configuration="default-vector-config"),
    SimpleField(name="page_number", type=SearchFieldDataType.Int32, searchable=True, filterable=True),
]


def does_index_exists():
    """
    Checks if a specific index exists in the search index client.

    Args:
        N/A

    Returns:
        bool: True if the index exists, False otherwise.
    """
    index_client = SearchIndexClient(endpoint=COGNITIVE_SEARCH_CONFIG["endpoint"],
                                     credential=AzureKeyCredential(COGNITIVE_SEARCH_CONFIG["api_key"]))
    index_names = list(index_client.list_index_names())
    index_client.close()
    return COGNITIVE_SEARCH_CONFIG["index_name"] in index_names


def create_index():
    """
    Creates a search index if it does not already exist. Utilizes the Cognitive Search configuration to set
    up the index client and search index. Prints a success message upon index creation.

    Args:
        N/A

    Returns:
        N/A
    """
    if not does_index_exists():
        index_client = SearchIndexClient(endpoint=COGNITIVE_SEARCH_CONFIG["endpoint"],
                                         credential=AzureKeyCredential(COGNITIVE_SEARCH_CONFIG["api_key"]))
        search_index = SearchIndex(
            name=COGNITIVE_SEARCH_CONFIG["index_name"],
            fields=fields,
            vector_search=VectorSearch(
                algorithm_configurations=[HnswVectorSearchAlgorithmConfiguration(
                    name="default-vector-config",
                    kind="hnsw")
                ],
            )
        )
        index_client.create_index(search_index)
        print("Search Index is created successfully!")
        index_client.close()


def ingest_chunks(chunks):
    """
    Ingests chunks of data into a search index. Prints a success message upon chunks indexing.

    Args:
        chunks (List) : A list of data chunks to be ingested.

    Returns:
        N/A
    """
    create_index()
    with SearchIndexingBufferedSender(COGNITIVE_SEARCH_CONFIG["endpoint"],
                                      COGNITIVE_SEARCH_CONFIG["index_name"],
                                      AzureKeyCredential(COGNITIVE_SEARCH_CONFIG["api_key"])) as batch_client:
        batch_client.upload_documents(documents=chunks)
    print("The PDF(s) are indexed successfully!")


def delete_index():
    """
    Deletes the search index. Prints a success message upon index deletion.

    Args:
        N/A

    Returns:
        N/A
    """
    index_client = SearchIndexClient(endpoint=COGNITIVE_SEARCH_CONFIG["endpoint"],
                                     credential=AzureKeyCredential(COGNITIVE_SEARCH_CONFIG["api_key"]))
    index_client.delete_index(COGNITIVE_SEARCH_CONFIG["index_name"])
    print("Search Index is deleted successfully!")
    index_client.close()


def search_in_index(query, top_k=3):
    """
    Searches related Chunks in the search index using Azure Cognitive Search.

    Args:
        query (str): The search query string.
        top_k (int): The number of top results to retrieve (default is 3).

    Returns:
        contexts (List) : A list of contexts containing search results.
    """
    search_client = SearchClient(endpoint=COGNITIVE_SEARCH_CONFIG["endpoint"],
                                 index_name=COGNITIVE_SEARCH_CONFIG["index_name"],
                                 credential=AzureKeyCredential(COGNITIVE_SEARCH_CONFIG["api_key"]))
    vector = Vector(value=get_embedding(query),
                    k=top_k,
                    fields="chunk_vector")

    contexts = list(search_client.search(
        search_text="*",
        vectors=[vector],
        select=["chunk"],
        top=top_k
    ))

    search_client.close()
    print("The Searching Process is done successfully!")
    return contexts
