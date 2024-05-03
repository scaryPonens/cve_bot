from typing import List

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.documents import Document
from langchain_core.runnables import RunnableSerializable
from typing_extensions import TypedDict

from cve_kb import CVEKnowledgeBase
from kb_grader import KnowledgeGrader
from qa_gen import CVEAnswers


class AgentsWorkflow(TypedDict):
    """
    Represents the state of our workflow

    Attributes:
        question: question about reported CVE
        generation: LLM generated answer
        web_search: web search results
        documents: list of CVE related documents
    """
    question: str
    generation: str
    web_search: str
    documents: List[str]
    retriever: CVEKnowledgeBase
    rag_chain: CVEAnswers
    retrieval_grader: KnowledgeGrader
    hallucination_grader: CVEAnswers
    answer_grader: CVEAnswers
    web_search_tool: TavilySearchResults


def retrieve(state: dict) -> dict:
    """
    Retrieve pages from web search

    Args:
        state: current state of the workflow

    Returns:
        updated state
    """
    print("---RETRIEVE DOCS ABOUT CVE---")
    state['web_search'] = "web search results"
    question = state['question']
    retriever = state['retriever']

    # retrieval logic here
    documents = retriever.invoke(question)
    return {'documents': documents, 'question': question}


def generate(state: dict) -> dict:
    """
    Generate answer to the question

    Args:
        state: current state of the workflow

    Returns:
        updated state
    """
    print("---GENERATE ANSWER---")
    question = state["question"]
    documents = state["documents"]
    rag_chain = state["rag_chain"]

    # rag generation logic here
    generation = rag_chain.invoke({'context': documents, 'question': question})
    return {'documents': documents, 'question': question, 'generation': generation}


def grade_cve_docs(state: dict) -> dict:
    """
    Grade the generated answer

    Args:
        state: current state of the workflow

    Returns:
        updated state
    """
    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    generation = state["generation"]
    documents = state["documents"]
    retrieval_grader = state["retrieval_grader"]

    # score each doc
    filtered_docs = []
    web_search = "No"
    for doc in documents:
        score = retrieval_grader.invoke({"question": question, "document": doc.page_content})
        grade = score['score'] if 'score' in score else "no"
        if grade.lower() == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(doc)
    return {'documents': filtered_docs, 'question': question, 'generation': generation,
            'web_search': 'Yes' if len(filtered_docs) == 0 else 'No'}


def web_search(state):
    print("---WEB SEARCH---")
    question = state['question']
    documents = state['documents']
    web_search_tool = state['web_search_tool']

    docs = web_search_tool.invoke({"query": question})
    web_results = "\n\n".join([doc.page_content for doc in docs])
    web_results = Document(page_content=web_results)
    if documents is not None:
        documents.append(web_results)
    else:
        documents = [web_results]
    return {'documents': documents, 'question': question}


def decide_to_generate(state):
    print("---ASSESS GRADED DOCUMENTS---")
    question = state['question']
    web_search = state['web_search']
    filtered_docs = state['documents']

    if web_search == 'Yes':
        print("---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, INCLUDE WEB SEARCH---")
        return "websearch"
    else:
        print("---DECISION: SUFFICIENT RELEVANT DOCS, GENERATE ANSWER---")
        return "generate"


def decide_if_answer_is_grounded(state):
    print("---CHECK HALLUCINATIONS---")
    question = state['question']
    documents = state['documents']
    generation = state['generation']

    hallucination_grader = state['hallucination_grader']
    answer_grader = state['answer_grader']
    score = hallucination_grader.invoke({"documents": documents, "generation": generation})
    print(f"Score: {score}")
    grade = score['score'] if 'score' in score else "no"

    if grade == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        score = answer_grader.invoke({"question": question, "generation": generation})
        grade = score['score']
        if grade == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        else:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"

