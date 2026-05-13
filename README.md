# UENR Testa StudyBuddy

A comprehensive AI-powered study assistant platform for university students across all departments and faculties.

## 🌟 Features

### Core Features
- **AI-Powered Q&A**: Ask questions and get intelligent answers based on your uploaded documents
- **Document Management**: Upload and manage PDFs, Word documents, PowerPoint presentations, and text files
- **Smart Search**: Advanced search capabilities with semantic understanding
- **Study Analytics**: Track your learning progress and study patterns

### Study Tools
- **Quiz Generator**: Create custom quizzes from your study materials
- **Flashcards**: Generate and study with interactive flashcards
- **Study Guides**: Comprehensive study guides tailored to your content
- **Document Summaries**: Get concise summaries of lengthy documents

### Additional Features
- **Bookmarks**: Save important questions and answers for quick access
- **Search History**: Keep track of your searches
- **Recommendations**: Get personalized study recommendations
- **Export Options**: Export your study materials and Q&A history

## 🎯 Target Audience

**UENR Testa StudyBuddy** is designed for **all university students** across:
- All departments
- All faculties
- All academic disciplines

Whether you're studying Engineering, Business, Arts, Sciences, or any other field, Testa StudyBuddy adapts to your needs.

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/CaL7598/Testa-studyBuddy.git
   cd Testa-studyBuddy
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   BYTEZ_API_KEY=your_bytez_api_key_here
   ```
   
   Get your free API key from [Bytez](https://bytez.com)

4. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   
   Open your browser and navigate to: `http://127.0.0.1:8000`

## 📚 Usage

### First Steps
1. **Register/Login**: Create an account or log in
2. **Upload Documents**: Upload your study materials (PDFs, Word docs, etc.)
3. **Ask Questions**: Start asking questions about your uploaded content
4. **Explore Features**: Try quizzes, flashcards, and study guides

### Tips for Best Results
- Upload well-structured documents for better AI understanding
- Be specific with your questions
- Use bookmarks to save important Q&A pairs
- Check your analytics to track progress

## 🛠️ Technology Stack

- **Backend**: Django 5.0.3
- **AI/ML**: 
  - Bytez API (free open-source models)
  - LangChain for AI orchestration
  - Sentence Transformers for embeddings
  - FAISS for vector search
- **Frontend**: 
  - HTML5, CSS3, JavaScript
  - Tailwind CSS for styling
  - Google Fonts (Montserrat, Poppins)
- **Document Processing**: PyPDF2, python-docx, python-pptx

## 📖 Documentation

- [API Setup Guide](API_SETUP.md) - Detailed API configuration instructions
- [Bytez Migration Guide](BYTEZ_MIGRATION.md) - Migration from Gemini to Bytez

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is open source and available for educational purposes.

## 🙏 Acknowledgments

- UENR (University of Energy and Natural Resources)
- Bytez for providing free open-source AI models
- All contributors and users

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Made with ❤️ for students across all disciplines**
