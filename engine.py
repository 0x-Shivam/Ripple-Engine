print("Loading Butterfly Prediction Engine Core.")
import networkx as nx
import random

class ButterflyPredictionEngine:
    def __init__(self):
       # Directed Graph instance
        self.graph = nx.DiGraph()
        self._initialize_infrastructure_network()
        
    def _initialize_infrastructure_network(self):
        """
        Step 1: Map out the directional nodes and structural edges.
        We establish the paths that the 'Butterfly Effect' ripples through.
        """
         #core decision node 
        self.graph.add_node("Proposed_Metro_Hub", type="intervention")
        
        
        self.graph.add_nodes_from([
            ("Mobility_Sector", {"type": "sector"}),
            ("Environmental_Sector", {"type": "sector"}),
            ("Economic_Sector", {"type": "sector"})
        ])
        
         # end point meteric nodes 
        self.graph.add_nodes_from([
            ("Traffic_Flow", {"type": "metric", "base_unit": "%"}),
            ("Air_Quality", {"type": "metric", "base_unit": "%"}),
            ("Jobs_Created", {"type": "metric", "base_unit": "count"}),
            ("Flood_Risk", {"type": "metric", "base_unit": "%"}),
            ("Green_Spaces", {"type": "metric", "base_unit": "%"}),
            ("Property_Value", {"type": "metric", "base_unit": "%"}),
            ("Noise_Level", {"type": "metric", "base_unit": "%"})
        ])

        # (Intervention -> Sector)
        self.graph.add_edge("Proposed_Metro_Hub", "Mobility_Sector")
        self.graph.add_edge("Proposed_Metro_Hub", "Environmental_Sector")
        self.graph.add_edge("Proposed_Metro_Hub", "Economic_Sector")

        #  (Sector -> Final Metrics)
        # Mobility impacts

        self.graph.add_edge("Mobility_Sector", "Traffic_Flow", coefficient=0.18)
        self.graph.add_edge("Mobility_Sector", "Noise_Level", coefficient=-0.12) # Public transport can reduce car noise
        
        # Environmental impacts
        self.graph.add_edge("Environmental_Sector", "Air_Quality", coefficient=0.24) 
        self.graph.add_edge("Environmental_Sector", "Green_Spaces", coefficient=0.21) 
        self.graph.add_edge("Environmental_Sector", "Flood_Risk", coefficient=-0.14) 
        
        # Economic impacts
        self.graph.add_edge("Economic_Sector", "Jobs_Created", coefficient=1200) # Raw numbers instead of %

        self.graph.add_edge("Economic_Sector", "Property_Value", coefficient=0.16)

    def calculate_predictions(self, target_node, target_year=2035):
        """
        Calculates downstream changes scaled by year targets (2025-2050).
        Includes a deterministic growth factor plus small Monte Carlo variance.
        """
        predictions = {}
        if target_node not in self.graph:
            return predictions
            
       
        base_year = 2025
        years_passed = max(0, target_year - base_year)
        time_multiplier = 1.0 + (years_passed * 0.05) 

        # Traverse the entire graph to collect target metric nodes
        for sector in list(self.graph.successors(target_node)):
            for metric in list(self.graph.successors(sector)):
                edge_data = self.graph.get_edge_data(sector, metric)
                coefficient = edge_data.get("coefficient", 0.1)
                
                
                variance = random.uniform(0.98, 1.02)
                raw_value = coefficient * time_multiplier * variance
                
                # Format string values perfectly based on metric types

                node_data = self.graph.nodes[metric]
                if node_data.get("base_unit") == "count":
                    predictions[metric] = f"+{int(raw_value)}"
                else:
                    percentage = int(raw_value * 100)
                    sign = "+" if percentage > 0 else ""
                    predictions[metric] = f"{sign}{percentage}%"
                    
        return predictions
    

            
            #local verifcation test

if __name__ == "__main__":
    print(" Running local verification test...")
    engine = ButterflyPredictionEngine()
    
   
    results = engine.calculate_predictions("Proposed_Metro_Hub", target_year=2035)
    
    print("\n --- THE BUTTERFLY ENGINE PREDICTION RUN (Year: 2035) --- ")
    for metric, calculation in results.items():
        print(f" {metric.replace('_', ' ')}: {calculation}")