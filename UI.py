import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox
)
from db_connection import Neo4jConnection

class Neo4jApp(QWidget):
    def __init__(self):
        super().__init__()
        # Connect to Neo4j Aura
        self.conn = Neo4jConnection(
            "neo4j+s://77cd1c2a.databases.neo4j.io",
            "neo4j",
            "SuJsSR8y5TxBxdSfauvjfrR8CbEveaFTzKzYQ4NEUY8"
        )
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Neo4j Search UI")
        self.setGeometry(200, 200, 700, 500)

        layout = QVBoxLayout()

        # Search layout
        search_layout = QHBoxLayout()
        search_label = QLabel("Search by Node Property (e.g., number or circular_title):")
        self.search_input = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_node)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)

        # Result display
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        # Add to main layout
        layout.addLayout(search_layout)
        layout.addWidget(self.result_text)

        self.setLayout(layout)

    def search_node(self):
        query_text = self.search_input.text().strip()
        if not query_text:
            QMessageBox.warning(self, "Input Error", "Please enter a value to search!")
            return

        # Simple search query by 'number' or 'circular_title'
        cypher_query = """
        MATCH (n)
        WHERE n.number CONTAINS $value OR n.circular_title CONTAINS $value
        RETURN n LIMIT 20
        """
        try:
            results = self.conn.query(cypher_query, {"value": query_text})
            if not results:
                self.result_text.setText("No nodes found.")
                return

            output = ""
            for record in results:
                node = record["n"]
                output += f"Node ID: {node.id}\n"
                output += f"Labels: {', '.join(node.labels)}\n"
                output += "Properties:\n"
                for k, v in node._properties.items():
                    output += f"  {k}: {v}\n"
                output += "-"*50 + "\n"

            self.result_text.setText(output)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch nodes:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Neo4jApp()
    window.show()
    sys.exit(app.exec_())
