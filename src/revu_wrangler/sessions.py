import os
import pathlib
from typing import Any, Dict, Iterable, Optional

import httpx

from .config import API_ROOT, DEFAULT_RETRY_BACKOFF_BASE, DEFAULT_RETRY_STATUS_CODES, DEFAULT_MAX_RETRIES
from .exceptions import UnsupportedOperationError
from .utils import retry, raise_for_status_mapped

class SessionsAPI:
    """
    Abstraction over Session-related endpoints.
    Focus on: create/list/get/delete sessions, upload/list/get files, snapshot download.
    """

    def __init__(
        self,
        *,
        http: httpx.Client,
        base_url: str,
        client_id: str,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_base: float = DEFAULT_RETRY_BACKOFF_BASE,
        retry_statuses: Optional[Iterable[int]] = None,
    ):
        self._http = http
        self.base_url = base_url
        self.client_id = client_id
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.retry_statuses = set(retry_statuses or DEFAULT_RETRY_STATUS_CODES)

    # ---------- helper ----------
    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"client_id": self.client_id}
        if extra:
            h.update(extra)
        return h

    # ---------- Session CRUD ----------
    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def create_session(self, *, name: str, description: Optional[str] = None, restricted: Optional[bool] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{API_ROOT}/sessions"
        body: Dict[str, Any] = {"Name": name}
        if description is not None:
            body["Description"] = description
        if restricted is not None:
            body["Restricted"] = bool(restricted)
        resp = self._http.post(url, headers=self._headers(), json=body)
        raise_for_status_mapped(resp)
        return resp.json()

    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def list_sessions(self, *, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        url = f"{self.base_url}{API_ROOT}/sessions"
        params = {"page": page, "pageSize": page_size}
        resp = self._http.get(url, headers=self._headers(), params=params)
        raise_for_status_mapped(resp)
        return resp.json()

    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def get_session(self, session_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}{API_ROOT}/sessions/{session_id}"
        resp = self._http.get(url, headers=self._headers())
        raise_for_status_mapped(resp)
        return resp.json()

    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def delete_session(self, session_id: str) -> None:
        url = f"{self.base_url}{API_ROOT}/sessions/{session_id}"
        resp = self._http.delete(url, headers=self._headers())
        raise_for_status_mapped(resp)

    # ---------- Files (upload → confirm) ----------
    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def _create_file_placeholder(self, session_id: str, *, name: str, source: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{API_ROOT}/sessions/{session_id}/files"
        body: Dict[str, Any] = {"Name": name}
        if source:
            body["Source"] = source
        resp = self._http.post(url, headers=self._headers(), json=body)
        raise_for_status_mapped(resp)
        return resp.json()  # expect: { "Id": ..., "UploadUrl": "...", "UploadContentType": "Application/PDF" }

    def _guess_content_type(self, upload_content_type: Optional[str]) -> str:
        if upload_content_type:
            return upload_content_type
        return "application/pdf"

    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def _confirm_upload(self, session_id: str, file_id: str) -> None:
        url = f"{self.base_url}{API_ROOT}/sessions/{session_id}/files/{file_id}/confirm-upload"
        resp = self._http.post(url, headers=self._headers())
        raise_for_status_mapped(resp)

    def upload_pdf(
        self,
        session_id: str,
        file_path: str,
        *,
        source: Optional[str] = None,
        require_pdf_extension: bool = True,
        add_sse_header: bool = True,
        put_timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Multi-step upload:
         1) Create placeholder -> UploadUrl, fileId
         2) PUT the bytes to UploadUrl (direct to storage)
         3) Confirm upload
        Returns dict with at least {"Id": <fileId>, ...}
        """
        name = pathlib.Path(file_path).name
        if require_pdf_extension and not name.lower().endswith(".pdf"):
            raise ValueError("Sessions only support PDF files; file must end with .pdf")

        placeholder = self._create_file_placeholder(session_id, name=name, source=source)
        file_id = str(placeholder["Id"])
        upload_url = placeholder["UploadUrl"]
        upload_ct = self._guess_content_type(placeholder.get("UploadContentType"))

        # Stream upload to pre-signed URL
        headers = {"Content-Type": upload_ct}
        if add_sse_header:
            # S3 encryption header (docs indicate AES256 commonly required)
            headers["x-amz-server-side-encryption"] = "AES256"

        with open(file_path, "rb") as f:
            resp = httpx.put(upload_url, content=f, headers=headers, timeout=put_timeout or 120.0)
        # Presigned URL response: non-2xx means upload failed
        if not (200 <= resp.status_code < 300):
            resp.raise_for_status()

        # Confirm
        self._confirm_upload(session_id, file_id)
        # Return minimal info (caller can list/get for full metadata)
        return {"Id": file_id, "Name": name}

    # ---------- Files (list/get) ----------
    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def list_files(self, session_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}{API_ROOT}/sessions/{session_id}/files"
        resp = self._http.get(url, headers=self._headers())
        raise_for_status_mapped(resp)
        return resp.json()

    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def get_file(self, session_id: str, file_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}{API_ROOT}/sessions/{session_id}/files/{file_id}"
        resp = self._http.get(url, headers=self._headers())
        raise_for_status_mapped(resp)
        return resp.json()

    # ---------- Files (delete) ----------
    def delete_file(self, session_id: str, file_id: str) -> None:
        """
        NOTE: As of the public docs surveyed, an explicit Session-file DELETE endpoint
        is not clearly documented. Raise UnsupportedOperationError until verified.
        """
        raise UnsupportedOperationError("Delete file from Session is not documented by the public API.")

    # ---------- Snapshots (PDF + markups) ----------
    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def request_snapshot(self, session_id: str, file_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}{API_ROOT}/sessions/{session_id}/files/{file_id}/snapshot"
        resp = self._http.post(url, headers=self._headers())
        raise_for_status_mapped(resp)
        return resp.json()

    @retry(max_retries=DEFAULT_MAX_RETRIES, backoff_base=DEFAULT_RETRY_BACKOFF_BASE, retry_statuses=DEFAULT_RETRY_STATUS_CODES)
    def get_snapshot_status(self, session_id: str, file_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}{API_ROOT}/sessions/{session_id}/files/{file_id}/snapshot"
        resp = self._http.get(url, headers=self._headers())
        raise_for_status_mapped(resp)
        return resp.json()

    def download_snapshot_when_ready(
        self,
        session_id: str,
        file_id: str,
        dest_path: str,
        *,
        poll_interval: float = 3.0,
        max_polls: int = 200,
    ) -> str:
        """
        Requests a snapshot, polls until complete, downloads to dest_path.
        Returns dest_path on success.
        """
        self.request_snapshot(session_id, file_id)
        attempts = 0
        download_url: Optional[str] = None

        while attempts < max_polls:
            attempts += 1
            status = self.get_snapshot_status(session_id, file_id)
            if str(status.get("Status", "")).lower() == "complete" and status.get("DownloadUrl"):
                download_url = status["DownloadUrl"]
                break
            import time as _time
            _time.sleep(poll_interval)

        if not download_url:
            raise RuntimeError("Snapshot did not complete within polling window")

        # Download the combined PDF
        with httpx.stream("GET", download_url, timeout=120.0) as r:
            r.raise_for_status()
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        return dest_path
