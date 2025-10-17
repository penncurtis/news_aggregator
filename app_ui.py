import requests, os, streamlit as st

API = os.getenv("NEWS_API_URL", "http://127.0.0.1:8008")

st.title("🗞️ Personalized News Aggregator")

with st.sidebar:
    st.header("Profile")
    user_id = st.text_input("User ID", "alice")
    interests = st.text_input("Interests (comma-separated)", "ai, economics, policy")
    if st.button("Save Profile"):
        r = requests.post(f"{API}/profile", json={"user_id": user_id, "interests": [s.strip() for s in interests.split(",")]})
        st.success(r.json())

if st.button("Ingest Latest"):
    r = requests.post(f"{API}/ingest")
    st.info(f"Ingested {r.json()} new articles")

st.subheader("Recommendations")
r = requests.get(f"{API}/recommendations", params={"user_id": user_id, "k": 10})
if r.ok:
    for art in r.json():
        st.markdown(f"### [{art['title']}]({art['url']})")
        st.caption(f"{art['source']} — {art['published_at']}")
        st.write(art['summary'])
        st.divider()
