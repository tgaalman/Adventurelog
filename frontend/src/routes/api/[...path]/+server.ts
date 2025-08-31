const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';
import { fetchCSRFToken } from '$lib/index.server';
import { json } from '@sveltejs/kit';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
	const { url, params, request, fetch, cookies } = event;
	const searchParam = url.search ? `${url.search}&format=json` : '?format=json';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

/** @type {import('./$types').RequestHandler} */
export async function POST({ url, params, request, fetch, cookies }) {
	const searchParam = url.search ? `${url.search}` : '';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

export async function PATCH({ url, params, request, fetch, cookies }) {
	const searchParam = url.search ? `${url.search}&format=json` : '?format=json';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

export async function PUT({ url, params, request, fetch, cookies }) {
	const searchParam = url.search ? `${url.search}&format=json` : '?format=json';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

export async function DELETE({ url, params, request, fetch, cookies }) {
	const searchParam = url.search ? `${url.search}&format=json` : '?format=json';
	return handleRequest(url, params, request, fetch, cookies, searchParam, true);
}

async function handleRequest(
	url: any,
	params: any,
	request: any,
	fetch: any,
	cookies: any,
	searchParam: string,
	requreTrailingSlash: boolean | undefined = false
) {
	const path = params.path;
	let targetUrl = `${endpoint}/api/${path}`;

	// Ensure the path ends with a trailing slash
	if (requreTrailingSlash && !targetUrl.endsWith('/')) {
		targetUrl += '/';
	}

	// Append query parameters to the path correctly
	targetUrl += searchParam; // This will add ?format=json or &format=json to the URL

	const headers = new Headers(request.headers);

	// Delete existing csrf cookie by setting an expired date
	cookies.delete('csrftoken', { path: '/' });

	// Generate a new csrf token (using your existing fetchCSRFToken function)
	const csrfToken = await fetchCSRFToken();
	if (!csrfToken) {
		return json({ error: 'CSRF token is missing or invalid' }, { status: 400 });
	}

	// Merge incoming cookies with refreshed csrftoken while preserving sessionid
	const incomingCookie = headers.get('cookie') || '';
	let mergedCookie = incomingCookie;
	if (incomingCookie.toLowerCase().includes('csrftoken=')) {
		mergedCookie = incomingCookie.replace(/csrftoken=[^;]*/i, `csrftoken=${csrfToken}`);
	} else if (incomingCookie) {
		mergedCookie = `${incomingCookie}; csrftoken=${csrfToken}`;
	} else {
		mergedCookie = `csrftoken=${csrfToken}`;
	}

	// Extract session id to also send as X-Session-Token (middleware support)
	const sessionMatch = incomingCookie.match(/(?:^|;\s*)sessionid=([^;]+)/i);
	const sessionId = sessionMatch ? sessionMatch[1] : '';

	try {
		const response = await fetch(targetUrl, {
			method: request.method,
			headers: {
				...Object.fromEntries(headers),
				'X-CSRFToken': csrfToken,
				Cookie: mergedCookie,
				...(sessionId ? { 'X-Session-Token': sessionId } : {})
			},
			body:
				request.method !== 'GET' && request.method !== 'HEAD' ? await request.text() : undefined,
			credentials: 'include' // This line ensures cookies are sent with the request
		});

		if (response.status === 204) {
			return new Response(null, {
				status: 204,
				headers: response.headers
			});
		}

		const responseData = await response.arrayBuffer();
		// Create a new Headers object without the 'set-cookie' header
		const cleanHeaders = new Headers(response.headers);
		cleanHeaders.delete('set-cookie');

		return new Response(responseData, {
			status: response.status,
			headers: cleanHeaders
		});
	} catch (error) {
		console.error('Error forwarding request:', error);
		return json({ error: 'Internal Server Error' }, { status: 500 });
	}
}
