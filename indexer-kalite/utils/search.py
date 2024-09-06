from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchIndex,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient, SearchIndexingBufferedSender
from azure.search.documents.indexes import SearchIndexClient
from config import EMBEDDING_DIMENSION, COGNITIVE_SEARCH_CONFIG
from utils.utils import get_embedding
from config import app_logger


fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True, sortable=True),
    SearchableField(name="parent_id", type=SearchFieldDataType.String, filterable=True, sortable=True),
    SearchableField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True, sortable=True),
    SimpleField(name="date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    SearchableField(name="website", type=SearchFieldDataType.String, searchable=True, filterable=True, sortable=True),
    SearchableField(name="keyword", type=SearchFieldDataType.String, searchable=True, filterable=True, sortable=True),
    SearchableField(name="url", type=SearchFieldDataType.String, searchable=True, filterable=True),
    SearchableField(name="notified_country", type=SearchFieldDataType.String, searchable=True, filterable=True,
                    sortable=True),
    SearchableField(name="chunk", type=SearchFieldDataType.String, filterable=True, searchable=True),
    SearchableField(name="parent_chunk", type=SearchFieldDataType.String, searchable=False),
    SearchField(name="chunk_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, vector_search_dimensions=EMBEDDING_DIMENSION,
                vector_search_profile_name="default_vector_search_profile"),
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
                profiles=[
                    VectorSearchProfile(
                        name="default_vector_search_profile",
                        algorithm_configuration_name="default_hnsw_algorithm_config"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="default_hnsw_algorithm_config",
                    )
                ]
            )
        )
        index_client.create_index(search_index)
        app_logger.info("Search Index is created successfully!")
        index_client.close()


def check_document_existence_by_title_and_date(title, date):
    """
    Check if a document with the given title and date exists in the search index.

    Args:
        title (str): The title of the document to check.
        date (str): The date of the document to check.

    Returns:
        bool: True if the document exists, False otherwise.
    """
    search_client = SearchClient(endpoint=COGNITIVE_SEARCH_CONFIG["endpoint"],
                                 index_name=COGNITIVE_SEARCH_CONFIG["index_name"],
                                 credential=AzureKeyCredential(COGNITIVE_SEARCH_CONFIG["api_key"]))

    # escape single quotes in the title by doubling them  
    title = title.replace("'", "''")  
    search_results = search_client.search(filter="title eq '{}' and date eq {}".format(title, date),
                                          select=["id"], top=1)
    return sum(1 for _ in search_results) > 0


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
    app_logger.info("The Chunks are indexed successfully!")


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
    app_logger.info("Search Index is deleted successfully!")
    index_client.close()


def search_in_index(query, filters=None, search_parameters=None,sorting=None, top_k=-1, top_k_contexts=6):
    """
    Searches related Chunks in the search index using Azure Cognitive Search.

    Args:
        query (str): The search query string.
        filters (dict): A dictionary of filters to apply to the search.
        sorting (List[str]): Which fields, how to sort the results by.
        top_k (int): The number of regulations to retrieve information from (default is -1 means all).
        top_k_contexts (int): The number of top results to retrieve (default is 6).

    Returns:
        contexts (List) : A list of contexts containing search results.
    """
    search_client = SearchClient(endpoint=COGNITIVE_SEARCH_CONFIG["endpoint"],
                                 index_name=COGNITIVE_SEARCH_CONFIG["index_name"],
                                 credential=AzureKeyCredential(COGNITIVE_SEARCH_CONFIG["api_key"]))
    vector = VectorizedQuery(
        vector=get_embedding(query),
        k_nearest_neighbors=top_k_contexts,
        fields="chunk_vector",
        exhaustive=True
    )
    
    filter_string = ""
    if filters:
        dates = []
        if filters.get("begin_date"):
            dates.append("date ge {}".format(filters["begin_date"]))
        if filters.get("end_date"):
            dates.append("date le {}".format(filters["end_date"]))
        filter_string = " and ".join(dates)

    search_string = ''
    if search_parameters:
        for idx, parameter in enumerate(search_parameters):
            if idx >=1: search_string += ' OR '
            search_string +=  '"' + str(parameter) + '"' +'^4'

    if top_k != -1 and top_k > 0:
        # Fetching top_k documents
        titles_data = list(search_client.search(
            select=["title", "date"],
            filter=filter_string if filters else None,
            order_by=sorting,
        ))
        if sorting:
            reverse_sorting = True if "desc" in sorting[0] else False
        else:
            reverse_sorting = False 
        sorted_titles_data = sorted(titles_data, key=lambda x: x["date"], reverse=reverse_sorting)

        distinct_titles = []
        for title_dict in sorted_titles_data:
            if len(distinct_titles) < 3:
                if title_dict["title"] not in distinct_titles:
                    distinct_titles.append(title_dict["title"])
            else:
                break

        filter_string_titles = " or ".join(["title eq '{}'".format(title) for title in distinct_titles])
        if filter_string != "":
            filter_string_with_titles = f" {filter_string} and ({filter_string_titles})"
        else:
            filter_string_with_titles = filter_string_titles
        
        # Searching inside the top_k documents
        contexts = list(search_client.search(
            search_text=search_string if search_parameters else query,
            search_fields=["title", "chunk"],
            vector_queries=[vector],
            filter=filter_string_with_titles,
            select=["parent_id", "parent_chunk", "title", "website", "keyword", "date"],
            top=top_k_contexts
        ))
    else:
        contexts = list(search_client.search(
            search_text = search_string if search_parameters else query,
            search_fields=["title", "chunk"],
            vector_queries=[vector],
            filter=filter_string if filters else None,
            select=["parent_id", "parent_chunk", "title", "website", "keyword", "date"],
            order_by=sorting,
            top=top_k_contexts
        ))

    unique_contexts = remove_duplicate_contexts(contexts)

    search_client.close()
    app_logger.info("The Searching Process is done successfully!")
    return unique_contexts    

def remove_duplicate_contexts(contexts: list) -> list: 
    
    unique_contexts = []  
    seen_parent_ids = set() 
    ranking = 1 
    for context in contexts:  
        parent_id = context['parent_id']  
        if parent_id not in seen_parent_ids:
            context["ranking"]=ranking
            ranking += 1 
            unique_contexts.append(context)  
            seen_parent_ids.add(parent_id) 
    
    return unique_contexts