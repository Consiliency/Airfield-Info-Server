# Airport Information Server

A Django-based backend server for managing and serving airport information.

## Features

- RESTful API for airport information
- Built with Django and Django REST Framework
- Poetry for dependency management

## Setup

1. Clone the repository:
```bash
git clone https://github.com/Consiliency/air_field_info_server.git
cd air_field_info_server
```

2. Install dependencies with Poetry:
```bash
poetry install
```

3. Run migrations:
```bash
poetry run python manage.py migrate
```

4. Start the development server:
```bash
poetry run python manage.py runserver
```

## Development

This project uses:
- Django 5.1.4
- Django REST Framework 3.15.2
- Poetry for dependency management
- Python 3.10+

## License

MIT
