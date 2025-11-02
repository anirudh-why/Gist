#!/usr/bin/env python
from __future__ import annotations

"""
Streamlit UI (Step 6): Student-friendly GitHub Repo Explainer.

A smart study companion that helps you understand any open-source repository
through natural language questions — like having a teacher explain the code.

Features
- Simple, welcoming onboarding flow
- Clear progress feedback during ingestion
- Conversational, educational answers with sources
- Minimal friction, maximum learning

Requirements
- streamlit
- chromadb, sentence-transformers (already in requirements)
- GROQ_API_KEY in env or .env for generation
"""

import os
import sys
from typing import Optional, List

import streamlit as st


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
        load_dotenv()
    except Exception:
        pass


def _ensure_paths() -> None:
    here = os.path.abspath(os.path.dirname(__file__))
    root = here
    sys.path.insert(0, os.path.join(root, 'src'))
    sys.path.insert(0, os.path.join(root, 'scripts'))


_ensure_paths()
_load_env()

from retrieval.retriever import query_collection, build_context
from generation.prompt import allowed_context_chars, format_sources
from generation.llm import generate_with_openai_compatible
from scripts.run_pipeline import ingest_repo, chunk_files, store_embeddings


st.set_page_config(
    page_title="💡 GitHub Repo Explainer",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================================
# Configuration & Session State
# ============================================================================

# Load Groq and embedding config from environment
embed_model = "sentence-transformers/all-MiniLM-L6-v2"
groq_model = os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant"
groq_base = os.getenv("GROQ_API_BASE") or "https://api.groq.com/openai"
groq_key = os.getenv("GROQ_API_KEY")

# Initialize session state
if "stage" not in st.session_state:
    st.session_state.stage = "welcome"  # welcome, ingested, qa

if "chroma_dir" not in st.session_state:
    st.session_state.chroma_dir = "./chroma_db"

if "collection" not in st.session_state:
    st.session_state.collection = None

if "repo_name" not in st.session_state:
    st.session_state.repo_name = None

if "repo_url" not in st.session_state:
    st.session_state.repo_url = None

if "file_count" not in st.session_state:
    st.session_state.file_count = 0

if "chunk_count" not in st.session_state:
    st.session_state.chunk_count = 0

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "out_raw" not in st.session_state:
    st.session_state.out_raw = None


# ============================================================================
# Helper Functions
# ============================================================================

def format_answer_as_tutorial(answer: str) -> str:
    """
    Add conversational, educational framing to make answers feel more like
    a teacher explaining, not just raw output.
    """
    prefix = "🧠 **Here's what I found:**\n\n"
    return prefix + answer


def show_celebration() -> None:
    """Show a success celebration when repo is ingested"""
    st.balloons()
    st.success("✅ Repository processed successfully! You can now ask questions.")


def build_file_tree(root: str, max_depth: int = 3, max_items: int = 150) -> str:
    """Build a visual tree of the repository structure"""
    if not os.path.isdir(root):
        return "No files available"
    
    lines: List[str] = []
    root = os.path.abspath(root)
    prefix_root = os.path.basename(root)
    lines.append(f"📁 {prefix_root}")
    count = 0
    
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        if depth > max_depth:
            continue
        indent = "  " * depth
        
        # Show directories
        for d in sorted(dirnames)[:50]:
            if count >= max_items:
                break
            lines.append(f"{indent}├─ 📁 {d}/")
            count += 1
        
        # Show files
        for f in sorted(filenames)[:50]:
            if count >= max_items:
                break
            # Add file icons based on extension
            icon = "📄"
            if f.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c')):
                icon = "💻"
            elif f.endswith(('.md', '.txt', '.rst')):
                icon = "📝"
            elif f.endswith(('.json', '.yaml', '.yml', '.xml', '.toml')):
                icon = "⚙️"
            lines.append(f"{indent}└─ {icon} {f}")
            count += 1
        
        if count >= max_items:
            lines.append("  ... (more files not shown)")
            break
    
    return "\n".join(lines)


# ============================================================================
# Sidebar (Advanced Settings - Collapsed by Default)
# ============================================================================

with st.sidebar:
    st.markdown("### ⚙️ Advanced Settings")
    st.caption("Most students won't need to change these")
    
    with st.expander("🔧 Generation Settings", expanded=False):
        top_k = st.slider("Context chunks", min_value=3, max_value=10, value=5,
                         help="How many code snippets to retrieve for context")
        max_tokens = st.slider("Max answer length", min_value=200, max_value=1200, 
                              value=500, step=50,
                              help="Longer = more detailed answers")
        temperature = st.slider("Creativity", min_value=0.0, max_value=1.0, 
                               value=0.3, step=0.05,
                               help="Lower = more focused, Higher = more creative")
    
    with st.expander("🗂️ Database Settings", expanded=False):
        chroma_dir_input = st.text_input(
            "Chroma DB directory",
            value="./chroma_db",
            help="Where to store the vector database"
        )
        st.session_state.chroma_dir = chroma_dir_input
    
    st.markdown("---")
    if not groq_key:
        st.warning("⚠️ GROQ_API_KEY not found in environment")
        st.caption("Add it to your .env file to use the Q&A feature")
    else:
        st.success("✅ GROQ_API_KEY configured")
    
    st.markdown("---")
    st.caption(f"Using model: `{groq_model}`")
    st.caption(f"Using embeddings: `{embed_model}`")


# ============================================================================
# Main UI Flow
# ============================================================================

# Welcome Header - Always visible at top
st.markdown(
    """
    <div style="text-align: center; padding: 2rem 1rem 1rem 1rem;">
        <h1 style="margin: 0; font-size: 2.5rem;">💡 GitHub Repo Explainer Bot</h1>
        <p style="color: #666; font-size: 1.2rem; margin-top: 0.5rem;">
            Understand any open-source repo — explained in simple terms
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================================
# STAGE 1: Welcome / Home Screen
# ============================================================================

if st.session_state.stage == "welcome":
    st.markdown("---")
    
    # Hero section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; border-radius: 15px; color: white; text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="margin: 0 0 1rem 0;">🎓 Learn by Exploring</h2>
                <p style="font-size: 1.1rem; margin: 0;">
                    Paste a GitHub link below and I'll help you understand the project.<br>
                    Ask questions in plain English — I'll explain like a teacher.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Main input area - clean and simple
        repo_url = st.text_input(
            "📥 GitHub Repository URL",
            placeholder="https://github.com/username/repository",
            help="Paste any public GitHub repo URL here"
        )
        
        # Use sensible defaults (hidden from users)
        excludes = "node_modules,dist,.cache,build,.git,.venv,venv"
        chunk_size = 1000
        overlap = 200
        max_size = 1_000_000
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Big, prominent CTA button
        ingest_clicked = st.button(
            "🚀 Ingest Repository",
            type="primary",
            use_container_width=True,
            help="Click to fetch, process, and index the repository"
        )
        
        if ingest_clicked:
            if not repo_url.strip():
                st.error("❌ Please enter a valid GitHub URL")
            else:
                # Parse repo info
                slug = repo_url.replace("https://github.com/", "").rstrip("/")
                repo_name = slug.split("/")[-1] if slug else "repo"
                
                # Set up paths
                out_raw = f"data/raw_{slug.replace('/', '_')}"
                chunks_out = f"data/chunks_{slug.replace('/', '_')}.jsonl"
                chroma_dir = st.session_state.chroma_dir
                collection = f"{repo_name}_sbert"
                
                # Parse excludes
                exclude_paths = {p.strip() for p in (excludes or '').split(',') if p.strip()}
                token = os.getenv("GITHUB_TOKEN")
                
                ingest_repo._path_excludes = exclude_paths  # type: ignore[attr-defined]
                
                # Show progress with detailed steps
                with st.status("🔄 Processing repository...", expanded=True) as status:
                    try:
                        # Step 1: Fetch
                        st.write("📥 Fetching repository files from GitHub...")
                        fetched = ingest_repo(repo_url, out_raw, token, int(max_size), None)
                        
                        if fetched == 0:
                            status.update(label="❌ No files fetched", state="error")
                            st.error("Could not fetch any files. The repo might be private or the URL is incorrect.")
                            st.stop()
                        
                        st.write(f"✅ Fetched **{fetched}** files")
                        
                        # Step 2: Chunk
                        st.write("✂️ Chunking code into manageable pieces...")
                        chunks_count = chunk_files(out_raw, slug, chunks_out, int(chunk_size), int(overlap))
                        
                        if chunks_count == 0:
                            status.update(label="❌ No chunks created", state="error")
                            st.error("Could not create chunks from the fetched files.")
                            st.stop()
                        
                        st.write(f"✅ Created **{chunks_count}** searchable chunks")
                        
                        # Step 3: Embed & Store
                        st.write(f"🧠 Creating embeddings with **{embed_model}**...")
                        st.caption("This may take a minute for large repos...")
                        store_embeddings(chunks_out, chroma_dir, collection, embed_model, 64, False)
                        
                        st.write("💾 Storing in vector database...")
                        
                        # Success!
                        status.update(label="✅ Repository indexed successfully!", state="complete")
                        
                        # Update session state
                        st.session_state.stage = "ingested"
                        st.session_state.collection = collection
                        st.session_state.repo_name = repo_name
                        st.session_state.repo_url = repo_url
                        st.session_state.file_count = fetched
                        st.session_state.chunk_count = chunks_count
                        st.session_state.out_raw = out_raw
                        st.session_state.chroma_dir = chroma_dir
                        
                        # Show celebration
                        show_celebration()
                        
                        # Auto-rerun to show Q&A interface
                        st.rerun()
                        
                    except Exception as e:
                        status.update(label="❌ Error during processing", state="error")
                        st.error(f"Something went wrong: {str(e)}")
                        st.exception(e)


# ============================================================================
# STAGE 2 & 3: Post-Ingestion / Q&A Interface
# ============================================================================

elif st.session_state.stage == "ingested":
    
    # Show repo summary banner
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
                    padding: 1.5rem; border-radius: 10px; color: white; margin-bottom: 1rem;">
            <h3 style="margin: 0;">✅ Repository Ready: {st.session_state.repo_name}</h3>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.95;">
                📦 {st.session_state.file_count} files • 
                📄 {st.session_state.chunk_count} chunks • 
                💾 Stored in <code>{st.session_state.collection}</code>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Two-column layout: Repo info (left) + Q&A (right)
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.markdown("### 🗂️ Repository Summary")
        
        # Repo details card
        st.markdown(
            f"""
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid #667eea;">
                <p style="margin: 0;"><strong>Repository:</strong><br>
                   <a href="{st.session_state.repo_url}" target="_blank">{st.session_state.repo_name}</a>
                </p>
                <p style="margin: 0.5rem 0 0 0;"><strong>Files indexed:</strong> {st.session_state.file_count}</p>
                <p style="margin: 0.5rem 0 0 0;"><strong>Code chunks:</strong> {st.session_state.chunk_count}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # File tree preview
        with st.expander("📂 View Folder Structure", expanded=False):
            if st.session_state.out_raw and os.path.isdir(st.session_state.out_raw):
                tree = build_file_tree(st.session_state.out_raw)
                st.code(tree, language="text")
            else:
                st.caption("File tree not available")
        
        # Option to index a different repo
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Index a Different Repo", use_container_width=True):
            st.session_state.stage = "welcome"
            st.session_state.conversation_history = []
            st.rerun()
    
    with right_col:
        st.markdown("### 💬 Ask Questions")
        
        st.markdown(
            """
            <div style="background: #fff3cd; padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid #ffc107; margin-bottom: 1rem;">
                <p style="margin: 0; color: #856404;">
                    💡 <strong>Tip:</strong> Ask specific questions like:
                    "What does main.py do?" or "How does authentication work?"
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Preset question buttons
        st.markdown("**🎯 Quick Start Questions:**")
        
        preset_col1, preset_col2 = st.columns(2)
        
        with preset_col1:
            if st.button("📝 What does main.py do?", use_container_width=True):
                st.session_state.current_question = "What does main.py do?"
                st.session_state.trigger_ask = True
            
            if st.button("🏗️ Explain the architecture", use_container_width=True):
                st.session_state.current_question = "Explain the overall architecture and design of this project."
                st.session_state.trigger_ask = True
        
        with preset_col2:
            if st.button("📁 Explain folder structure", use_container_width=True):
                st.session_state.current_question = "Explain the folder structure and organization."
                st.session_state.trigger_ask = True
            
            if st.button("🔧 How does it handle errors?", use_container_width=True):
                st.session_state.current_question = "How does this project handle errors and exceptions?"
                st.session_state.trigger_ask = True
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Custom question input
        st.markdown("**✍️ Or ask your own:**")
        question = st.text_area(
            "",
            placeholder="e.g., How are database connections managed?",
            height=100,
            key="question_input",
            label_visibility="collapsed"
        )
        
        ask_button = st.button("🔍 Get Answer", type="primary", use_container_width=True)
        
        # Handle question (from button or preset)
        should_ask = ask_button or st.session_state.get("trigger_ask", False)
        
        if should_ask:
            # Clear trigger
            if "trigger_ask" in st.session_state:
                st.session_state.trigger_ask = False
            
            # Get the question (from preset or input)
            if "current_question" in st.session_state and st.session_state.current_question:
                question = st.session_state.current_question
                st.session_state.current_question = None
            
            if not question.strip():
                st.error("❌ Please enter a question")
            elif not groq_key:
                st.error("❌ GROQ_API_KEY is not configured. Add it to your .env file.")
            else:
                # Ensure collection is set
                collection_name = st.session_state.collection
                if not collection_name:
                    st.error("❌ No collection selected. Please ingest a repository first.")
                    st.stop()
                
                try:
                    # Show what we're doing
                    with st.spinner("🔍 Searching the codebase for relevant context..."):
                        results = query_collection(
                            chroma_dir=st.session_state.chroma_dir,
                            collection_name=collection_name,
                            query=question,
                            model=embed_model,
                            k=int(top_k),
                            where=None,
                        )
                    
                    if not results:
                        st.warning("⚠️ No relevant code found for this question. Try rephrasing?")
                    else:
                        ctx_chars = allowed_context_chars(4096, int(max_tokens))
                        context_block = build_context(results, max_chars=ctx_chars)
                        
                        with st.spinner("🤔 Generating explanation..."):
                            answer = generate_with_openai_compatible(
                                context_block,
                                question,
                                api_base=groq_base,
                                model=groq_model,
                                api_key=groq_key,
                                temperature=float(temperature),
                                max_tokens=int(max_tokens),
                                top_p=0.9,
                            )
                        
                        # Add to conversation history
                        st.session_state.conversation_history.append({
                            "question": question,
                            "answer": answer,
                            "sources": results
                        })
                        
                        # Display answer in a nice card
                        st.markdown("---")
                        st.markdown(
                            f"""
                            <div style="background: #e7f3ff; padding: 1rem; border-radius: 8px; 
                                        border-left: 4px solid #2196F3; margin: 1rem 0;">
                                <strong style="color: #1976D2;">❓ Your Question:</strong>
                                <p style="margin: 0.5rem 0 0 0; color: #333;">{question}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        # Answer with educational framing
                        st.markdown("#### 🧠 Answer")
                        formatted_answer = format_answer_as_tutorial(answer)
                        st.markdown(formatted_answer)
                        
                        # Sources in expandable section
                        with st.expander("📚 View Sources (code snippets used)", expanded=False):
                            st.caption(f"Retrieved {len(results)} relevant code chunks")
                            
                            for i, r in enumerate(results[:5], start=1):
                                meta = r.get("metadata", {}) or {}
                                file_path = meta.get("file_path", "unknown")
                                chunk_index = meta.get("chunk_index", 0)
                                
                                st.markdown(f"**Source {i}: `{file_path}` (chunk {chunk_index})**")
                                code_snippet = (r.get("document", "") or "")[:800]
                                st.code(code_snippet, language="python")
                                st.markdown("---")
                        
                        # Encourage follow-up
                        st.markdown(
                            """
                            <div style="background: #f0f0f0; padding: 0.75rem; border-radius: 6px; 
                                        margin-top: 1rem; text-align: center;">
                                <p style="margin: 0; color: #666;">
                                    💭 <strong>Have a follow-up question?</strong> 
                                    Just ask above — I remember the context!
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                
                except Exception as e:
                    st.error(f"❌ Error generating answer: {str(e)}")
                    st.exception(e)
        
        # Show conversation history
        if st.session_state.conversation_history:
            st.markdown("---")
            st.markdown("### 📜 Conversation History")
            
            for i, conv in enumerate(reversed(st.session_state.conversation_history[-3:]), start=1):
                with st.expander(f"Q{len(st.session_state.conversation_history) - i + 1}: {conv['question'][:50]}...", expanded=False):
                    st.markdown(f"**Question:** {conv['question']}")
                    st.markdown(f"**Answer:** {conv['answer'][:500]}...")


# ============================================================================
# Footer
# ============================================================================

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #999; padding: 1rem;">
        <p style="margin: 0;">Built with ❤️ using Streamlit, ChromaDB, and Groq LLM</p>
        <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem;">
            Embeddings: sentence-transformers/all-MiniLM-L6-v2 • Model: {model}
        </p>
    </div>
    """.format(model=groq_model),
    unsafe_allow_html=True
)
