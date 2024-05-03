from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from cve_kb import CVEKnowledgeBase


class KnowledgeGrader:
    def __init__(self, knowledge_base: CVEKnowledgeBase):
        self._knowledge_base = knowledge_base

    @property
    def knowledge_base(self):
        return self._knowledge_base

    @property
    def prompt(self):
        return PromptTemplate.from_file("prompts/grade-docs.txt")

    @property
    def grader(self):
        return self.prompt | self.knowledge_base.llm | JsonOutputParser()

    def grade(self, question: str):
        retriever = self.knowledge_base.retriever
        docs = retriever.invoke(question)
        doc_txt = docs[1].page_content

        print(f"# Number of docs with question relevance: {len(docs)}")

        return self.grader.invoke({"question": question, "document": doc_txt})
