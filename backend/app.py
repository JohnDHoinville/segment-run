fetch(`${API_URL}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password }),
  credentials: 'include'    // <-- important
}); 

fetch(`${API_URL}/runs`, {
  credentials: 'include',   // <-- important 
}); 

app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='None',  # or 'Lax' if same-site is enough
    # ...
) 

CORS(
    app,
    origins=["http://localhost:3000"],
    allow_headers=["Content-Type", "Accept", "Cookie"],
    supports_credentials=True,
    expose_headers=["Content-Type", "Authorization", "Set-Cookie"],
    allow_credentials=True
) 