"""
Streamlit frontend that calls FastAPI backend
Beautiful, modern UI design with auto-refresh
"""
import streamlit as st
import requests
import os
import time
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh
import extra_streamlit_components as stx

load_dotenv()

# Configuration
def get_secret(key: str, default: str = "") -> str:
    """Safely get secret from environment or Streamlit secrets"""
    value = os.getenv(key)
    if value:
        return value
    try:
        if hasattr(st, "secrets") and st.secrets:
            return st.secrets.get(key, default)
    except Exception:
        pass
    return default

API_BASE = get_secret("API_BASE", "http://localhost:8000")
APP_PASSWORD = get_secret("VITE_APP_PASSWORD", "daiweihao1990")

# Page config
st.set_page_config(
    page_title="Finviz Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Beautiful custom CSS
st.markdown("""
<style>
    /* Main app styling */
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        color: #e2e8f0;
    }
    
    /* Headers */
    h1 {
        color: #f1f5f9;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    h2 {
        color: #f1f5f9;
        font-weight: 700;
        font-size: 1.75rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    
    h3 {
        color: #cbd5e1;
        font-weight: 600;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        background-color: #0b1220;
        color: #e2e8f0;
        border: 2px solid #1f2937;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
        height: 48px !important;
        font-size: 1rem;
        line-height: 1.5;
        box-sizing: border-box;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #60a5fa;
        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
    }
    
    /* Ensure input container has consistent height */
    .stTextInput > div {
        height: 48px !important;
    }
    
    .stTextInput > div > div {
        height: 48px !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        color: #ffffff;
        font-weight: 700;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
        height: 48px !important;
        font-size: 1rem;
        line-height: 1.5;
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
    }
    
    /* Ensure button container has consistent height */
    .stButton {
        height: 48px !important;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
        color: #60a5fa;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #94a3b8;
        font-weight: 600;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    
    .streamlit-expanderContent {
        background-color: #0b1220;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 1rem;
    }
    
    /* Dataframe styling */
    .dataframe {
        background-color: #0b1220;
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Info boxes */
    .stInfo {
        background-color: #1e3a8a;
        border-left: 4px solid #60a5fa;
        border-radius: 8px;
    }
    
    .stSuccess {
        background-color: #065f46;
        border-left: 4px solid #10b981;
        border-radius: 8px;
    }
    
    .stError {
        background-color: #7f1d1d;
        border-left: 4px solid #ef4444;
        border-radius: 8px;
    }
    
    .stWarning {
        background-color: #78350f;
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #334155, transparent);
        margin: 2rem 0;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #111827;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #60a5fa;
    }
    
    /* Number input */
    .stNumberInput > div > div > input {
        background-color: #0b1220;
        color: #e2e8f0;
        border: 2px solid #1f2937;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Password protection using server-side session_state + cookies for "Remember this computer"
# Password is stored in Streamlit Secrets or environment variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'cookie_checked' not in st.session_state:
    st.session_state.cookie_checked = False

# Initialize cookie manager using extra-streamlit-components
# Note: Cannot use @st.cache_resource because CookieManager uses widgets internally
cookies = stx.CookieManager()

# Generate a fixed auth token (hash of password only - same every time)
def generate_auth_token():
    """Generate a fixed auth token based on password"""
    return hashlib.md5(APP_PASSWORD.encode()).hexdigest()[:16]

# Check for saved authentication token in cookies (for "Remember this computer")
# This runs before login check to auto-authenticate if cookie exists
# Only check once per session to avoid repeated widget calls
if not st.session_state.authenticated and not st.session_state.cookie_checked:
    st.session_state.cookie_checked = True
    try:
        cookie_token = cookies.get('finviz_auth_token')
        if cookie_token:
            if cookie_token == generate_auth_token():
                # Token matches, auto-authenticate
                st.session_state.authenticated = True
                st.rerun()
    except Exception as e:
        # Cookie read error - silently continue to login page
        # This can happen on first load or if cookies are disabled
        # In Streamlit Cloud, CookieManager may need a rerun to initialize
        pass

# Initialize summary storage
if 'summaries' not in st.session_state:
    st.session_state.summaries = {}

# Initialize auto-refresh settings
if 'auto_refresh_enabled' not in st.session_state:
    st.session_state.auto_refresh_enabled = False
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = None

# Initialize quote data storage
if 'current_ticker' not in st.session_state:
    st.session_state.current_ticker = None  # No default, wait for user input
if 'current_quote' not in st.session_state:
    st.session_state.current_quote = {}
if 'current_news' not in st.session_state:
    st.session_state.current_news = []
if 'current_chart_url' not in st.session_state:
    st.session_state.current_chart_url = ""
if 'ticker_input' not in st.session_state:
    st.session_state.ticker_input = ""  # Empty default

if not st.session_state.authenticated:
    # Beautiful login page
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #111827, #1e293b); 
                    border-radius: 20px; border: 1px solid #334155; box-shadow: 0 20px 60px rgba(0,0,0,0.5);'>
            <h1 style='margin-bottom: 0.5rem;'>🔒</h1>
            <h2 style='color: #f1f5f9; margin-bottom: 0.5rem;'>访问受限</h2>
            <p style='color: #94a3b8;'>请输入密码以访问 Finviz 交易仪表板</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        password = st.text_input("密码", type="password", key="password_input", label_visibility="collapsed")
        
        # "Remember this computer" checkbox
        remember_me = st.checkbox("💾 记住此电脑（30天内免登录）", value=False, key="remember_me")
        
        if st.button("登录", type="primary", use_container_width=True):
            # Server-side password verification
            if password == APP_PASSWORD:
                st.session_state.authenticated = True
                
                # If "Remember me" is checked, save fixed token to cookie (30 days expiry)
                if remember_me:
                    try:
                        auth_token = generate_auth_token()
                        # Set cookie with 30 days expiry (max_age in seconds)
                        expiry_seconds = 30 * 24 * 60 * 60  # 30 days
                        # Use secure=True for HTTPS (Streamlit Cloud), same_site='lax' for cross-site compatibility
                        cookies.set(
                            'finviz_auth_token', 
                            auth_token, 
                            max_age=expiry_seconds,
                            secure=True,  # Required for HTTPS (Streamlit Cloud)
                            same_site='lax'  # Allows cookie to work across same-site navigations
                        )
                    except Exception as e:
                        # Cookie set error - log but don't block login
                        st.warning(f"⚠️ 无法保存登录状态: {str(e)}")
                
                st.rerun()
            else:
                st.error("❌ 密码错误，请重试")
    
    st.stop()

# Main app content - title removed

# Function to fetch and update data
def fetch_quote_data(ticker_symbol: str, silent: bool = False):
    """Fetch quote data from API and update session state"""
    try:
        # Check if API_BASE is configured correctly
        if API_BASE == "http://localhost:8000":
            # Check if we're running on Streamlit Cloud (not localhost)
            import socket
            try:
                # Try to resolve localhost - if it fails, we're probably on Streamlit Cloud
                socket.gethostbyname('localhost')
            except:
                if not silent:
                    st.error("""
                    ⚠️ **配置错误**: 无法连接到后端 API
                    
                    **在 Streamlit Cloud 上部署时，需要配置后端 URL：**
                    
                    1. 在 Streamlit Cloud 的 Settings → Secrets 中添加：
                    ```toml
                    [secrets]
                    API_BASE = "https://your-backend-url.com"
                    ```
                    
                    2. 确保 FastAPI 后端已部署并运行
                    
                    3. 检查后端 URL 是否正确（不要使用 localhost）
                    """)
                return False
        
        if not silent:
            with st.spinner("⏳ Fetching data from FastAPI backend..."):
                response = requests.get(f"{API_BASE}/quote/{ticker_symbol.upper()}", timeout=30)
                response.raise_for_status()
                data = response.json()
        else:
            # Silent refresh in background
            response = requests.get(f"{API_BASE}/quote/{ticker_symbol.upper()}", timeout=30)
            response.raise_for_status()
            data = response.json()
        
        # Store in session state so it persists
        st.session_state.current_ticker = ticker_symbol.upper()
        st.session_state.current_quote = data.get("quote", {})
        st.session_state.current_news = data.get("news", [])
        st.session_state.current_chart_url = data.get("chart_url", "")
        st.session_state.last_refresh_time = datetime.now()
        
        return True
    except requests.exceptions.ConnectionError as e:
        if not silent:
            error_msg = str(e)
            if "localhost" in API_BASE or "127.0.0.1" in API_BASE:
                st.error(f"""
                ❌ **连接失败**: 无法连接到后端 API
                
                **当前配置**: `{API_BASE}`
                
                **问题**: 在 Streamlit Cloud 上无法使用 `localhost` 或 `127.0.0.1`
                
                **解决方案**:
                1. 在 Streamlit Cloud Settings → Secrets 中配置：
                ```toml
                [secrets]
                API_BASE = "https://your-backend-url.com"
                ```
                
                2. 确保后端已部署（例如 Render, Railway, Heroku）
                
                3. 测试后端是否可访问：`curl https://your-backend-url.com/health`
                """)
            else:
                st.error(f"""
                ❌ **连接失败**: 无法连接到后端 API
                
                **当前配置**: `{API_BASE}`
                
                **可能的原因**:
                1. 后端服务未运行或已停止
                2. URL 配置错误
                3. 网络连接问题
                
                **请检查**:
                - 后端服务状态
                - API URL 是否正确
                - 后端是否允许来自 Streamlit Cloud 的请求（CORS）
                """)
        return False
    except Exception as e:
        if not silent:
            st.error(f"❌ Error fetching data: {str(e)}")
        return False

# Ticker input section with beautiful card
st.markdown("<br>", unsafe_allow_html=True)
with st.container():
    st.markdown("""
    <div style='background: linear-gradient(135deg, #111827, #1e293b); padding: 1.5rem; border-radius: 16px; 
                border: 1px solid #334155; margin-bottom: 1.5rem;'>
        <h2 style='margin-top: 0;'>🔍 Stock Lookup</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    with col1:
        ticker = st.text_input(
            "Ticker Symbol", 
            value=st.session_state.ticker_input,  # Use session state for persistence
            placeholder="e.g. AAPL, TSLA, MSFT...",
            key="ticker_input_main",  # Unique key to avoid conflicts
            label_visibility="collapsed"
        )
    with col2:
        get_quote_btn = st.button("🚀 Get Quote", type="primary", use_container_width=True)

# Manual refresh button
if get_quote_btn and ticker:
    # Update session state ticker_input to match what user entered
    st.session_state.ticker_input = ticker.upper()
    if fetch_quote_data(ticker.upper(), silent=False):
        st.rerun()

# Auto-refresh logic using st_autorefresh (doesn't reload page, preserves session state)
# Refresh data every 5 minutes when auto-refresh is enabled
if st.session_state.auto_refresh_enabled and 'current_ticker' in st.session_state and st.session_state.current_ticker:
    # Use st_autorefresh to trigger rerun every 5 minutes
    st_autorefresh(interval=5*60*1000, key="data_autorefresh", limit=None)
    # Fetch fresh data silently (this runs on each rerun triggered by st_autorefresh)
    fetch_quote_data(st.session_state.current_ticker, silent=True)

# Display stored data
if 'current_quote' in st.session_state and st.session_state.current_quote:
    quote = st.session_state.current_quote
    news = st.session_state.current_news
    chart_url = st.session_state.current_chart_url
    ticker = st.session_state.current_ticker
    
    # Create left and right columns
    col_left, col_right = st.columns([1, 1], gap="large")
    
    # LEFT COLUMN: Quote Data
    with col_left:
        st.markdown(f"### 📊 {ticker.upper()} Quote Data")
        
        if isinstance(quote, dict):
            # Create beautiful metric cards in multiple columns
            quote_items = list(quote.items())
            
            # Display in 3 columns for better layout
            cols = st.columns(3)
            for idx, (key, value) in enumerate(quote_items[:18]):
                with cols[idx % 3]:
                    st.metric(
                        label=key,
                        value=str(value),
                        delta=None
                    )
        
        # Chart in a card
        if chart_url:
            st.markdown("### 📈 Daily Chart")
            try:
                st.image(chart_url, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Chart image failed to load: {str(e)}")
    
    # RIGHT COLUMN: News Section
    with col_right:
        if news and len(news) > 0:
            st.markdown(f"### 📰 Latest News ({len(news)} articles)")
            
            for idx, item in enumerate(news[:10]):
                # Format date for display
                date_str = item.get('date', 'Unknown')
                if date_str and date_str != 'Unknown':
                    try:
                        from datetime import datetime
                        if 'T' in date_str:
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            date_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                
                with st.expander(f"📄 {item.get('title', 'No title')} - {date_str}"):
                    col_source, col_date = st.columns(2)
                    with col_source:
                        st.markdown(f"**Source:** {item.get('source', 'Unknown')}")
                    with col_date:
                        st.markdown(f"**Date:** {date_str}")
                    
                    if item.get('link'):
                        # Handle relative URLs
                        article_url = item['link']
                        if article_url.startswith('/'):
                            article_url = f"https://finviz.com{item['link']}"
                        st.markdown(f"[🔗 Read full article]({article_url})")
                        
                        # Summary section
                        summary_key = f"summary_{idx}_{ticker}_{item.get('link', '')}"
                        
                        # Check if summary already exists
                        if summary_key in st.session_state.summaries:
                            summary_data = st.session_state.summaries[summary_key]
                            st.markdown("#### 🇺🇸 English Summary")
                            st.markdown(f"""
                            <div style='background: #0b1220; padding: 1rem; border-radius: 10px; 
                                        border: 1px solid #1f2937; margin-top: 1rem;'>
                                <p style='color: #e2e8f0; line-height: 1.8;'>
                                    {summary_data.get('summary_en', 'No summary available')}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            st.markdown("#### 🇨🇳 中文摘要")
                            st.markdown(f"""
                            <div style='background: #0b1220; padding: 1rem; border-radius: 10px; 
                                        border: 1px solid #1f2937; margin-top: 1rem;'>
                                <p style='color: #e2e8f0; line-height: 1.8;'>
                                    {summary_data.get('summary_zh', 'No summary available')}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # Summary button
                            if st.button(f"✨ Get Summary", key=summary_key, use_container_width=True):
                                try:
                                    with st.spinner("⏳ Generating summary (this may take a moment)..."):
                                        # Handle relative URLs
                                        url = item['link']
                                        if url.startswith('/'):
                                            url = f"https://finviz.com{url}"
                                        summary_response = requests.get(
                                            f"{API_BASE}/news/summary",
                                            params={"url": url},
                                            timeout=60
                                        )
                                        summary_response.raise_for_status()
                                        summary_data = summary_response.json()
                                        
                                        # Store in session state
                                        st.session_state.summaries[summary_key] = summary_data
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Failed to get summary: {str(e)}")

# Sidebar with settings, logout, and auto-refresh
with st.sidebar:
    st.header("⚙️ 设置")
    
    # Logout button
    if st.button("🚪 退出登录", key="logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.cookie_checked = False  # Reset to allow cookie check on next load
        # Clear saved authentication token from cookie
        try:
            cookies.delete('finviz_auth_token', key='delete_auth_cookie')
        except Exception:
            # Cookie delete error - continue anyway
            pass
        st.rerun()
    
    st.markdown("---")
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("🔄 自动刷新 (5分钟)", value=st.session_state.auto_refresh_enabled, key="auto_refresh_checkbox")
    if auto_refresh != st.session_state.auto_refresh_enabled:
        st.session_state.auto_refresh_enabled = auto_refresh
        st.rerun()
    
    # Show last refresh time
    if st.session_state.last_refresh_time:
        time_diff = datetime.now() - st.session_state.last_refresh_time
        if time_diff.total_seconds() < 60:
            time_str = f"{int(time_diff.total_seconds())}秒前"
        elif time_diff.total_seconds() < 3600:
            time_str = f"{int(time_diff.total_seconds() / 60)}分钟前"
        else:
            time_str = f"{int(time_diff.total_seconds() / 3600)}小时前"
        st.caption(f"⏰ 最后更新: {time_str}")
    
    # Show next refresh info if auto-refresh is enabled
    if st.session_state.auto_refresh_enabled:
        st.caption("⏳ 下次刷新: 5 分钟后")
    
