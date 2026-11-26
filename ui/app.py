"""Local Streamlit client using OIDC login and API-audience access tokens."""

import httpx
import streamlit as st

st.set_page_config(page_title="AI PDF Chatbot", page_icon="📄")
st.title("AI PDF Chatbot")

if not st.user.is_logged_in:
    st.write("Sign in with the local identity provider to continue.")
    st.button("Sign in", on_click=st.login, type="primary")
    st.stop()

st.success("Signed in")
st.button("Sign out", on_click=st.logout)

try:
    access_token = st.user.tokens["access"]
except (AttributeError, KeyError, TypeError):
    access_token = None

if not isinstance(access_token, str) or not access_token:
    st.error(
        "No OIDC access token is available. Check Streamlit expose_tokens configuration."
    )
    st.stop()

api_base_url = str(st.secrets.get("api", {}).get("base_url", "http://localhost:8000"))
try:
    with httpx.Client(timeout=httpx.Timeout(10.0), trust_env=False) as client:
        response = client.get(
            f"{api_base_url.rstrip('/')}/api/v1/capabilities",
            headers={"Authorization": f"Bearer {access_token}"},
        )
except httpx.HTTPError:
    st.error("The chatbot API is unavailable. Check that it is running and configured.")
    st.stop()

if response.status_code == 401:
    st.warning("Your sign-in has expired. Sign in again to continue.")
    st.button("Sign in again", on_click=st.logout)
    st.stop()
if response.status_code == 403:
    st.error("Your account does not have the required local API permissions.")
    st.stop()
if response.status_code == 501:
    st.info(
        "Your access token was accepted. Chatbot capabilities are not implemented yet."
    )
elif response.is_success:
    st.write(response.json())
else:
    st.error("The API could not complete the request. Try again later.")
