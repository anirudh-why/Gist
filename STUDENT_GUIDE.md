# 📖 Student Quick Start Guide

**Welcome!** This guide will help you start learning from any GitHub repository in under 2 minutes.

---

## 🚀 Step 1: Get Your API Key (One-Time Setup)

You need a free API key from Groq to power the AI explanations.

1. **Visit:** https://console.groq.com/
2. **Sign up** with your email (it's free!)
3. **Create an API key** from the dashboard
4. **Copy** the key (starts with `gsk_...`)

---

## ⚙️ Step 2: Set Up Your Environment (One-Time Setup)

### Option A: Using .env file (Recommended)

1. Create a file named `.env` in the project folder
2. Add this line:
   ```
   GROQ_API_KEY=gsk_your_actual_key_here
   ```
3. Save the file

### Option B: Using environment variables

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="gsk_your_actual_key_here"
```

**Linux/Mac (Bash):**
```bash
export GROQ_API_KEY="gsk_your_actual_key_here"
```

---

## 🎬 Step 3: Launch the App

Open a terminal in the project folder and run:

**Easy way (using scripts):**

```bash
# Windows
scripts\run_ui.bat

# Linux/Mac
bash scripts/run_ui.sh
```

**Or directly:**

```bash
python -m streamlit run app.py
```

The app will open in your browser at: `http://localhost:8501`

---

## 🎓 Step 4: Explore a Repository

### A. Choose a Repository

Pick any public GitHub repo to explore. Here are some great ones to start with:

**Beginner-Friendly:**
- https://github.com/pallets/flask — Web framework
- https://github.com/requests/requests — HTTP library
- https://github.com/Nikhilesh002/invoice-app — Invoice management

**Intermediate:**
- https://github.com/django/django — Full web framework
- https://github.com/fastapi/fastapi — Modern API framework
- https://github.com/scikit-learn/scikit-learn — Machine learning

### B. Paste the URL

1. Copy the GitHub URL
2. Paste it in the "📥 GitHub Repository URL" field
3. Click **"🚀 Ingest Repository"**

### C. Wait for Processing

You'll see progress messages like:
- 📥 Fetching repository files...
- ✂️ Chunking code...
- 🧠 Creating embeddings...
- 💾 Storing in database...

This takes 1-3 minutes depending on repo size.

### D. Celebrate! 🎉

When you see balloons, you're ready to ask questions!

---

## 💬 Step 5: Ask Questions

### Quick Start Questions (Just Click!)

Try these preset buttons first:

1. **"📝 What does main.py do?"**
   - Learn about the entry point

2. **"📁 Explain folder structure"**
   - Understand project organization

3. **"🏗️ Explain the architecture"**
   - Get the big picture

4. **"🔧 How does it handle errors?"**
   - Learn error handling patterns

### Custom Questions

Type your own questions like:

- "How does authentication work?"
- "Where are database queries defined?"
- "Explain the API endpoints"
- "What testing framework is used?"
- "How are configuration files loaded?"

**Tip:** Be specific! Instead of "Explain the code", ask "How does the login function validate passwords?"

---

## 📚 Step 6: Read the Answer

### What You'll See:

1. **Your Question** — Displayed at the top
2. **🧠 Answer** — Educational explanation in simple terms
3. **📚 Sources** — Code snippets that support the answer (click to expand)
4. **💭 Follow-up prompt** — Encouragement to ask more

### Understanding the Answer:

- Answers use **bullet points** for clarity
- **Code snippets** are syntax-highlighted
- **Bolded terms** highlight key concepts
- **"In short"** summaries wrap things up

---

## 🔄 Step 7: Keep Exploring

### Ask Follow-Up Questions

After reading an answer, dive deeper:

- "Explain that in more detail"
- "How does [specific function] work?"
- "What are the dependencies of this module?"
- "Are there any security concerns with this approach?"

### View Sources

Click "📚 View Sources" to see the actual code that was used to generate the answer. This helps you:

- Verify the information
- See real examples
- Learn coding patterns
- Build trust in the explanations

### Check Conversation History

Scroll down to see your last 3 questions and answers. This helps you:

- Remember what you learned
- Reference previous explanations
- Build a learning path

---

## 🎯 Tips for Best Results

### ✅ DO:

- **Ask specific questions** about files, functions, or features
- **Use preset buttons** when starting out
- **Read the sources** to see real code examples
- **Ask follow-ups** to dive deeper
- **Start with small repos** (<100 files) to learn the app

### ❌ DON'T:

- Ask extremely vague questions like "Tell me everything"
- Expect it to write code for you (it explains existing code)
- Use it for very large repos on first try (>1000 files)
- Give up after one question — exploration is the key!

---

## 🐛 Troubleshooting

### "GROQ_API_KEY not found"

**Solution:** Make sure you've set the API key in your `.env` file or environment variables. See Step 2.

### "No relevant code found"

**Solutions:**
1. Make the question more specific
2. Ask about well-known files like `README.md` or `main.py`
3. Try rephrasing with different keywords

### "Could not fetch any files"

**Solutions:**
1. Check if the URL is correct
2. Make sure the repository is public
3. For private repos, add a GitHub token in the advanced settings

### App won't start

**Solutions:**
1. Make sure you're in the correct folder
2. Activate your virtual environment if you have one
3. Check that Streamlit is installed: `pip install streamlit`

---

## 🎓 Learning Strategies

### For Complete Beginners:

1. **Start with Flask** — Small, well-organized web framework
2. **Ask basic questions** like "What does app.py do?"
3. **Read sources carefully** — See how pros write code
4. **Follow imports** — Ask "What does [imported module] do?"

### For Intermediate Learners:

1. **Compare architectures** — Index Django and Flask, compare patterns
2. **Deep-dive features** — "How does Django ORM work?"
3. **Study error handling** — Learn best practices
4. **Explore testing** — "How are tests organized?"

### For Advanced Learners:

1. **Security analysis** — "What security measures are in place?"
2. **Performance patterns** — "How is caching implemented?"
3. **Design patterns** — "What design patterns are used here?"
4. **Architecture decisions** — "Why is the code structured this way?"

---

## 📊 Example Learning Session

Here's how a typical 15-minute session might look:

```
0:00 - Paste Flask repo URL, click Ingest
0:02 - Processing complete! 🎉
0:03 - Click "What does main.py do?"
0:04 - Read answer, expand sources
0:06 - Ask: "How are routes defined?"
0:07 - Read explanation about @app.route decorator
0:09 - Ask: "How does error handling work?"
0:10 - Learn about try-except and error handlers
0:12 - Ask: "Explain the folder structure"
0:13 - Get overview of project organization
0:15 - Check conversation history, bookmark key points
```

**Result:** Understood Flask's basic architecture in 15 minutes!

---

## 🌟 Next Steps

Once you're comfortable:

1. **Index your own projects** — Understand your own code better
2. **Index dependencies** — Learn how the libraries you use work
3. **Compare alternatives** — Flask vs Django, React vs Vue
4. **Contribute to open source** — Understand codebases before PRs
5. **Study design patterns** — Learn from well-architected projects

---

## 💡 Pro Tips

### Save Time:

- **Bookmark the app** — Run it daily for different repos
- **Keep .env configured** — No setup needed next time
- **Start browser sessions** — Answer history saved per browser session

### Learn Faster:

- **Ask "Why?"** — Don't just learn what, learn why
- **Follow the code flow** — Start → Middle → End
- **Compare with docs** — Cross-reference with official documentation
- **Take notes** — Copy key insights to your learning journal

### Go Deeper:

- **Ask about edge cases** — "How does it handle invalid input?"
- **Explore dependencies** — "What does [library] provide?"
- **Study tests** — "How are [feature] tests organized?"
- **Learn conventions** — "What coding style is used?"

---

## 🤝 Get Help

If you get stuck:

1. **Check the README** — Full documentation
2. **Read UX_DESIGN.md** — Detailed feature guide
3. **Try different questions** — Rephrase and retry
4. **Start with small repos** — Build confidence first
5. **Ask on GitHub Issues** — Community support

---

## 🎉 You're Ready!

You now have everything you need to start learning from any open-source repository.

**Remember:** The best way to learn is to **explore, question, and experiment**.

Happy coding! 🚀

---

**Made with ❤️ for students learning to code**
