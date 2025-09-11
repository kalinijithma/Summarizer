from neo4j import GraphDatabase

class Neo4jConnection:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            print("Successfully connected to Neo4j Aura!")
        except Exception as e:
            print("Error connecting to Neo4j:", e)

    def close(self):
        self.driver.close()

    def query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

# Usage example
if __name__ == "__main__":
    uri = "neo4j+s://77cd1c2a.databases.neo4j.io"
    user = "neo4j"
    password = "SuJsSR8y5TxBxdSfauvjfrR8CbEveaFTzKzYQ4NEUY8"

    conn = Neo4jConnection(uri, user, password)
    # Test query
    results = conn.query("MATCH (n) RETURN n LIMIT 5")
    for record in results:
        print(record)
    conn.close()
