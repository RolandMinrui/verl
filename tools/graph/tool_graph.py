from __future__ import annotations
from collections import deque
from copy import deepcopy
import re
import random
import numpy as np
from tqdm import tqdm
from tools.graph.utils import EmbeddingClient

class ToolNode:
    def __init__(self, name: str, description: str, parameters: dict):
        self.name = name
        self.description = description
        self.parameters = parameters
        self._parse_description()

        self.neighbors = [] # store both relate_to and depend_on edges
        self.relate_to_neighbors = []
        self.depend_on_neighbors = []
    
    def add_neighbor(self, neighbor: ToolNode, neighbor_type: str) -> None:
        '''
        Add a given neighbor to this node.
        If given neighbor already exists, we need to check the type of existing edge.
        The depend_on edge will overwrite the relate_to edge.
        '''
        assert neighbor_type in ["relate_to", "depend_on"], "neighbor_type must be either 'relate_to' or 'depend_on'"
        
        if neighbor in self.neighbors:
            if neighbor in self.relate_to_neighbors:
                self.relate_to_neighbors.remove(neighbor)
            if neighbor in self.depend_on_neighbors:
                self.depend_on_neighbors.remove(neighbor)
            self.neighbors.remove(neighbor)
        
        if neighbor_type == "relate_to":
            self.relate_to_neighbors.append(neighbor)
        else:
            self.depend_on_neighbors.append(neighbor)
        self.neighbors.append(neighbor)

    def _parse_description(self) -> None:
        '''
        Split the description into description, argument, and return.
        '''
        pattern = r'(.*?)(?:\s*Args:\s*(.*?))?(?:\s*Returns:\s*(.*))?$'
        match = re.search(pattern, self.description.strip(), re.DOTALL)
        
        self.description = match.group(1).strip().replace("\n", "") if match.group(1) else "None"
        self.arguments = match.group(2).strip().replace("\n", "") if match.group(2) else "None"
        self.returns = match.group(3).strip().replace("\n", "") if match.group(3) else "None"
    
    def generate_embedding(self, embedding_model: EmbeddingClient) -> None:
        self.embedding = {
            "description": embedding_model.encode(self.description),
            "arguments": embedding_model.encode(self.arguments),
            "returns": embedding_model.encode(self.returns),
        }

