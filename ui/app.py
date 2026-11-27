"""Authenticated Streamlit interface for the AI PDF chatbot."""

import secrets

import streamlit as st

from ui.api_client import APIClient, APIClientError, AuthenticationExpired

MAX_PDF_BYTES = 20 * 1024 * 1024


def _show_error(error: APIClientError) -> None:
    if error.status_code == 501:
        st.warning("This API operation is not implemented yet. The UI is ready for it.")
    elif error.status_code == 403:
        st.error("Your account does not have permission for this operation.")
    elif error.retryable:
        st.text(f"{error} You can retry when the service is available.")
    else:
        st.text(str(error))


def _clear_app_state() -> None:
    for key in list(st.session_state):
        if key.startswith("aipdf_"):
            del st.session_state[key]


def _upload_page(api: APIClient) -> None:
    st.header("Upload a PDF")
    st.caption("PDF files up to 20 MiB are accepted.")
    with st.form("aipdf_upload_form", clear_on_submit=False):
        upload = st.file_uploader("Choose a PDF", type=["pdf"], key="aipdf_pdf_file")
        submitted = st.form_submit_button(
            "Upload and process", type="primary", key="aipdf_upload_submit"
        )
    if not submitted:
        return
    if upload is None:
        st.error("Choose a PDF file first.")
        return
    if upload.size <= 0 or upload.size > MAX_PDF_BYTES:
        st.error("The PDF must be non-empty and no larger than 20 MiB.")
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
    except AuthenticationExpired:
        raise
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
    except AuthenticationExpired:
        raise
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
                st.text(str(error["message"]))
            document_id = document.get("id")
            if not document_id:
                continue
            actions = st.columns(2)
            if document.get("status") == "failed" and actions[0].button(
                "Retry processing", key=f"aipdf_retry_{document_id}"
            ):
                result = api.post(
                    f"/documents/{document_id}/retry",
                    idempotency_key=secrets.token_urlsafe(24),
                )
                if isinstance(result, dict):
                    st.success(f"Retry job accepted: {result.get('job_id', 'queued')}")
            confirmed = actions[1].checkbox(
                "Confirm deletion", key=f"aipdf_confirm_delete_{document_id}"
            )
            if confirmed and actions[1].button(
                "Delete document", key=f"aipdf_delete_{document_id}"
            ):
                result = api.delete(
                    f"/documents/{document_id}",
                    idempotency_key=secrets.token_urlsafe(24),
                )
                if isinstance(result, dict):
                    st.success(
                        f"Deletion job accepted: {result.get('job_id', 'queued')}"
                    )
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


def _chat_page(api: APIClient) -> None:
    st.header("Ask about your PDFs")
    documents_response = api.get("/documents", params={"limit": 100})
    documents = (
        documents_response.get("items", [])
        if isinstance(documents_response, dict)
        else []
    )
    if isinstance(documents_response, dict) and documents_response.get("next_cursor"):
        st.caption("The question picker shows the first 100 documents.")
    ready = [document for document in documents if document.get("status") == "ready"]
    if not ready:
        st.info("Upload a PDF and wait until it is ready before asking a question.")
        return
    labels = {
        str(document["id"]): str(document.get("original_filename", "Untitled PDF"))
        for document in ready
        if document.get("id")
    }
    with st.form("aipdf_chat_form"):
        selected = st.multiselect(
            "Choose source documents",
            options=list(labels),
            format_func=lambda document_id: labels[document_id],
            max_selections=10,
            key="aipdf_chat_documents",
        )
        question = st.text_area(
            "Your question", max_chars=2000, height=120, key="aipdf_question"
        )
        submitted = st.form_submit_button(
            "Ask question", type="primary", key="aipdf_chat_submit"
        )
    if submitted:
        if not selected:
            st.error("Select at least one ready document.")
        elif not question.strip():
            st.error("Enter a question first.")
        else:
            response = api.post(
                "/chat",
                json_body={"question": question, "document_ids": selected},
                idempotency_key=secrets.token_urlsafe(24),
            )
            if isinstance(response, dict) and response.get("job_id"):
                st.session_state["aipdf_active_chat_job"] = str(response["job_id"])
                st.success("Question accepted. Track its answer below.")
    job_id = st.session_state.get("aipdf_active_chat_job")
    if not job_id:
        return
    st.subheader("Answer job")
    refresh = st.button("Refresh answer status", key="aipdf_refresh_chat")
    if refresh or job_id:
        job = api.get(f"/jobs/{job_id}")
        if not isinstance(job, dict):
            st.error("The jobs API returned an invalid response.")
            return
        state = str(job.get("state", "unknown"))
        st.caption(f"Job state: {state.replace('_', ' ').title()}")
        if state in {"queued", "running", "retrying"}:
            st.info("Your question is being processed. Refresh to check for an answer.")
        elif state == "succeeded" and isinstance(job.get("result"), dict):
            result = job["result"]
            if result.get("insufficient_evidence"):
                st.warning("The selected documents do not provide enough evidence.")
            if result.get("answer"):
                st.text(str(result["answer"]))
            sources = result.get("sources", [])
            if sources:
                st.subheader("Sources")
                for index, source in enumerate(sources, start=1):
                    page = source.get("page_number", "?")
                    source_id = str(source.get("source_id", index))
                    with st.expander(f"Source {index} ({source_id}) · page {page}"):
                        st.text(str(source.get("filename", "PDF")))
                        st.text(str(source.get("excerpt", "")))
        elif state in {"failed", "cancelled", "expired"}:
            error = job.get("error")
            if isinstance(error, dict):
                st.text(
                    str(error.get("message", "The question could not be completed."))
                )
            else:
                st.error(f"The question job {state}.")


