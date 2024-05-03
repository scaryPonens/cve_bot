from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from cve_kb import CVEKnowledgeBase


class CVEAnswers:
    def __init__(self, cve_kb: CVEKnowledgeBase):
        self.cve_kb = cve_kb

    @property
    def prompt(self):
        return PromptTemplate.from_file("prompts/answer-question.txt")

    @property
    def chain(self):
        return self.prompt | ChatOllama(model='llama3', temperature=3) | StrOutputParser()

    def answer(self, question: str):
        docs = self.cve_kb.retriever.invoke(question)
        print("# number of docs with question relevance: ", len(docs))
        docs_txt = "\n\n".join(doc.page_content for doc in docs)
        return self.chain.invoke({"context": docs_txt, "question": question})
