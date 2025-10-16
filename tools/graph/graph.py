class Node:
    def __init__(self, value):
        self.value = value
        self.neighbors = []
    
    def add_neighbor(self, neighbor):
        """Add a neighbor to this node"""
        if neighbor not in self.neighbors:
            self.neighbors.append(neighbor)
    
    def remove_neighbor(self, neighbor):
        """Remove a neighbor from this node"""
        if neighbor in self.neighbors:
            self.neighbors.remove(neighbor)
    
    def get_neighbors(self):
        """Return list of neighbors"""
        return self.neighbors
    
    def __str__(self):
        return f"Node({self.value})"
    
    def __repr__(self):
        return self.__str__()


class Graph:
    def __init__(self, directed=False):
        self.nodes = {}
        self.directed = directed
    
    def add_node(self, value):
        """Add a node to the graph"""
        if value not in self.nodes:
            self.nodes[value] = Node(value)
        return self.nodes[value]
    
    def add_edge(self, value1, value2):
        """Add an edge between two nodes"""
        node1 = self.add_node(value1)
        node2 = self.add_node(value2)
        
        node1.add_neighbor(node2)
        if not self.directed:
            node2.add_neighbor(node1)
    
    def remove_edge(self, value1, value2):
        """Remove edge between two nodes"""
        if value1 in self.nodes and value2 in self.nodes:
            node1 = self.nodes[value1]
            node2 = self.nodes[value2]
            
            node1.remove_neighbor(node2)
            if not self.directed:
                node2.remove_neighbor(node1)
    
    def remove_node(self, value):
        """Remove a node and all its edges"""
        if value in self.nodes:
            node_to_remove = self.nodes[value]
            
            # Remove this node from all neighbors' lists
            for neighbor in node_to_remove.neighbors:
                neighbor.remove_neighbor(node_to_remove)
            
            # Remove the node from the graph
            del self.nodes[value]
    
    def get_node(self, value):
        """Get node by value"""
        return self.nodes.get(value)
    
    def get_nodes(self):
        """Return all nodes in the graph"""
        return list(self.nodes.values())
    
    def has_edge(self, value1, value2):
        """Check if there's an edge between two nodes"""
        if value1 in self.nodes and value2 in self.nodes:
            node1 = self.nodes[value1]
            node2 = self.nodes[value2]
            return node2 in node1.neighbors
        return False
    
    def dfs(self, start_value, visited=None):
        """Depth First Search traversal"""
        if start_value not in self.nodes:
            return []
        
        if visited is None:
            visited = set()
        
        start_node = self.nodes[start_value]
        result = [start_node.value]
        visited.add(start_node.value)
        
        for neighbor in start_node.neighbors:
            if neighbor.value not in visited:
                result.extend(self.dfs(neighbor.value, visited))
        
        return result
    
    def bfs(self, start_value):
        """Breadth First Search traversal"""
        if start_value not in self.nodes:
            return []
        
        visited = set()
        queue = [start_value]
        result = []
        
        while queue:
            current_value = queue.pop(0)
            if current_value not in visited:
                visited.add(current_value)
                result.append(current_value)
                current_node = self.nodes[current_value]
                
                for neighbor in current_node.neighbors:
                    if neighbor.value not in visited:
                        queue.append(neighbor.value)
        
        return result
    
    def __str__(self):
        """String representation of the graph"""
        result = []
        for node in self.nodes.values():
            neighbors = [neighbor.value for neighbor in node.neighbors]
            result.append(f"{node.value}: {neighbors}")
        return "\n".join(result)


# Example usage
if __name__ == "__main__":
    # Create an undirected graph
    graph = Graph()
    
    # Add nodes and edges
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "E")
    graph.add_edge("D", "E")
    
    print("Graph structure:")
    print(graph)
    print("\nDFS traversal from A:", graph.dfs("A"))
    print("BFS traversal from A:", graph.bfs("A"))
    
    # Create a directed graph
    directed_graph = Graph(directed=True)
    directed_graph.add_edge("A", "B")
    directed_graph.add_edge("A", "C")
    directed_graph.add_edge("B", "D")
    
    print("\nDirected graph:")
    print(directed_graph)