def _jobs_page(api: APIClient) -> None:
    st.header("Job history")
    st.caption("Track PDF ingestion, question answering, and deletion jobs.")
    filter_columns = st.columns(2)
    state = filter_columns[0].selectbox(
        "State",
        [
            "All",
            "queued",
            "running",
            "retrying",
            "succeeded",
            "failed",
            "cancelling",
            "cancelled",
            "expired",
        ],
    )
    job_type = filter_columns[1].selectbox(
        "Type", ["All", "ingestion", "answer", "cleanup"]
    )
    cursor_key = "aipdf_jobs_cursor"
    history_key = "aipdf_jobs_history"
    st.session_state.setdefault(cursor_key, None)
    st.session_state.setdefault(history_key, [])
    params = {"limit": 20}
    filter_state_key = "aipdf_jobs_filter"
    current_filters = (state, job_type)
    if st.session_state.get(filter_state_key) != current_filters:
        st.session_state[filter_state_key] = current_filters
        st.session_state[cursor_key] = None
        st.session_state[history_key] = []
    if st.session_state[cursor_key]:
        params["cursor"] = st.session_state[cursor_key]
    if state != "All":
        params["state"] = state
    if job_type != "All":
        params["type"] = job_type
    if st.button("Refresh job history"):
        st.rerun()
    result = api.get("/jobs", params=params)
    items = result.get("items", []) if isinstance(result, dict) else []
    if not items:
        st.info("No jobs match these filters.")
        return
    for job in items:
        job_id = str(job.get("id", ""))
        with st.container(border=True):
            columns = st.columns([2, 2, 3, 2])
            columns[0].text(str(job.get("type", "job")).title())
            columns[1].caption(str(job.get("state", "unknown")).title())
            columns[2].caption(f"Created: {job.get('created_at', '—')}")
            columns[3].caption(
                "Result ready" if job.get("result_available") else "No result yet"
            )
            if job_id and st.button("View details", key=f"aipdf_job_{job_id}"):
                st.session_state["aipdf_selected_job_id"] = job_id
                st.rerun()
            if job.get("state") in {"queued", "running", "retrying"} and st.button(
                "Cancel job", key=f"aipdf_cancel_{job_id}"
            ):
                response = api.post(
                    f"/jobs/{job_id}/cancel",
                    idempotency_key=secrets.token_urlsafe(24),
                )
                if isinstance(response, dict):
                    st.success("Cancellation accepted.")

    prev_col, next_col = st.columns(2)
    if prev_col.button("Previous jobs", disabled=not st.session_state[history_key]):
        st.session_state[cursor_key] = st.session_state[history_key].pop()
        st.rerun()
    next_cursor = result.get("next_cursor") if isinstance(result, dict) else None
    if next_col.button("Next jobs", disabled=not next_cursor):
        st.session_state[history_key].append(st.session_state[cursor_key])
        st.session_state[cursor_key] = next_cursor
        st.rerun()

    selected = st.session_state.get("aipdf_selected_job_id")
    if selected:
        st.subheader("Selected job")
        if st.button("Refresh selected job", key="aipdf_refresh_job_detail"):
            st.rerun()
        job = api.get(f"/jobs/{selected}")
        if not isinstance(job, dict):
            st.error("The jobs API returned an invalid response.")
            return
        st.caption(
            f"{str(job.get('type', 'job')).title()} · "
            f"{str(job.get('state', 'unknown')).replace('_', ' ').title()}"
        )
        error = job.get("error")
        if isinstance(error, dict):
            st.text(str(error.get("message", "The job failed.")))
        result_body = job.get("result")
        if isinstance(result_body, dict):
            if result_body.get("insufficient_evidence"):
                st.warning("The selected documents do not provide enough evidence.")
            if result_body.get("answer"):
                st.text(str(result_body["answer"]))
            for index, source in enumerate(result_body.get("sources", []), start=1):
                page = source.get("page_number", "?")
                source_id = str(source.get("source_id", index))
                with st.expander(f"Source {index} ({source_id}) · page {page}"):
                    st.text(str(source.get("filename", "PDF")))
                    st.text(str(source.get("excerpt", "")))


def main() -> None:
    st.set_page_config(page_title="AI PDF Chatbot", page_icon="📄")
    st.title("AI PDF Chatbot")

    if not st.user.is_logged_in:
        st.write("Sign in with the local identity provider to continue.")
        st.button("Sign in", on_click=st.login, type="primary")
        st.stop()

    st.sidebar.success("Signed in")
    if st.sidebar.button("Sign out"):
        _clear_app_state()
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
            section = st.sidebar.radio(
                "Workspace", ["Upload PDF", "Documents", "Ask a question", "Jobs"]
            )
            if section == "Upload PDF":
                _upload_page(api)
            elif section == "Documents":
                _documents_page(api)
            elif section == "Ask a question":
                _chat_page(api)
            else:
                _jobs_page(api)
    except AuthenticationExpired:
        st.warning("Your access token expired. Sign in again to continue.")
        if st.button("Sign in again", type="primary"):
            _clear_app_state()
            st.logout()
            st.stop()
    except (APIClientError, ValueError) as error:
        _show_error(error) if isinstance(error, APIClientError) else st.error(
            str(error)
        )


if __name__ == "__main__":
    main()
