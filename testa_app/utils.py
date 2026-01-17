"""
Utility functions for Testa ChatBuddy application
"""
import os
import json
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
from docx import Document
from pptx import Presentation
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate


def get_file_text(file):
    """Extract text from various file types (PDF, DOCX, PPTX, TXT)"""
    extension = file.name.split('.')[-1].lower()
    
    if extension == 'pdf':
        return extract_text_from_pdf(file)
    elif extension == 'docx':
        return extract_text_from_docx(file)
    elif extension == 'pptx':
        return extract_text_from_pptx(file)
    elif extension == 'txt':
        return extract_text_from_txt(file)
    else:
        raise ValueError('Unsupported file type')


def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    text = ""
    pdf_reader = PdfReader(file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    doc = Document(file)
    return '\n'.join([para.text for para in doc.paragraphs])


def extract_text_from_pptx(file):
    """Extract text from PPTX file"""
    presentation = Presentation(file)
    text = ""
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text


def extract_text_from_txt(file):
    """Extract text from TXT file"""
    return file.read().decode('utf-8')


def get_text_chunks(text, chunk_size=50000, chunk_overlap=1000):
    """Split text into chunks for vector database"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_text(text)
    return chunks


def get_vector_store(text_chunks, index_path="faiss_index"):
    """Create or update FAISS vector store"""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local(index_path)
    return vector_store


def load_vector_store(index_path="faiss_index"):
    """Load existing FAISS vector store"""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    try:
        vector_store = FAISS.load_local(
            index_path, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        return vector_store
    except Exception as e:
        print(f"Error loading vector store: {e}")
        return None


def get_conversational_chain():
    """Get conversational chain for question answering"""
    prompt_template = """
    You are an educational AI assistant for Computer and Electrical Engineering students.
    Answer the following question based on the provided context.
    If the answer is not in the provided context, use your knowledge but indicate uncertainty.
    
    Context:
    {context}
    
    Question:
    {question}
    
    Provide a clear, educational answer with examples where appropriate.
    Include the course and topic if determinable.
    """
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    prompt = PromptTemplate(
        template=prompt_template, 
        input_variables=["context", "question"]
    )
    from langchain.chains.question_answering import load_qa_chain
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain


class QuizGenerator:
    """Generate quizzes from documents using AI"""
    
    def __init__(self, api_key=None):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-pro", 
            temperature=0.7,
            google_api_key=api_key or os.getenv("GOOGLE_API_KEY")
        )
    
    def generate_quiz(self, document_text, topic, num_questions=5, difficulty="medium"):
        """Generate quiz questions from document text"""
        prompt = f"""Generate a quiz with {num_questions} questions on the topic of {topic} from this content:

{document_text}

Difficulty: {difficulty}

Return ONLY a JSON object with this structure:
{{
  "title": "Quiz title",
  "questions": [
    {{
      "question": "Question text",
      "type": "mcq",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "Why A is correct"
    }}
  ]
}}

Ensure questions test understanding, not just memorization.
"""
        try:
            response = self.model.invoke(prompt)
            # Extract JSON from response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # Try to parse JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            return None
        except Exception as e:
            print(f"Error generating quiz: {e}")
            return None


class FlashcardGenerator:
    """Generate flashcards from documents using AI"""
    
    def __init__(self, api_key=None):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-pro", 
            temperature=0.7,
            google_api_key=api_key or os.getenv("GOOGLE_API_KEY")
        )
    
    def generate_flashcards(self, document_text, topic, num_cards=10):
        """Generate flashcards from document text"""
        prompt = f"""Create {num_cards} flashcards from this educational content about {topic}:

{document_text}

Return ONLY a JSON object:
{{
  "flashcards": [
    {{
      "front": "Question or term",
      "back": "Answer or definition"
    }}
  ]
}}

Focus on key concepts, definitions, and important facts.
"""
        try:
            response = self.model.invoke(prompt)
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            return None
        except Exception as e:
            print(f"Error generating flashcards: {e}")
            return None


class SummaryGenerator:
    """Generate summaries from documents"""
    
    def __init__(self, api_key=None):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-pro", 
            temperature=0.3,
            google_api_key=api_key or os.getenv("GOOGLE_API_KEY")
        )
    
    def generate_summary(self, document_text, summary_type="concise"):
        """Generate summary based on type: concise, detailed, or bullet_points"""
        type_instructions = {
            "concise": "Provide 2-3 paragraphs covering main points.",
            "detailed": "Cover all topics and subtopics comprehensively.",
            "bullet_points": "Create organized bullet list of key concepts."
        }
        
        prompt = f"""Summarize this educational content in {summary_type} format:

{document_text}

{type_instructions.get(summary_type, type_instructions['concise'])}
"""
        try:
            response = self.model.invoke(prompt)
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        except Exception as e:
            print(f"Error generating summary: {e}")
            return None
    
    def generate_study_guide(self, document_text, topic):
        """Generate comprehensive study guide"""
        prompt = f"""Create a comprehensive study guide for the topic: {topic}

Content:
{document_text}

The study guide should include:
1. Overview of the topic
2. Key concepts list
3. Important formulas (if applicable)
4. Study tips
5. Common mistakes to avoid
6. Practice questions (3-5)

Format it in clear sections with headings.
"""
        try:
            response = self.model.invoke(prompt)
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        except Exception as e:
            print(f"Error generating study guide: {e}")
            return None
