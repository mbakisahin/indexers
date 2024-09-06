import pdfplumber
import io
from langchain.text_splitter import RecursiveCharacterTextSplitter
from uuid import uuid4
from openai import AzureOpenAI
import openai
from datetime import datetime
from config import app_logger
from typing import List, Optional, Sequence
import uuid
from langchain.load import dumps, loads
from config import ADA_CONFIG, GPT_CONFIG


def parse_pdf(file):
    """
    Parses a PDF file and extracts the texts in the file together with metadata like title and page count.

    Args:
        file (file): The PDF file to be parsed.

    Returns:
        pdf_dict (Dict): A dictionary containing the extracted metadata and content from the PDF file.
    """
    pdf_dict = {}
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        pdf_dict["title"] = pdf.metadata.get("Title", "Title Not Found")
        pdf_dict["page_count"] = len(pdf.pages)
        page_contents = []
        full_content = ""
        for page in pdf.pages:
            page_contents.append(page.extract_text())
            full_content += page.extract_text()
        pdf_dict["full_content"] = full_content
        pdf_dict["page_contents"] = page_contents
    app_logger.info("PDF parsed successfully!")
    return pdf_dict


def parse_pdf_with_path(pdf_file_path):
    """
    Parses a PDF file located at the given file path and extracts the texts in the file together
    with metadata like title and page count.

    Args:
        pdf_file_path (str): The file path of the PDF file to parse.

    Returns:
        pdf_dict (Dict): A dictionary containing the extracted metadata and content from the PDF file.
    """
    pdf_dict = {}
    with pdfplumber.open(pdf_file_path) as pdf:
        pdf_dict["title"] = pdf.metadata.get("Title", "Title Not Found")
        pdf_dict["page_count"] = len(pdf.pages)
        page_contents = []
        full_content = ""
        for page in pdf.pages:
            page_contents.append(page.extract_text())
            full_content += page.extract_text()
        pdf_dict["full_content"] = full_content
        pdf_dict["page_contents"] = page_contents
    app_logger.info("PDF parsed successfully!")
    return pdf_dict


def split_pdf_to_chunks(pdf_dict):
    """
    Split a PDF into chunks of text and create a list of dictionaries with chunk information.

    Args:
        pdf_dict (Dict): A dictionary containing the PDF content and metadata.

    Returns:
        chunks (List): A list of dictionaries, each containing chunk information.
    """
    ids: Optional[List[str]] = None
    add_to_docstore: bool = True
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=10000)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)

    if parent_splitter is not None:
        pdf_content = parent_splitter.split_text(pdf_dict["full_content"])
    if ids is None:
        doc_ids = [str(uuid.uuid4()) for _ in pdf_content]
        if not add_to_docstore:
            raise ValueError(
                "If ids are not passed in, `add_to_docstore` MUST be True"
            )
    else:
        if len(pdf_content) != len(ids):
            raise ValueError(
                    "Got uneven list of documents and ids. "
                    "If `ids` is provided, should be same length as `documents`."
            )
        doc_ids = ids

    parent_child_chunks = {}
    for doc, _id in zip(pdf_content, doc_ids, strict=True):
        sub_docs = child_splitter.split_text((doc))
        parent_child_chunks[_id] = []

        for sub_doc in sub_docs:
            chunk_info = {"id": str(uuid4()),'parent_id': _id, 'parent_chunk': doc, 'chunk': sub_doc}  # Create dictionary with chunk information
            parent_child_chunks[_id].append(chunk_info)

    app_logger.info(f"PDF splitted to {len(parent_child_chunks.keys())} parent chunks successfully!")
    return parent_child_chunks

