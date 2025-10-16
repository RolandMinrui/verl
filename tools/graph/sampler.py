from abc import ABC, abstractmethod
import random

from tools.graph.tool_graph import ToolNode

class Sampler(ABC):
    @abstractmethod
    def sample(self, node: ToolNode):
        pass


class RandomSampler(Sampler):
    """Random sampler that samples each neighbor with probability p."""
    def __init__(self, p: float = 0.5):
        self.p = p
    
    def sample(self, node: ToolNode) -> list:
        """Sample each neighbors of a node with probability p."""
        sampled_neighbors = []
        for neighbor in node.neighbors:
            if random.random() < self.p:
                sampled_neighbors.append(neighbor)
        return sampled_neighbors


class RandomWalkSampler(Sampler):
    """Random walk sampler that samples exactly one random neighbor from the given node."""
    def sample(self, node: ToolNode):
        return random.choice(node.neighbors)