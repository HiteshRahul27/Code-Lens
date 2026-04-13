import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="CodeLens", layout="wide")

st.title(" CodeLens")
st.caption("Understand code execution flow instantly")


st.subheader(" Ingest Repository")

repo_url = st.text_input("Enter GitHub Repo URL")

if st.button("Ingest"):
    if repo_url:
        with st.spinner("Indexing repo..."):
            res = requests.post(
                f"{API_URL}/ingest",
                json={"repo_url": repo_url}
            )
            st.success(res.json())
    else:
        st.warning("Enter a repo URL")


st.subheader(" Ask a Question")

col1, col2 = st.columns(2)

with col1:
    query = st.text_input("Query (e.g., authentication flow)")

with col2:
    repo = st.text_input("Repo name (e.g., starlette)")

if st.button("Search"):
    if query and repo:
        with st.spinner("Analyzing code..."):
            res = requests.get(
                f"{API_URL}/search",
                params={"query": query, "repo": repo}
            )
            data = res.json()

        st.subheader(" Execution Flow")
        answer = data.get("answer", "")
        steps = answer.split("\n")

        for step in steps:
            if step.strip():
                st.write(f"{step.strip()}")
        st.subheader("📁 Sources")

        for s in data.get("sources", []):
            st.markdown(
                f"- **{s['name']}**  \n"
                f"  `{s['file']}`  \n"
                f"  Lines: {s['lines']}"
            )

    else:
        st.warning("Enter both query and repo name")