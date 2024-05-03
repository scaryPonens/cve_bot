import os
from typing import Tuple, List

import requests
from bs4 import BeautifulSoup

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.chat_models import ChatOllama
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings, OllamaEmbeddings
from langchain_core.prompts import PromptTemplate


class CVEKnowledgeBase:
    def __init__(self, cve_code: str):
        self._vectorstore = None
        self._nist_cve_url = os.getenv('NIST_CVE_URL') or 'https://nvd.nist.gov/vuln/detail/'
        self._persist_directory = os.getenv('CHROMA_DB_DIR') or './chromadb'
        self._embeddings_model = os.getenv('EMBEDDINGS_MODEL') or 'nomic-embed-text'
        self._embeddings = OllamaEmbeddings(model=self._embeddings_model)
        self._local_llm = os.getenv('LOCAL_LLM_MODEL') or 'llama3'
        self.llm = ChatOllama(model=self._local_llm, format="json", temperature=0)

    @property
    def grade_docs_prompt(self):
        return PromptTemplate.from_file("prompts/grade-docs.txt")

    @property
    def nist_cve_url(self):
        return self._nist_cve_url

    @property
    def vectorstore(self):
        return (self._vectorstore or
                Chroma(persist_directory=self._persist_directory, embedding_function=self._embeddings))

    @property
    def retriever(self):
        return self.vectorstore.as_retriever()

    def fetch_cve_description_and_refs(self, cve: str) -> Tuple[str, str, List[str]]:
        response = requests.get(f'{self.nist_cve_url}{cve}')
        soup = BeautifulSoup(response.content, 'html.parser')
        cve_refs = [h.get('href') for h in soup.find('div', id='vulnHyperlinksPanel').select('a')
                    if not h.get('href').startswith('mailto')]
        cve_desc = soup.find('p', {"data-testid": "vuln-description"}).get_text()
        return cve_desc, soup.get_text(), cve_refs

    def crawl_cve_references(self, urls: List[str]) -> List[str]:
        for url in urls:
            try:
                response = requests.get(url)
            except requests.exceptions.SSLError:
                continue
            soup = BeautifulSoup(response.content, 'html.parser')
            yield soup.get_text()

    def init_kb(self, cve_code: str):
        cve_desc, cve_text, cve_refs = self.fetch_cve_description_and_refs(cve_code)
        docs_list = list(self.crawl_cve_references(cve_refs))
        docs_list.append(cve_text)
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=3000, chunk_overlap=1000
        )
        doc_splits = text_splitter.create_documents(docs_list)
        self._vectorstore = Chroma.from_documents(
            doc_splits,
            self._embeddings,
            persist_directory=self._persist_directory
        )
