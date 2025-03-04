import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'  # Secret key for session management
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable Flask-SQLAlchemy track modifications to save resources

    # Database connection details using SQLAlchemy and ODBC for SQL Server
    SQLALCHEMY_DATABASE_URI = (
        "mssql+pyodbc:///?odbc_connect="
        + os.environ.get('DB_CONNECTION_STRING')
        or 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=88.222.244.120;DATABASE=newHosp;UID=ams;PWD=pC6p[Pb84et0'
    )

    # Optional: You can add logging settings or other configurations here if needed
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
