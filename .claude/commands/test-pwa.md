Start the PWA dev server by running Python's built-in HTTP server on port 8080, serving the `docs/` directory from the project root:

```bash
python3 -m http.server 8080 --directory docs/
```

Run this in the background, then tell the user the app is available at http://localhost:8080 and remind them that Chrome treats localhost as a secure context so service workers and the install prompt will work.
