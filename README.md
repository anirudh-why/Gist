# 💡 GitHub Repo Explainer — AI-Powered Code Learning Assistant

> **Understand any open-source repository through natural language questions — like having a teacher explain the code.**

This is a complete RAG (Retrieval-Augmented Generation) pipeline that helps students and developers learn from open-source codebases by asking questions in plain English.

---

## 🌟 What Makes This Special?

### **Student-Friendly UX**
- 🎓 **Learn by exploring** — paste any GitHub repo URL and start asking questions
- 💬 **Conversational answers** — explanations in simple, educational language
- 📚 **Source transparency** — every answer cites actual code snippets
- 🎯 **Preset questions** — quick-start buttons for common queries
- ✨ **Minimal friction** — sensible defaults, no complex setup

### **Powerful Backend**
- 🧠 **Local embeddings** — `sentence-transformers/all-MiniLM-L6-v2` (no API costs)
- 💾 **Vector search** — ChromaDB for efficient semantic retrieval
- ⚡ **Fast generation** — Groq LLM with OpenAI-compatible API
- 🔄 **Complete pipeline** — ingestion → chunking → embedding → retrieval → generation

---

## 🚀 Quick Start

### **1. Install Dependencies**

```bash
python -m pip install -r requirements.txt
```

### **2. Set Up Groq API Key**

