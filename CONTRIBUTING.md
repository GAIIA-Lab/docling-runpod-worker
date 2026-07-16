# Contributing

Contributions that keep the worker portable and its request/response contract
stable are welcome.

## Development workflow

1. Fork and clone the repository.
2. Create a branch from `main`.
3. Create a Python virtual environment and run `pip install -r requirements.txt`.
4. Run `python -m unittest discover -s tests -v`.
5. Open a pull request describing the behaviour change and its validation.

Keep application-specific persistence, schemas, classification, and business
logic in the calling application. Never commit API keys, callback secrets, test
documents containing private data, or generated extraction output.
