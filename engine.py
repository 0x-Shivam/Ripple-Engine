import networkx as nx
import random


class ButterflyPredictionEngine:
    def __init__(self):
        # Directed Graph instance
        self.graph = nx.DiGraph()
        self.initialize_infrastructure_network()

    def _initialize_infrastructure_network (self):
        """
        Step 1: Map out the directional nodes and structual edges.
        We estabilsh the path that the 'Butterfly Effect' ripple though.
        """

        #core decision node 