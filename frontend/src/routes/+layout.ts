// The application is a client-rendered single-page app. Authentication state lives in an HttpOnly cookie that the browser
// sends to /api, so no page content depends on localStorage or on server-rendered secrets.
export const ssr = false;
export const prerender = false;