class ToolGraph:
    def __init__(self, embedding_model: EmbeddingClient, threshold: float = 0.75):
        self.nodes = {}
        self.embedding_model = embedding_model
        self.threshold = threshold

    def print_graph_stats(self):
        """Print statistics about the graph"""
        total_relate_to = 0
        total_depend_on = 0
        total_neighbors = 0
        
        for node in self.nodes.values():
            total_relate_to += len(node.relate_to_neighbors)
            total_depend_on += len(node.depend_on_neighbors)
            total_neighbors += len(node.neighbors)
        
        print(f"Graph Statistics:")
        print(f"  Total nodes: {len(self.nodes)}")
        print(f"  Total relate_to edges: {total_relate_to // 2}")
        print(f"  Total depend_on edges: {total_depend_on // 2}")
        print(f"  Total all edges: {total_neighbors // 2}")

    def build_tool_graph(self, tools: dict):
        # Create nodes
        for tool_name, tool_schema in tqdm(tools.items(), desc="Creating tool nodes"):
            if "load_scenario" in tool_name or "save_scenario" in tool_name:
                continue
            node = ToolNode(
                tool_name, 
                tool_schema['function']['description'],
                tool_schema['function']['parameters'], 
            )
            # node.generate_embedding(self.embedding_model)
            self.nodes[tool_name] = node

        # Prepare data for batch embedding computation
        node_names = list(self.nodes.keys())
        descriptions = []
        arguments = []
        returns = []
        
        for node_name in node_names:
            node = self.nodes[node_name]
            descriptions.append(node.description)
            arguments.append(node.arguments)
            returns.append(node.returns)
        
        # Compute embeddings in batch
        desc_embeddings = self.embedding_model.encode(descriptions)
        arg_embeddings = self.embedding_model.encode(arguments)
        ret_embeddings = self.embedding_model.encode(returns)

        # Compute similarity matrices
        desc_similarities = self.embedding_model.similarity(desc_embeddings, desc_embeddings)
        arg_similarities = self.embedding_model.similarity(arg_embeddings, arg_embeddings)
        cross_arg_ret_similarities = self.embedding_model.similarity(arg_embeddings, ret_embeddings)

        # Build edges
        self._build_relate_to_edges(node_names, desc_similarities, arg_similarities)
        self._build_depend_on_edges(node_names, cross_arg_ret_similarities)
        
        self.print_graph_stats()

    def _build_relate_to_edges(self, node_names: list, desc_similarities, arg_similarities):
        """Build relate_to edges based on tool similarity"""
        n = len(node_names)    
        for i in range(n):
            node_i = self.nodes[node_names[i]]
            
            for j in range(i+1, n):
                desc_sim, arg_sim = desc_similarities[i][j], arg_similarities[i][j]
                weighted_sim = 0.7 * desc_sim + 0.3 * arg_sim
                
                if weighted_sim > self.threshold:
                    node_j = self.nodes[node_names[j]]
                    node_i.add_neighbor(node_j, "relate_to")
                    node_j.add_neighbor(node_i, "relate_to") # relate_to edge is two-way

    def _build_depend_on_edges(self, node_names: list, cross_arg_ret_similarities):
        """Build depend_on edges based on argument-return compatibility"""
        n = len(node_names)
        
        for i in range(n):  # argument
            node_i = self.nodes[node_names[i]]
            
            for j in range(n):  # return
                if i == j:  
                    continue
                
                node_j = self.nodes[node_names[j]]
                if cross_arg_ret_similarities[i][j] > self.threshold:
                    node_i.add_neighbor(node_j, "depend_on")

    def sample_subgraph(self, sampler, max_nodes: int = 10, start_node: str = None) -> ToolGraph:
        '''
        Randomly sample a starting node and perform BFS to sample a subgraph.
        
        Args:
            max_nodes: Maximum number of nodes in the sampled subgraph
            start_node: Optional starting node name. If None, a random node is selected.
            sampler: Sampler instance to use for neighbor sampling. If None, uses RandomSampler(p=0.5)
            
        Returns:
            A new ToolGraph containing the sampled subgraph
        '''
        if not self.nodes:
            raise ValueError("The graph is empty. Cannot sample subgraph.")
        
        # Select a starting node
        if start_node is None or start_node not in self.nodes:
            start_node = random.choice(list(self.nodes.keys()))

        # Perform BFS to sample nodes
        visited = set()
        queue = deque([start_node])
        
        while queue and len(visited) < max_nodes:
            current_node_name = queue.popleft()
            if current_node_name in visited:
                continue
                
            visited.add(current_node_name)
            current_node = self.nodes[current_node_name]
            
            # Sample neighbors using sampler
            sampled_neighbors = sampler.sample(current_node)
            for neighbor in sampled_neighbors:
                if neighbor.name not in visited and len(visited) < max_nodes:
                    queue.append(neighbor.name)

        # Create new subgraph
        subgraph = ToolGraph(
            embedding_model=self.embedding_model,
            threshold=self.threshold,
        )

        # Add sampled nodes to subgraph
        for node_name in visited:
            original_node = self.nodes[node_name]
            new_node = ToolNode(
                original_node.name,
                original_node.description,
                original_node.parameters
            )
            subgraph.nodes[node_name] = new_node
        
        # Reconstruct edges between sampled nodes
        for node_name in visited:
            new_node = subgraph.nodes[node_name]
            original_node = self.nodes[node_name]
            
            # Only add edges to neighbors that are in the sampled subgraph
            for neighbor in original_node.neighbors:
                if neighbor.name in visited:
                    if neighbor in original_node.relate_to_neighbors:
                        edge_type = "relate_to"
                    else:
                        edge_type = "depend_on"
                    
                    neighbor_in_subgraph = subgraph.nodes[neighbor.name]
                    new_node.add_neighbor(neighbor_in_subgraph, edge_type)
        
        return subgraph