Get a free API key from [Groq Console](https://console.groq.com/) and add to your environment:

```bash
# Linux/Mac
export GROQ_API_KEY="gsk_..."

# Windows (PowerShell)
$env:GROQ_API_KEY="gsk_..."

# Or create a .env file in the project root
echo "GROQ_API_KEY=gsk_..." > .env
```

### **3. Launch the UI**

**Easy way (using our runner scripts):**

```bash
# Linux/Mac
bash scripts/run_ui.sh

# Windows
scripts\run_ui.bat
```

**Or directly:**

```bash
python -m streamlit run app.py
```

The app will open at `http://localhost:8501` 🎉

---

## 🎯 How to Use

### **Step 1: Ingest a Repository**

1. Open the app in your browser
2. Paste any public GitHub URL (e.g., `https://github.com/flask/flask`)
3. Click **"🚀 Ingest Repository"**
4. Wait for processing (fetching → chunking → embedding)
5. See success celebration! 🎉

### **Step 2: Ask Questions**

Choose a preset question or write your own:

**Preset examples:**
- 📝 "What does main.py do?"
- 📁 "Explain the folder structure"
- 🏗️ "Explain the architecture"
- 🔧 "How does it handle errors?"

**Custom examples:**
- "How does authentication work?"
- "Where are database queries defined?"
- "Explain the API endpoints"

### **Step 3: Learn from Answers**

- 🧠 Read the educational explanation
- 📚 Expand sources to see actual code snippets
- 💭 Ask follow-up questions to dive deeper

---

## 📁 Project Structure

```
Gist/
├── app.py                      # 🎨 Main Streamlit UI (student-friendly)
├── repo_explainer.py           # 📝 Minimal CLI with Q&A loop
├── src/
│   ├── ingest/                 # Step 1: Fetch GitHub repos
│   │   ├── github_client.py    # GitHub API integration
│   │   └── utils.py            # Helper functions
│   ├── chunking/               # Step 2: Split code into chunks
│   │   └── chunker.py          # Text chunking with overlap
│   ├── embeddings/             # Step 3: Create vector embeddings
│   │   └── embedder.py         # Sentence transformers
│   ├── retrieval/              # Step 4: Semantic search
│   │   └── retriever.py        # ChromaDB queries
│   └── generation/             # Step 5: LLM answers
│       ├── llm.py              # Groq client with retries
│       └── prompt.py           # Context formatting
├── scripts/
│   ├── run_ingest.py           # CLI: Fetch repos
│   ├── run_chunker.py          # CLI: Chunk files
│   ├── run_embeddings.py       # CLI: Create embeddings
│   ├── query_retrieval.py      # CLI: Search vectors
│   ├── run_generation.py       # CLI: Generate answers
│   ├── run_pipeline.py         # Orchestration utilities
│   ├── run_ui.sh               # 🚀 Launch UI (Linux/Mac)
│   └── run_ui.bat              # 🚀 Launch UI (Windows)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── UX_DESIGN.md               # 🎨 Detailed UX documentation
```

---

## 🛠️ Advanced Usage

### **CLI Tools (for developers)**

Each step has a standalone CLI:

**Step 1: Ingest GitHub Repo**
```bash
python scripts/run_ingest.py https://github.com/owner/repo \
  --out data/raw --token YOUR_GITHUB_TOKEN
```

**Step 2: Chunk Files**
```bash
python scripts/run_chunker.py data/raw owner/repo \
  --out chunks.jsonl --size 1000 --overlap 200
```

**Step 3: Create Embeddings**
```bash
python scripts/run_embeddings.py chunks.jsonl \
  --chroma-dir ./chroma_db --collection my_repo
```

**Step 4: Query Vector DB**
```bash
PYTHONPATH=./src python scripts/query_retrieval.py \
  --chroma-dir ./chroma_db --collection my_repo \
  --query "How does authentication work?" --k 5
```

**Step 5: Generate Answer**
```bash
export GROQ_API_KEY="gsk_..."
PYTHONPATH=./src python scripts/run_generation.py \
  --chroma-dir ./chroma_db --collection my_repo \
  --query "How does authentication work?" \
  --groq-model llama-3.1-8b-instant --k 5 --max-tokens 400
```

### **Interactive CLI**

Prefer a guided experience? Use the interactive runner:

```bash
python scripts/run_interactive.py
```

It will prompt you for:
- New repo URL or existing collection?
- Query question
- Model settings

### **Minimal Example Script**

For quick testing with exactly 2 questions:

```bash
python repo_explainer.py
```

---

## ⚙️ Configuration

### **Environment Variables**

Create a `.env` file in the project root:

```env
# Required for generation
GROQ_API_KEY=gsk_your_groq_api_key_here

# Optional: for private repos
GITHUB_TOKEN=ghp_your_github_token_here

# Optional: customize model
GROQ_MODEL=llama-3.1-8b-instant
GROQ_API_BASE=https://api.groq.com/openai
```

### **Advanced Settings (in UI sidebar)**

- **Context chunks (top-K):** How many code snippets to retrieve (3-10)
- **Max answer length:** Token limit for generated responses (200-1200)
- **Creativity (temperature):** Lower = focused, Higher = creative (0.0-1.0)
- **Database directory:** Where ChromaDB stores vectors

---

## 🎨 UX Design Highlights

### **Welcome Screen**
- Clean, welcoming hero section with gradient background
- Single prominent input for GitHub URL
- Advanced settings collapsed by default
- Clear call-to-action button

### **Ingestion Progress**
- Real-time step-by-step feedback
- Emoji indicators for visual scanning
- Celebration animation on success
- Helpful error messages with suggestions

### **Q&A Interface**
- **Left panel:** Repository summary with file tree
- **Right panel:** Question area with presets
- **Answer display:** Educational framing with sources
- **Conversation history:** Last 3 Q&As visible

### **Answer Quality**
- Conversational, student-friendly explanations
- Markdown formatting for readability
- Code snippets with syntax highlighting
- Source citations for transparency

📖 **See [UX_DESIGN.md](./UX_DESIGN.md) for complete design documentation**

---

## 🧪 Example Queries You Can Try

Once you've ingested a repository, try these questions:

### **Understanding Code Structure**
- "What does main.py do?"
- "Explain the folder structure"
- "What are the main modules in this project?"
- "Show me the entry point of the application"

### **Deep Dives**
- "How does authentication work?"
- "Explain the database schema"
- "How are API routes organized?"
- "What testing framework is used?"

### **Debugging & Troubleshooting**
- "How are errors handled?"
- "Where are logs written?"
- "What validation is performed on user input?"
- "How are configuration files loaded?"

### **Architecture & Design**
- "Explain the overall architecture"
- "What design patterns are used?"
- "How is the codebase organized?"
- "What are the dependencies between modules?"

---

## 🔒 Security Best Practices

### **API Keys**
- ✅ **DO:** Store keys in `.env` or environment variables
- ✅ **DO:** Add `.env` to `.gitignore`
- ✅ **DO:** Use secret management in production
- ❌ **DON'T:** Hard-code keys in source files
- ❌ **DON'T:** Commit keys to version control
- ❌ **DON'T:** Share keys in chat/email

### **GitHub Tokens**
- Only required for private repositories
- Use fine-grained tokens with minimal permissions
- Rotate tokens if exposed

---

## 🐛 Troubleshooting

### **"streamlit: command not found"**

Use the provided runner scripts or activate your virtual environment:

```bash
# Activate venv first
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Then run
streamlit run app.py
```

### **"GROQ_API_KEY not found"**

Make sure you've set the environment variable:

```bash
# Check if it's set
echo $GROQ_API_KEY  # Linux/Mac
echo %GROQ_API_KEY%  # Windows

# Set it if missing
export GROQ_API_KEY="gsk_..."  # Linux/Mac
$env:GROQ_API_KEY="gsk_..."    # Windows PowerShell
```

### **"No relevant code found"**

This can happen if:
- The query is too vague (be more specific)
- The repo hasn't been ingested properly
- The embedding model didn't find semantic matches

**Try:**
- Rephrasing your question with specific file/function names
- Asking about well-known files like `README.md` or `main.py`
- Checking that ingestion completed successfully

### **Slow embedding generation**

First run downloads the embedding model (~90MB). Subsequent runs are fast.

To speed up:
- Reduce chunk size during ingestion
- Exclude large folders (node_modules, dist, etc.)
- Use smaller repos for testing

---

## 🚧 Known Limitations

1. **Code-only focus:** Works best with text/code files (Python, JS, Java, etc.)
2. **Context window:** Very large files may be truncated
3. **Binary files:** PDFs, images, videos are not processed
4. **Rate limits:** GitHub API has rate limits (60 req/hr without token)
5. **Groq limits:** Free tier has API rate limits

---

## 🎓 Educational Use Cases

### **For Students**
- 📚 Learn how popular frameworks are structured (Flask, React, Django)
- 🔍 Understand unfamiliar codebases before contributing
- 📝 Study open-source projects for class assignments
- 💡 Explore different coding patterns and architectures

### **For Educators**
- 🏫 Demonstrate real-world code examples in class
- 📊 Compare multiple implementations of the same concept
- 🎯 Create guided tours through complex projects
- ✅ Help students understand assignment starter code

### **For Developers**
- 🚀 Onboard to new projects faster
- 🔧 Debug unfamiliar codebases
- 📖 Document legacy code automatically
- 🔄 Compare similar libraries/frameworks

---

## 🤝 Contributing

We welcome contributions! Here are some ideas:

- 🐛 **Bug fixes:** Improve error handling, fix edge cases
- ✨ **Features:** Multi-repo comparison, export conversations, visual diagrams
- 📝 **Documentation:** Better examples, tutorials, video guides
- 🎨 **UX:** Improve UI/UX, add themes, mobile responsiveness
- 🧪 **Testing:** Add unit tests, integration tests

### **Development Setup**

```bash
# Clone the repo
git clone https://github.com/anirudh-why/Gist.git
cd Gist

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env  # Create from template
# Edit .env and add your GROQ_API_KEY

# Run tests (if available)
pytest

# Start development server
streamlit run app.py
```

---

## 📜 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) — Beautiful web apps for ML/AI
- [ChromaDB](https://www.trychroma.com/) — Vector database for embeddings
- [Sentence Transformers](https://www.sbert.net/) — State-of-the-art embeddings
- [Groq](https://groq.com/) — Ultra-fast LLM inference
- [GitHub API](https://docs.github.com/en/rest) — Repository access

Special thanks to the open-source community for inspiration and tools.

---

## 📧 Contact & Support

- 🐛 **Issues:** [GitHub Issues](https://github.com/anirudh-why/Gist/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/anirudh-why/Gist/discussions)
- 📧 **Email:** [Your Email]
- 🌟 **Star this repo** if you find it helpful!

---

<div align="center">

**Made with ❤️ for students learning to code**

[⭐ Star](https://github.com/anirudh-why/Gist) • [🍴 Fork](https://github.com/anirudh-why/Gist/fork) • [🐛 Report Bug](https://github.com/anirudh-why/Gist/issues)

</div>
