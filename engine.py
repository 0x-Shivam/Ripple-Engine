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

        self.graph.add_node("Proposed_Metro_Hub", type="intervention")

        # Impact sector node 

        self.graph.add_node([
            ("Mobility_Sector", {"type": "sector"}),
            ("Environmental_Sector", {"type": "sector"}),
            ("Economic_Sector", {"type": "sector"})

        
        ])


        # end point meteric nodes 

        self.graph.add_nodes_from([
            ("Traffic_Flow", {"type": "metric", "base_unit" : "%"}),
            ("Air_Quality", {"type": "metric", "base_unit" : "%"}),
            ("Jobs_Created", {"type": "metric", "base_unit" : "%"}),
            ("Flood_Risk", {"type": "metric", "base_unit" : "%"}),
            ("Green_Spaces", {"type": "metric", "base_unit" : "%"}),("Property_Value", {"type": "metric", "base_unit" : "%"}),("Noise_Level", {"type": "metric", "base_unit" : "%"})
        ])