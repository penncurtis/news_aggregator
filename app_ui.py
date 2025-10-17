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
if 'refresh_trigger' not in st.session_state:
    st.session_state.refresh_trigger = 0


st.title("📰 Daily News Highlights")
st.caption(f"*Updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')} • Only showing articles from the last 36 hours*")

# Simple profile section
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Your Interests")
    # Simple approach - always use empty value and let user type fresh
    interests = st.text_input("What interests you?", 
                             value="", 
                             placeholder="e.g., sports, technology, business", 
                             help="Enter topics separated by commas")
    
    if st.button("Update My Feed", type="primary"):
        # Update session state FIRST
        st.session_state.interests = interests
        st.session_state.refresh_trigger += 1
        st.session_state.feed_updated = True
        # Clear cached articles to force fresh recommendations
        if 'current_articles' in st.session_state:
            del st.session_state.current_articles
        
        # Save to backend
        try:
            # First, save the profile
            r = requests.post(f"{API}/profile", json={"user_id": st.session_state.user_id, "interests": [s.strip() for s in interests.split(",")]})
            if r.status_code == 200:
                # Then, fetch articles for these interests
                with st.spinner("Fetching articles for your interests..."):
                    interests_list = [s.strip() for s in interests.split(",")]
                    r2 = requests.post(f"{API}/ingest-for-interests", json=interests_list)
                if r2.status_code == 200:
                    result = r2.json()
                    st.success(f"✅ Feed updated! New interests: {interests}")
                else:
                    st.success(f"✅ Feed updated! New interests: {interests}")
            else:
                st.error("Failed to update feed")
        except Exception as e:
            st.error(f"Error updating feed: {e}")

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
        st.session_state.refresh_trigger += 1
        st.success("🔄 Feed refreshed! Scroll down to see updated recommendations.")
        st.rerun()

# Load recommendations only if we have articles cached or it's the first load
if 'current_articles' not in st.session_state or st.session_state.refresh_trigger > 0:
    import time
    timestamp = int(time.time() * 1000)  # Current timestamp in milliseconds

    # Load fresh recommendations
    with st.spinner("Loading personalized recommendations..."):
        r = requests.get(f"{API}/recommendations", params={
            "user_id": st.session_state.user_id, 
            "k": 8,
            "refresh": st.session_state.refresh_trigger,
            "timestamp": timestamp
        })

    if r.ok:
        articles = r.json()
        st.session_state.current_articles = articles
    else:
        st.error("❌ Failed to load recommendations")
        articles = []
else:
    # Use cached articles
    articles = st.session_state.get('current_articles', [])

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

# Footer
st.markdown("---")
st.caption("💡 *Tip: Update your interests above to see personalized news tailored just for you*")
