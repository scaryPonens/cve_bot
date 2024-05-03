import os
from typing import Tuple, List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.chat_models import ChatOllama
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings, OllamaEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END

from agents_wf import AgentsWorkflow, web_search, retrieve, grade_cve_docs, generate, decide_to_generate, \
    decide_if_answer_is_grounded
from cve_kb import CVEKnowledgeBase
from kb_grader import KnowledgeGrader
from qa_gen import CVEAnswers

load_dotenv()

CVE = 'CVE-2021-3156'

if __name__ == '__main__':
    from langchain_community.tools.tavily_search import TavilySearchResults

    web_search_tool = TavilySearchResults(k=3)

    cve_kb = CVEKnowledgeBase(CVE)
    grader = KnowledgeGrader(cve_kb)

    # Run
    qa_gen = CVEAnswers(cve_kb)
    question = f"Can you explain to me how the {CVE} exploit works?"
    random_question = "What is Donald Duck's favorite color?"

    workflow = StateGraph(AgentsWorkflow)
    workflow.add_node('websearch', web_search)
    workflow.add_node('retrieve', retrieve)
    workflow.add_node('grade_cve_docs', grade_cve_docs)
    workflow.add_node("generate", generate)

    workflow.set_entry_point('retrieve')
    workflow.add_edge('retrieve', 'grade_cve_docs')
    workflow.add_conditional_edges('grade_cve_docs', decide_to_generate,
                                   {'websearch': 'websearch', 'generate': 'generate'})
    workflow.add_edge('websearch', 'generate')
    workflow.add_conditional_edges('generate', decide_if_answer_is_grounded, {
        'not supported': 'generate',
        'useful': END,
        'not useful': 'websearch'
    })

    app = workflow.compile()

    from pprint import pprint

    inputs = {"question": question,
              'retriever': cve_kb.retriever,
              'rag_chain': qa_gen.rag_chain,
              'retrieval_grader': grader.grader,
              'hallucination_grader': qa_gen.hallucination_grader,
              'answer_grader': qa_gen.answer_grader,
              'web_search_tool': web_search_tool}
    for output in app.stream(inputs):
        for key, value in output.items():
            pprint(f"Finished running: {key}:")
    pprint(value["generation"])
