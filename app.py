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

from cve_kb import CVEKnowledgeBase
from kb_grader import KnowledgeGrader
from qa_gen import CVEAnswers

load_dotenv()

CVE = 'CVE-2021-3156'

if __name__ == '__main__':
    cve_kb = CVEKnowledgeBase(CVE)
    grader = KnowledgeGrader(cve_kb)
    print(grader.grade(CVE))

    # Run
    qa_gen = CVEAnswers(cve_kb)
    print("# Answering question")
    question = f"Can you explain to me how the exploit works?"
    print(qa_gen.answer(question))
