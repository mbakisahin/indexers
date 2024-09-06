from datetime import datetime


def prepare_answering_prompt(user_input, contexts, language=None):
    """
    Formats the GPT prompt for the question-answering task.

    Args:
        user_input: the user's input question.
        contexts: a list of related contexts.

    Returns:
        A formatted string representing the GPT prompt for the question-answering task.
    """
    prompt = f"""
    Here is the information Contexts:
    """
    for index, context in enumerate(contexts):
        prompt += f"""
    Context {index}: 
        Text:  `{context["parent_chunk"]}`
        Reference: `{context["title"]}` notified at {context["date"]}`
        Website: `{context["website"]}`
        """
    prompt += f"""

    Here is the question:
    Question: 
    {user_input}
    {f"Answer in {language}" if language else ""}

    Here is the answer:
    Answer:
    """
    return prompt


def prepare_feature_extraction_prompt(user_input):
    """
    Formats the GPT prompt for the feature extraction task.

    Args:
        user_input: the user's input question.

    Returns:
        A formatted string representing the GPT prompt for the feature extraction task.
    """
    prompt = f"""
    Today's date is {datetime.now().strftime("%Y-%m-%d")}.

    Here is the question:
    Question:
    {user_input}

    Here is the extracted features in JSON Format:
    """
    return prompt
