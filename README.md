# WeHome.io 
```
              _
__      _____| |__   ___  _ __ ___   ___
\ \ /\ / / _ \ '_ \ / _ \| '_ ` _ \ / _ \
 \ V  V /  __/ | | | (_) | | | | | |  __/
  \_/\_/ \___|_| |_|\___/|_| |_| |_|\___|
  
```

version control
## Development

### Run Back-End

```sh
# cp config.py.sample config.py
$ python manage.py runserver
```

### Run Background tasks
```sh
# in venv
celery -A index.celery worker --loglevel=DEBUG
```

### Test Back-End

```sh
$ python test.py --cov-report=term --cov-report=html --cov=application/ tests/
```

### Git commit message
Use our commit template as your default commit message.

*Notice*: This only works when you do `git commit` without specifying `-m`.

```sh
$ git config commit.template ./COMMIT_TEMPLATE.md
```

## Installation

### Create DB
```sh
$ export DATABASE_URL="postgresql://localhost/yourdb"

or

$ export DATABASE_URL="mysql+mysqlconnector://localhost/yourdb"

or

$ export DATABASE_URL="sqlite:///your.db"

$ python manage.py create_db
$ python manage.py db upgrade
$ python manage.py db migrate
```

To update database after creating new migrations, use:

```sh
$ python manage.py db upgrade
```

