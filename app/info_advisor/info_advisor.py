"""Conversation Info Advisor.

Helps answer the candidate's questions about the position, formulates the
next message, and maintains engagement -- while steering the conversation
toward the end goal of scheduling an interview. May use the vector database
(Chroma) built from the job description for retrieval-augmented answers.
"""

# TODO: from app.tools.vector_store import retrieve_relevant_chunks


class InfoAdvisor:
    """Answers candidate questions and drafts the next reply."""

    def __init__(self):
        # TODO: construct the LLM client / prompt, and the Chroma
        # retriever used to ground answers in the job description.
        pass

    def answer(self, conversation):
        """Draft a reply to the candidate's latest message.

        TODO:
        - Retrieve relevant job-description chunks from Chroma for the
          candidate's question.
        - Draft a reply that answers the question and nudges toward
          scheduling an interview.
        - Return an AdvisorResult (see app.schemas, once it exists).
        """
        raise NotImplementedError