def split_text_to_chunks(text):
    """
    Split a text into chunks and create a list of dictionaries with chunk information.

    Args:
        text (str): The text to be split into chunks.

    Returns:
        chunks (List): A list of dictionaries, each containing chunk information.
    """
   
    ids: Optional[List[str]] = None
    add_to_docstore: bool = True
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=10000)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)

    if parent_splitter is not None:
        text = parent_splitter.split_text(text)
    if ids is None:
        doc_ids = [str(uuid.uuid4()) for _ in text]
        if not add_to_docstore:
            raise ValueError(
                "If ids are not passed in, `add_to_docstore` MUST be True"
            )
    else:
        if len(text) != len(ids):
            raise ValueError(
                    "Got uneven list of documents and ids. "
                    "If `ids` is provided, should be same length as `documents`."
            )
        doc_ids = ids

    parent_child_chunks = {}
    for doc, _id in zip(text, doc_ids, strict=True):
        sub_docs = child_splitter.split_text((doc))
        parent_child_chunks[_id] = []

        for sub_doc in sub_docs:
            chunk_info = {"id": str(uuid4()),'parent_id': _id, 'parent_chunk': doc, 'chunk': sub_doc}  # Create dictionary with chunk information
            parent_child_chunks[_id].append(chunk_info)

    app_logger.info(f".TXT splitted to {len(parent_child_chunks.keys())} parent chunks successfully!")
    return parent_child_chunks

def process_pdf_file(pdf_file):
    """
    Process a PDF file by parsing it, splitting it into chunks,
    and generating embedding vector for each chunk.

    Args:
        pdf_file (str): The provided PDF file to process.

    Returns:
        pdf_chunks (List): A list of dictionaries, each containing a chunk of the PDF
                           with an added 'chunk_vector' key storing the embedding.
    """
    pdf_dict = parse_pdf(pdf_file)
    pdf_chunks = split_pdf_to_chunks(pdf_dict)
    for chunk in pdf_chunks:
        chunk["chunk_vector"] = get_embedding(chunk["chunk"])
    return pdf_chunks


def process_pdf_file_with_path(pdf_file_path):
    """
    Process a PDF file located at the specified path, by parsing it, splitting it into chunks,
    and generating embedding vector for each chunk.

    Args:
        pdf_file_path (str): The file path to the PDF file.

    Returns:
        pdf_chunks (List): A list of dictionaries, each containing a PDF chunk and its corresponding embedding vector.
    """
    pdf_dict = parse_pdf_with_path(pdf_file_path)
    pdf_chunks = split_pdf_to_chunks(pdf_dict)
    for chunk in pdf_chunks:
        chunk["chunk_vector"] = get_embedding(chunk["chunk"])
    return pdf_chunks

def format_date_as_odatav4(date_string):
    """
    Formats a date string as a valid OData V4 format.

    Args:
        date_string (str): The date string to format.

    Returns:
        str: The formatted date string.
    """
    date_object = datetime.strptime(date_string, '%Y-%m-%d').date()
    # Convert the datetime object to a string in the OData V4 format (yyyy-MM-ddTHH:mm:ss.fffZ)
    odata_format = date_object.strftime("%Y-%m-%dT%H:%M:%S-00:00%Z")
    return odata_format


def get_embedding(input_string, verbose_token=False):
    """
    Get an embedding vector based on the input string using OpenAI Ada model.

    Args:
        input_string (str): The input text to generate an embedding for.
        verbose_token (bool): Whether to print the token usage. Defaults to False.

    Returns:
        list or None: The embedding vector if successful, else None.
    """
    openai_client = AzureOpenAI(
        api_key=ADA_CONFIG["api_key"],
        api_version=ADA_CONFIG["api_version"],
        azure_endpoint=ADA_CONFIG["api_base"],
        azure_deployment=ADA_CONFIG["deployment_name"],
    )
    try:
        response = openai_client.embeddings.create(
            input=input_string,
            model=ADA_CONFIG["model"],
        )
        results = response.data[0].embedding
        openai_client.close()
        if verbose_token:
            app_logger.info(f"OpenAI - Ada Token Usage: (Tokens={response.usage.total_tokens})")
        return results
    except openai.APIConnectionError as e:
        openai_client.close()
        app_logger.info(f"(OpenAI/Ada): Failed to connect to OpenAI API: {e}")
        return None
    except openai.APIError as e:
        openai_client.close()
        app_logger.info(f"(OpenAI/Ada): OpenAI API returned an API Error: {e}")
        return None
    except openai.RateLimitError as e:
        openai_client.close()
        app_logger.info(f"(OpenAI/Ada): OpenAI API request exceeded rate limit: {e}")
        return None

