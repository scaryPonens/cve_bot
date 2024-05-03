from typing import List

from langchain_community.chat_models import ChatOllama
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import PromptTemplate

from cve_kb import CVEKnowledgeBase


class CVEAnswers:
    def __init__(self, cve_kb: CVEKnowledgeBase):
        self.cve_kb = cve_kb

    @property
    def prompt(self):
        return PromptTemplate.from_file("prompts/answer-question.txt")

    @property
    def llm(self):
        return ChatOllama(model='llama3', temperature=3)

    @property
    def llm_json(self):
        return ChatOllama(model='llama3', format="json", temperature=0)

    @property
    def hallucination_prompt(self):
        return PromptTemplate.from_file("prompts/hallucination-grader.txt")

    @property
    def answer_grade_prompt(self):
        return PromptTemplate.from_file("prompts/grade-answer.txt")

    @property
    def rag_chain(self):
        return self.prompt | self.llm | StrOutputParser()

    @property
    def hallucination_grader(self):
        return self.hallucination_prompt | self.llm_json | JsonOutputParser()

    @property
    def answer_grader(self):
        return self.answer_grade_prompt | self.llm_json | JsonOutputParser()

    def answer(self, question: str):
        docs = self.cve_kb.retriever.invoke(question)
        print("# number of docs with question relevance: ", len(docs))
        docs_txt = "\n\n".join(doc.page_content for doc in docs)
        return docs, (self.prompt | self.llm | StrOutputParser()).invoke({"context": docs_txt, "question": question})

    def is_hallucination(self, docs: List[Document], generation: str):
        hallucination_grader = self.hallucination_prompt | self.llm_json | JsonOutputParser()
        docs_txt = "\n\n".join(doc.page_content for doc in docs)
        return hallucination_grader.invoke({"documents": docs_txt, "generation": generation})

    def answer_grade(self, question: str, generation: str):
        answer_grader = self.answer_grade_prompt | self.llm_json | JsonOutputParser()
        return answer_grader.invoke({"question": question, "generation": generation})
