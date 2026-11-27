"""Authenticated Streamlit interface for the AI PDF chatbot."""

import streamlit as st

from ui.api_client import APIClient, APIClientError, AuthenticationExpired

MAX_PDF_BYTES = 20 * 1024 * 1024


def _show_error(error: APIClientError) -> None:
    if error.status_code == 501:
        st.warning("This API operation is not implemented yet. The UI is ready for it.")
    elif error.status_code == 403:
        st.error("Your account does not have permission for this operation.")
    elif error.retryable:
        st.warning(f"{error}. You can retry when the service is available.")
    else:
        st.error(str(error))


def _upload_page(api: APIClient) -> None:
    st.header("Upload a PDF")
    st.caption("PDF files up to 20 MiB are accepted.")
    with st.form("aipdf_upload_form", clear_on_submit=False):
        upload = st.file_uploader("Choose a PDF", type=["pdf"])
        submitted = st.form_submit_button("Upload and process", type="primary")
    if not submitted:
        return
    if upload is None:
        st.error("Choose a PDF file first.")
        return
    content = upload.getvalue()
    if len(content) == 0 or len(content) > MAX_PDF_BYTES:
        st.error("The PDF must be non-empty and no larger than 20 MiB.")
        return
    if not content.startswith(b"%PDF-"):
        st.error("The selected file does not have a valid PDF signature.")
        return
    try:
        with st.spinner("Uploading the PDF securely…"):
            result = api.upload_pdf(upload.name, content)
        if isinstance(result, dict):
            st.success("Upload accepted.")
            st.caption(f"Document ID: {result.get('document_id', 'pending')}")
            if result.get("job_id"):
                st.caption(f"Ingestion job: {result['job_id']}")
    except APIClientError as error:
        _show_error(error)


def _documents_page(api: APIClient) -> None:
    st.header("Your documents")
    st.caption("Review processing state and page/chunk totals for your PDFs.")
    cursor_key = "aipdf_documents_cursor"
    history_key = "aipdf_documents_history"
    st.session_state.setdefault(cursor_key, None)
    st.session_state.setdefault(history_key, [])
    if st.button("Refresh documents"):
        st.session_state[cursor_key] = None
        st.session_state[history_key] = []
        st.rerun()
    params = {"limit": 20}
    if st.session_state[cursor_key]:
        params["cursor"] = st.session_state[cursor_key]
    try:
        result = api.get("/documents", params=params)
    except APIClientError as error:
        _show_error(error)
        return
    if not isinstance(result, dict) or not isinstance(result.get("items"), list):
        st.error("The documents API returned an invalid response.")
        return
    items = result["items"]
    if not items and not st.session_state[history_key]:
        st.info("No documents are available yet. Upload a PDF to begin.")
        return
    for document in items:
        with st.container(border=True):
            heading, status = st.columns([4, 2])
            heading.text(document.get("original_filename") or "Untitled PDF")
            status.caption(
                str(document.get("status", "unknown")).replace("_", " ").title()
            )
            metrics = st.columns(3)
            metrics[0].caption(f"Pages: {document.get('page_count') or '—'}")
            metrics[1].caption(
                f"Textless pages: {document.get('textless_page_count', 0)}"
            )
            metrics[2].caption(f"Chunks: {document.get('chunk_count', 0)}")
            st.caption(f"Document ID: {document.get('id', '')}")
            error = document.get("error")
            if isinstance(error, dict) and error.get("message"):
                st.warning(str(error["message"]))
    previous, next_page = st.columns(2)
    history = st.session_state[history_key]
    if previous.button("Previous page", disabled=not history):
        st.session_state[cursor_key] = history.pop()
        st.rerun()
    next_cursor = result.get("next_cursor")
    if next_page.button("Next page", disabled=not next_cursor):
        history.append(st.session_state[cursor_key])
        st.session_state[cursor_key] = next_cursor
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="AI PDF Chatbot", page_icon="📄")
    st.title("AI PDF Chatbot")

    if not st.user.is_logged_in:
        st.write("Sign in with the local identity provider to continue.")
        st.button("Sign in", on_click=st.login, type="primary")
        st.stop()

    st.sidebar.success("Signed in")
    if st.sidebar.button("Sign out"):
        st.logout()
        st.stop()
    try:
        access_token = st.user.tokens["access"]
    except (AttributeError, KeyError, TypeError):
        access_token = None
    if not isinstance(access_token, str) or not access_token:
        st.error(
            "No OIDC access token is available. Check expose_tokens in Streamlit secrets."
        )
        st.stop()

    try:
        base_url = str(
            st.secrets.get("api", {}).get("base_url", "http://localhost:8000")
        )
        with APIClient(base_url, access_token) as api:
            section = st.sidebar.radio("Workspace", ["Upload PDF", "Documents"])
            if section == "Upload PDF":
                _upload_page(api)
            else:
                _documents_page(api)
    except AuthenticationExpired:
        st.warning("Your sign-in expired. Sign in again to continue.")
        st.logout()
    except (APIClientError, ValueError) as error:
        _show_error(error) if isinstance(error, APIClientError) else st.error(
            str(error)
        )


if __name__ == "__main__":
    main()
