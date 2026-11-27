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
    if st.button("Refresh documents"):
        st.rerun()
    try:
        result = api.get("/documents", params={"limit": 100})
    except APIClientError as error:
        _show_error(error)
        return
    items = result.get("items", []) if isinstance(result, dict) else []
    if not items:
        st.info("No documents are available yet. Upload a PDF to begin.")
        return
    for document in items:
        with st.container(border=True):
            columns = st.columns([4, 2, 2])
            columns[0].write(document.get("original_filename", "Untitled PDF"))
            columns[1].write(
                str(document.get("status", "unknown")).replace("_", " ").title()
            )
            columns[2].caption(f"Pages: {document.get('page_count') or '—'}")
            columns[0].caption(f"ID: {document.get('id', '')}")
            if document.get("error"):
                st.warning(document["error"].get("message", "Processing failed."))


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
