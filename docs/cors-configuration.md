# CORS Configuration Guide

## Overview
The backend API uses django-cors-headers to handle Cross-Origin Resource Sharing (CORS) requests from the frontend application.

## Development Configuration

In development (`backend/apps/config/settings/local.py`), CORS is configured to allow the following origins:

- `http://localhost:5173` - Vite development server (default)
- `http://127.0.0.1:5173` - Vite development server (IP)
- `http://localhost:3000` - Alternative React dev server
- `http://127.0.0.1:3000` - Alternative React dev server (IP)

### Key Settings:
```python
CORS_ALLOW_ALL_ORIGINS = False  # Explicit origin whitelist
CORS_ALLOWED_ORIGINS = [...]    # List of allowed origins
CORS_ALLOW_CREDENTIALS = True   # Allow cookies/auth headers
```

## Production Configuration

In production (`backend/apps/config/settings/prod.py`), CORS origins are configured via environment variables:

### Environment Variables:
```bash
# In your .env file or deployment configuration
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Key Settings:
```python
CORS_ALLOW_ALL_ORIGINS = False              # Never allow all origins in production
CORS_ALLOWED_ORIGINS = env.list(...)        # From environment variable
CORS_ALLOW_CREDENTIALS = True               # For authenticated requests
CORS_PREFLIGHT_MAX_AGE = 86400             # Cache preflight for 24 hours
```

## Testing CORS

### Quick Test with curl:
```bash
# Test preflight request
curl -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://localhost:8000/api/health/

# Test actual request
curl -H "Origin: http://localhost:5173" \
     http://localhost:8000/api/health/
```

### Expected Headers:
A successful CORS response should include:
- `Access-Control-Allow-Origin: http://localhost:5173`
- `Access-Control-Allow-Credentials: true`
- `Vary: Origin`

## Common Issues

### 1. CORS Error in Browser Console
**Symptom:** "Access to fetch at 'http://localhost:8000/api/...' from origin 'http://localhost:5173' has been blocked by CORS policy"

**Solution:** 
- Ensure the frontend URL is in `CORS_ALLOWED_ORIGINS`
- Check that the backend server is running
- Verify the request URL is correct

### 2. Credentials Not Being Sent
**Symptom:** Authentication cookies/headers not included in requests

**Solution:**
- Ensure `CORS_ALLOW_CREDENTIALS = True` in backend
- Include `credentials: 'include'` in frontend fetch requests
- Use `withCredentials: true` in Axios

### 3. Preflight Requests Failing
**Symptom:** OPTIONS requests returning 403 or 404

**Solution:**
- Ensure CORS middleware is before CommonMiddleware in MIDDLEWARE
- Check that the API endpoint exists
- Verify allowed methods include OPTIONS

## Security Best Practices

1. **Never use `CORS_ALLOW_ALL_ORIGINS = True` in production**
   - Always explicitly whitelist trusted origins

2. **Use HTTPS in production**
   - Configure `CORS_ALLOWED_ORIGINS` with https:// URLs only

3. **Limit allowed headers and methods**
   - Can be configured with `CORS_ALLOW_HEADERS` and `CORS_ALLOW_METHODS`

4. **Use credentials carefully**
   - Only set `CORS_ALLOW_CREDENTIALS = True` if your API requires authentication

## Deployment Checklist

- [ ] Set `CORS_ALLOWED_ORIGINS` environment variable with production frontend URL(s)
- [ ] Ensure all origins use HTTPS in production
- [ ] Test CORS configuration before deploying
- [ ] Monitor CORS errors in production logs
- [ ] Document any custom CORS requirements for your API

## Additional Resources

- [django-cors-headers documentation](https://github.com/adamchainz/django-cors-headers)
- [MDN CORS documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [CORS Testing Tools](https://www.test-cors.org/)