import requests, os, streamlit as st
from datetime import datetime, timedelta

API = os.getenv("NEWS_API_URL", "http://127.0.0.1:8008")

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = "alice"
if 'interests' not in st.session_state:
    st.session_state.interests = "sports, technology"
if 'last_daily_update' not in st.session_state:
    st.session_state.last_daily_update = None

# Check if we need to update daily content
today = datetime.now().date()
if st.session_state.last_daily_update != today:
    st.session_state.last_daily_update = today
    st.session_state.daily_updated = False

st.title("📰 Daily News Highlights")
st.caption(f"*Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')} • Only showing articles from the last 36 hours*")

# Simple profile section
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Your Interests")
    interests = st.text_input("What interests you?", value=st.session_state.interests, 
                             placeholder="e.g., sports, technology, business", 
                             help="Enter topics separated by commas")
    
    if st.button("Update My Feed", type="primary"):
        st.session_state.interests = interests
        # Save to backend
        r = requests.post(f"{API}/profile", json={"user_id": st.session_state.user_id, "interests": [s.strip() for s in interests.split(",")]})
        if r.status_code == 200:
            st.success("✅ Feed updated!")
        else:
            st.error("Failed to update feed")

with col2:
    if st.button("🔄 Refresh Today's News", help="Get the latest articles from the past 36 hours"):
        with st.spinner("Fetching today's top stories..."):
            r = requests.post(f"{API}/daily-update")
            if r.status_code == 200:
                result = r.json()
                st.success(f"📰 Added {result['ingested']} fresh articles!")
            else:
                st.error("Failed to fetch news")

# Daily highlights section
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("🔥 Today's Top Stories")
with col2:
    if st.button("🔄 Refresh Feed", help="Update your personalized recommendations"):
        st.rerun()

# Get recommendations
r = requests.get(f"{API}/recommendations", params={"user_id": st.session_state.user_id, "k": 8})
if r.ok:
    articles = r.json()
    if articles:
        # Create a simple, clean layout
        for i, art in enumerate(articles):
            # Format the article nicely
            st.markdown(f"#### [{art['title']}]({art['url']})")
            
            # Source and time
            source = art['source']
            pub_time = art['published_at'][:10] if art['published_at'] else "Today"
            st.caption(f"📰 {source} • {pub_time}")
            
            # Summary
            if art['summary']:
                st.write(art['summary'][:200] + "..." if len(art['summary']) > 200 else art['summary'])
            
            # Add some visual separation
            if i < len(articles) - 1:
                st.markdown("---")
    else:
        st.info("📭 No articles found. Click 'Refresh Today's News' to get started!")
else:
    st.error("❌ Failed to load recommendations")

# Footer
st.markdown("---")
st.caption("💡 *Tip: Update your interests above to see personalized news tailored just for you*")