def rerank_contexts(lists, k=60):  
    """Reciprocal Rank Fusion of multiple lists without explicit ranks.  
      
    Args:  
        lists (list of lists): A list where each element is a list containing items.  
        k (int): A constant value used in the RRF formula (default is 60).  
          
    Returns:  
        dict: Reranked contexts based on their fused scores.  
    """  
    fused_scores = {}  
    all_items = {}
    for rank_list in lists:  
        for item in rank_list:  
            # Calculate the reciprocal rank, note that index is 0-based and rank should start from 1  
            reciprocal_rank = 1 / (k + item["ranking"])  
            parent_id = item["parent_id"]

            fused_scores[parent_id] = fused_scores.get(parent_id, 0) + reciprocal_rank 
            
            if parent_id not in all_items.keys():
                all_items[parent_id] = item

    reranked_results = [all_items[parent_id] for parent_id, score in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)]

    return reranked_results  

def get_completion(prompt, history=None, temperature=0.7, max_tokens=2048, top_p=0.95, frequency_penalty=0, presence_penalty=0,
                   verbose_token=False, system_message="", json_response=False):
    """
    Get text completion using AzureOpenAI API based on the provided prompt.

    Args:
        prompt (str): The input text prompt.
        history (List[dict[str, str]]): List of previous messages of the session conversation.
        temperature (float): Controls randomness of the output. Higher values make it more randomized.
        max_tokens (int): Maximum number of tokens in the generated completion.
        top_p (float): Controls the diversity of the output. Lower values make it more focused.
        frequency_penalty (float): Controls relative frequency of tokens. Higher values make it choose rarer tokens.
        presence_penalty (float): Controls repetition of tokens. Higher values make it more focused.
        verbose_token (bool): If True, prints token usage information.
        system_message (str): The system message to be used in the prompt.

    Returns:
        str or None: Generated completion text if successful, else None.
    """

    openai_client = AzureOpenAI(
        api_key=GPT_CONFIG["api_key"],
        api_version=GPT_CONFIG["api_version"],
        azure_endpoint=GPT_CONFIG["api_base"],
        azure_deployment=GPT_CONFIG["deployment_name"],
    )

    try:
        if history is None:
            history = []
        chat_messages = [
            {"role": "system", "content": system_message}
        ]
        for prev_message in history:
            chat_messages.append(prev_message)
        chat_messages.append({"role": "user", "content": prompt})
        response = openai_client.chat.completions.create(
            model=GPT_CONFIG["model"],
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            seed=42,
            response_format = {"type": "json_object" if json_response else "text"}
        )
        if verbose_token:
            app_logger.info(f"(OpenAI/GPT Token Usage): Prompt: {response.usage.prompt_tokens} + Completion: "
                            f"{response.usage.completion_tokens} = Total: {response.usage.total_tokens}")
        return response.choices[0].message.content
    except openai.APIConnectionError as e:
        openai_client.close()
        app_logger.info(f"(OpenAI/GPT): Failed to connect to OpenAI API: {e}")
        return None
    except openai.APIError as e:
        openai_client.close()
        app_logger.info(f"(OpenAI/GPT): OpenAI API returned an API Error: {e}")
        return None
    except openai.RateLimitError as e:
        openai_client.close()
        app_logger.info(f"(OpenAI/GPT): OpenAI API request exceeded rate limit: {e}")
        return None
