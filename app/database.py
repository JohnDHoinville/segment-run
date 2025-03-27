import traceback

class RunDatabase:
    def __init__(self, db_name='runs.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.conn_thread_id = None
        
        # Catch any connection errors during initialization
        try:
            self.connect()
            
            # Wrap init_db in its own try-except to prevent startup errors
            try:
                self.init_db()
                print("Database initialized successfully")
            except Exception as init_error:
                print(f"WARNING: Database initialization error: {str(init_error)}")
                print("The application will continue, but database functionality may be limited")
                traceback.print_exc()
                
        except Exception as conn_error:
            print(f"CRITICAL: Database connection error during initialization: {str(conn_error)}")
            print("The application will continue, but database functionality will be unavailable")
            traceback.print_exc() 