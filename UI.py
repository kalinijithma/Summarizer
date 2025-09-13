import sys
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QScrollArea, QFrame, QTextBrowser
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
        self.load_labels()

    def initUI(self):
        self.setWindowTitle("Neo4j Search UI")
        self.setGeometry(200, 200, 1200, 700)  # wider for side-by-side view

        main_layout = QHBoxLayout()  # Horizontal split

        # ---------------- Left Panel (Labels / Buttons) ----------------
        # ---------------- Left Panel (Labels / Buttons) ----------------
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Available Node Labels:"))

        self.label_buttons_layout = QVBoxLayout()
        self.label_buttons_widget = QWidget()
        self.label_buttons_widget.setLayout(self.label_buttons_layout)

        # Remove scroll area, just add the widget directly
        left_panel.addWidget(self.label_buttons_widget)
        left_panel.addStretch()  # Push buttons to top

        # ---------------- Right Panel (Search + Results) ----------------
        right_panel = QVBoxLayout()

        # Search layout
        search_layout = QHBoxLayout()
        search_label = QLabel("Search by Node Property (number / circular_title):")
        self.search_input = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_node)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)

        # Result display
        self.result_text = QTextBrowser()
        self.result_text.setOpenExternalLinks(True)
        self.result_text.anchorClicked.connect(self.handle_internal_link)

        # Add search + results to right panel
        right_panel.addLayout(search_layout)
        right_panel.addWidget(QLabel("Results:"))
        right_panel.addWidget(self.result_text, stretch=1)

        # ---------------- Combine Left and Right ----------------
        main_layout.addLayout(left_panel, stretch=1)  # Left panel narrower
        main_layout.addLayout(right_panel, stretch=3)  # Right panel wider

        self.setLayout(main_layout)

    def load_labels(self):
        """Fetch all labels and create buttons dynamically"""
        try:
            results = self.conn.query("CALL db.labels()")
            if not results:
                self.result_text.setText("No labels found in database.")
                return

            for record in results:
                label = record['label']
                btn = QPushButton(label)
                btn.clicked.connect(lambda checked, l=label: self.show_nodes_by_label(l))
                self.label_buttons_layout.addWidget(btn)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch labels:\n{e}")

    def format_node_output(self, node):
        """Format node properties into HTML with clickable links and references"""
        output = f"<b>Node ID:</b> {node.id}<br>"
        output += f"<b>Labels:</b> {', '.join(node.labels)}<br>"
        output += "<b>Properties:</b><br><ul>"

        for k, v in node._properties.items():
            if k == "link" and str(v).startswith("http"):
                # Make external link clickable
                output += f"<li>{k}: <a href='{v}' target='_blank'>{v}</a></li>"
            elif k == "content":
                content_html = self.linkify_references(str(v))
                output += f"<li>{k}:<br><div style='margin-left:15px;'>{content_html}</div></li>"
            else:
                output += f"<li>{k}: {v}</li>"

        output += "</ul><hr>"
        return output

    def linkify_references(self, text):
        """
        Detect phrases like 'Circular No. 843' and make them clickable
        Internal links are formatted as neo4j://circular/843
        """
        pattern = r"(Circular\s+No\.?\s*\d+)"
        return re.sub(pattern,
                      lambda m: f"<a href='neo4j://circular/{m.group(0).split()[-1]}'>{m.group(0)}</a>",
                      text)

    def handle_internal_link(self, url):
        """Handle clicks on internal neo4j:// links"""
        url_str = url.toString()
        if url_str.startswith("neo4j://circular/"):
            circular_number = url_str.split("/")[-1]

            cypher_query = """
            MATCH (n)
            WHERE n.number = $num
            RETURN n LIMIT 1
            """
            results = self.conn.query(cypher_query, {"num": circular_number})

            if results:
                node = results[0]["n"]
                self.result_text.setHtml(self.format_node_output(node))
            else:
                QMessageBox.information(self, "Not Found", f"Circular {circular_number} not found in DB.")

    def show_nodes_by_label(self, label):
        """Fetch and display all nodes belonging to a specific label"""
        cypher_query = f"""
        MATCH (n:`{label}`)
        RETURN n LIMIT 20
        """
        try:
            results = self.conn.query(cypher_query)
            if not results:
                self.result_text.setText(f"No nodes found for label: {label}")
                return

            output = f"<h3>Nodes with label: {label}</h3><hr>"
            for record in results:
                node = record["n"]
                output += self.format_node_output(node)

            self.result_text.setHtml(output)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch nodes for {label}:\n{e}")

    def search_node(self):
        query_text = self.search_input.text().strip()
        if not query_text:
            QMessageBox.warning(self, "Input Error", "Please enter a value to search!")
            return

        cypher_query = """
        MATCH (n)
        WHERE (n.number IS NOT NULL AND toString(n.number) CONTAINS $value)
           OR (n.circular_title IS NOT NULL AND toLower(toString(n.circular_title)) CONTAINS toLower($value))
        RETURN n LIMIT 20
        """
        try:
            results = self.conn.query(cypher_query, {"value": query_text})
            if not results:
                self.result_text.setText("No nodes found.")
                return

            output = f"<h3>Search results for: {query_text}</h3><hr>"
            for record in results:
                node = record["n"]
                output += self.format_node_output(node)

            self.result_text.setHtml(output)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch nodes:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Neo4jApp()
    window.show()
    sys.exit(app.exec_())
