class RunDatabase:
    def __init__(self, db_name='runs.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.conn_thread_id = None
        self.connect()
        self.init_db() 