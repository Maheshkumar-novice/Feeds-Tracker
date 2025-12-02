# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please open an issue or contact the maintainer directly.

## Security Best Practices

### Environment Variables
- **NEVER** commit your `.env` file to version control.
- The `.env` file contains sensitive information like `ADMIN_TOKEN`.
- Ensure `.env` is listed in your `.gitignore` file.

### Authentication
- This application uses a simple token-based authentication system (`Bearer` token).
- The `ADMIN_TOKEN` is required for all write operations (Add Feed, Delete Feed, Refresh).
- Read operations are public by default. If you need a private reader, you must implement additional protection for GET endpoints.

### Deployment
- **Debug Mode:** Ensure `FLASK_DEBUG` is set to `False` in production.
- **HTTPS:** Always serve this application over HTTPS in production to protect the `ADMIN_TOKEN` during transmission.
- **CORS:** The default configuration allows all origins (`*`). For production, configure CORS to allow only your frontend domain.

### Dependencies
- Keep dependencies up to date using `uv` or `pip`.
- Regularly check for vulnerabilities in dependencies.
