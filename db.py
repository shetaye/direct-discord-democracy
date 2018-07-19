class DBTable:
    """Wrapper class for the mongo database"""
    def __init__(self,table):
        self.table = table

    def store_action(self,action):
        """Serialies and stores a single action"""
        pass
    
    def query_one(self,query):
        """Pases a query to the underlying database and returns a single action"""
        pass

    def query_many(self,query):
        """Passes on a query to the underlying database and returns a list of actions"""
        pass
    
    def find_by_id(self,id):
        """Queries and returns a single action with the specified ID"""
        pass