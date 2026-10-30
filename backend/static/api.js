/* Same-origin API client. Passwords and session/CSRF material are never stored in web storage. */
let csrfToken = null;

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

export async function api(path, {method = 'GET', body, signal, idempotencyKey} = {}) {
  const headers = {Accept: 'application/json'};
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
  if (!['GET', 'HEAD'].includes(method)) {
    if (!csrfToken) {
      const protection = await api('/api/auth/csrf');
      csrfToken = protection.csrfToken;
    }
    headers['X-CSRF-Token'] = csrfToken;
  }
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let response;
  try {
    response = await fetch(path, {method, headers, credentials: 'same-origin', cache: 'no-store',
      body: body === undefined ? undefined : JSON.stringify(body), signal});
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError(0, 'We couldn’t reach the service. Check the connection and try again.');
  }
  let payload = null;
  if (response.status !== 204) {
    try { payload = await response.json(); }
    catch { throw new ApiError(response.status, 'The service returned an unexpected response. Refresh the page and try again.'); }
  }
  if (payload?.csrfToken) csrfToken = payload.csrfToken;
  if (!response.ok) {
    let message = payload?.error?.message || 'The request could not be completed.';
    if (response.status === 403 && /csrf|origin/i.test(message)) {
      csrfToken = null;
      message = 'Your session changed. Refresh the page and try again.';
    }
    if (response.status === 401 && !path.startsWith('/api/auth/')) {
      csrfToken = null;
      document.dispatchEvent(new Event('sessionexpired'));
    }
    throw new ApiError(response.status, message);
  }
  return payload;
}
