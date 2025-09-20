import sys
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
    QScrollArea, QFrame, QTextEdit
)
from PyQt5.QtCore import Qt
from db_connection import Neo4jConnection
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx


class Neo4jApp(QWidget):
    def __init__(self):
        super().__init__()
        # Neo4j connection
        self.conn = Neo4jConnection(
            "neo4j+s://77cd1c2a.databases.neo4j.io",
            "neo4j",
            "SuJsSR8y5TxBxdSfauvjfrR8CbEveaFTzKzYQ4NEUY8"
        )
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.initUI()
        self.load_labels()

    def initUI(self):
        self.setWindowTitle("Neo4j Search UI")
        self.setGeometry(200, 200, 1200, 700)
        main_layout = QHBoxLayout()

        # Left panel
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Available Node Labels:"))
        self.label_buttons_layout = QVBoxLayout()
        left_panel.addLayout(self.label_buttons_layout)
        left_panel.addStretch()

        # Right panel
        right_panel = QVBoxLayout()
        search_layout = QHBoxLayout()
        search_label = QLabel("Search by Node Property (number / circular_title):")
        self.search_input = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_node)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        right_panel.addLayout(search_layout)

        # Scrollable area for results
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)
        right_panel.addWidget(self.scroll_area)

        main_layout.addLayout(left_panel, stretch=1)
        main_layout.addLayout(right_panel, stretch=3)
        self.setLayout(main_layout)

    def load_labels(self):
        try:
            results = self.conn.query("CALL db.labels()")
            if not results:
                return
            for record in results:
                label = record['label']
                btn = QPushButton(label)
                btn.clicked.connect(lambda checked, l=label: self.show_nodes_by_label(l))
                self.label_buttons_layout.addWidget(btn)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch labels:\n{e}")

    def clear_results(self):
        # Remove all widgets from scroll layout
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

    def show_nodes_by_label(self, label):
        cypher_query = f"MATCH (n:`{label}`) RETURN n LIMIT 50"
        try:
            results = self.conn.query(cypher_query)
            if not results:
                QMessageBox.information(self, "Info", f"No nodes found for label {label}")
                return
            nodes = [r["n"] for r in results]
            self.display_nodes(nodes)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def search_node(self):
        query_text = self.search_input.text().strip()
        if not query_text:
            return
        cypher_query = """
        MATCH (n)
        WHERE (n.number IS NOT NULL AND toString(n.number) CONTAINS $value)
           OR (n.circular_title IS NOT NULL AND toLower(toString(n.circular_title)) CONTAINS toLower($value))
        RETURN n LIMIT 50
        """
        try:
            results = self.conn.query(cypher_query, {"value": query_text})
            if not results:
                QMessageBox.information(self, "Info", "No nodes found.")
                return
            nodes = [r["n"] for r in results]
            self.display_nodes(nodes)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def display_nodes(self, nodes):
        self.clear_results()
        for node in nodes:
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            layout = QVBoxLayout()

            # Node info
            info = f"<b>Node ID:</b> {node.element_id}<br><b>Labels:</b> {', '.join(node.labels)}<br>"
            for k, v in node._properties.items():
                if k == "link" and str(v).startswith("http"):
                    info += f"<b>{k}:</b> <a href='{v}' target='_blank'>{v}</a><br>"
                else:
                    info += f"<b>{k}:</b> {v}<br>"

            content_label = QLabel()
            content_label.setTextFormat(Qt.RichText)
            content_label.setText(info)
            content_label.setWordWrap(True)
            layout.addWidget(content_label)

            # Summarize button
            summarize_btn = QPushButton(f"Summarize Circular {node._properties.get('number','')}")
            layout.addWidget(summarize_btn)

            # Summary output
            summary_label = QLabel()
            summary_label.setWordWrap(True)
            layout.addWidget(summary_label)

            # Store sentences & embeddings
            content = node._properties.get("content","")
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            embeddings = self.model.encode(sentences)
            node._sentences = sentences
            node._sentence_embeddings = embeddings

            # Connect button
            summarize_btn.clicked.connect(lambda _, n=node, s_label=summary_label: self.show_summary(n, s_label))

            frame.setLayout(layout)
            self.scroll_layout.addWidget(frame)

    def show_summary(self, node, summary_label, top_n=3):
        sentences = node._sentences
        embeddings = node._sentence_embeddings

        # Step 1: Compute semantic similarity
        sim_matrix = cosine_similarity(embeddings)

        # Step 2: Build a graph where sentences are nodes
        nx_graph = nx.from_numpy_array(sim_matrix)

        # Step 3: Rank sentences using TextRank/PageRank
        scores = nx.pagerank(nx_graph)

        # Step 4: Select top N important sentences
        ranked = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)
        top_sentences = [s for _, s in ranked[:top_n]]

        # Step 5: Reorder sentences as in original text
        summary = " ".join([s for s in sentences if s in top_sentences])

        # Step 6: Display summary in GUI
        summary_label.setText(f"<b>Summary:</b> {summary}")

# Take all sentences of the circular (node._sentences).
# Compute embeddings (already stored in node._sentence_embeddings).
# Calculate similarity between sentences → produces a matrix of how similar each sentence is to the others.
# Build a graph → sentences are nodes, similarities are edges.
# Run TextRank/PageRank → scores each sentence based on importance.
# Pick top sentences (e.g., top 3 by default).
# Reorder the selected sentences as in the original content.
# Show the summary in the GUI below the Summarize button.

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Neo4jApp()
    window.show()
    sys.exit(app.exec_())
