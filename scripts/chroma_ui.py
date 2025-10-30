import streamlit as st
import json
from chromadb.config import Settings
import chromadb
import os

st.set_page_config(page_title="Chroma DB Inspector", layout="wide")
st.title("Chroma DB Inspector")

chroma_dir = st.sidebar.text_input("Chroma persist directory", value="./chroma_db")
if not os.path.isdir(chroma_dir):
    st.sidebar.warning(f"{chroma_dir} not found (will create on write)")

try:
    client = chromadb.Client(Settings(persist_directory=chroma_dir))
except Exception as e:
    st.sidebar.error(f"Failed to open Chroma client: {e}")
    st.stop()

collections = [c.name for c in client.list_collections()]
st.sidebar.subheader("Collections")
coll_selected = st.sidebar.selectbox("Collection", options=["<none>"] + collections)

if coll_selected == "<none>":
    st.write("No collection selected. Collections on disk:", collections)
    st.stop()

try:
    coll = client.get_collection(name=coll_selected)
except Exception as e:
    st.error(f"Failed to load collection {coll_selected}: {e}")
    st.stop()

st.write(f"### Collection: {coll_selected}")

# show count if available
count = None
try:
    count = coll.count()
except Exception:
    try:
        res = coll.get(limit=1)
        count = len(res.get("ids", []))
    except Exception:
        count = "unknown"
st.write("Count:", count)

# show documents
st.subheader("Sample documents")
n = st.slider("Preview N documents", 1, 50, 10)
try:
    res = coll.get(limit=n)
    for i, _id in enumerate(res.get("ids", [])):
        st.markdown(f"**#{i} — {_id}**")
        st.write("metadata:", res["metadatas"][i])
        st.code(res["documents"][i][:1000])
except Exception as e:
    st.write("Failed to fetch docs:", e)

st.subheader("Query (semantic search)")
query = st.text_input("Enter a natural language query")
k = st.slider("Top K", 1, 20, 5)
if st.button("Search") and query.strip():
    try:
        # prefer query_texts which will embed automatically if supported
        try:
            out = coll.query(query_texts=[query], n_results=k)
            docs = out["documents"][0]
            metas = out["metadatas"][0]
            ids = out["ids"][0]
        except Exception:
            # if query_texts not available, we need to embed externally and call query with embeddings
            st.info("query_texts not available for this Chroma backend; please embed query externally.")
            docs, metas, ids = [], [], []
        for i, (d, m, _id) in enumerate(zip(docs, metas, ids)):
            st.markdown(f"**Rank {i+1} — {_id}**")
            st.write("metadata:", m)
            st.code(d[:2000])
    except Exception as e:
        st.error(f"Query failed: {e}")