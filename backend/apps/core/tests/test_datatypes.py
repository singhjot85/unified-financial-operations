import pytest

from apps.core.datatypes import CycleError, DirectedGraph, Graph, Queue


class TestQueueDataType:

    def setup_method(self):
        self.queue_obj = Queue()

    @property
    def queue(self):
        return self.queue_obj.queue

    def test_enqueue(self):
        # First Enqueue, start and end index should be 0
        start, end = self.queue_obj.enqueue(10)
        assert len(self.queue) == 1
        assert start == 0
        assert end == 0

        # Second Enqueue, start and end index should be 0 and 1 respectively
        start, end = self.queue_obj.enqueue(20)
        assert len(self.queue) == 2
        assert start == 0
        assert end == 1

        # Third Enqueue, start and end index should be 0 and 2 respectively
        start, end = self.queue_obj.enqueue(30)
        assert len(self.queue) == 3
        assert start == 0
        assert end == 2

    def test_dequeue(self):
        self.queue_obj.enqueue(10)
        self.queue_obj.enqueue(20)
        self.queue_obj.enqueue(30)

        # Initially, queue should have 3 elements
        assert len(self.queue) == 3

        # Dequeue first element, queue should have 2 elements and start index should be 1
        assert self.queue_obj.dequeue() == 10
        assert len(self.queue) == 2
        start, end = self.queue_obj.indices
        assert start == 1
        assert end == 2

        # Dequeue second element, queue should have 1 element and start index should be 2
        assert self.queue_obj.dequeue() == 20
        assert len(self.queue) == 1
        start, end = self.queue_obj.indices
        assert start == 2
        assert end == 2

        # Dequeue third element, queue should be empty and start and end index should be 0
        assert self.queue_obj.dequeue() == 30
        assert len(self.queue) == 0
        start, end = self.queue_obj.indices
        assert start == 0
        assert end == 0

    def test_peep(self):
        # Peep empty queue
        assert self.queue_obj.peep() is None

        # Peep queue with elements
        self.queue_obj.enqueue(10)
        self.queue_obj.enqueue(20)
        assert self.queue_obj.peep() == 10

        # Peep after a dequeue (verifies the fix to the index error)
        self.queue_obj.dequeue()
        assert self.queue_obj.peep() == 20

        # Peep after dequeuing all
        self.queue_obj.dequeue()
        assert self.queue_obj.peep() is None


class TestGraphDataType:

    def test_graph_initialization(self):
        # Test directed graph
        g_directed = Graph(directed=True)
        assert g_directed.total_nodes == 0
        assert g_directed.adjacency_list == {}

        # Test undirected graph
        g_undirected = Graph(directed=False)
        assert g_undirected.total_nodes == 0
        assert g_undirected.adjacency_list == {}

    def test_add_node_directed(self):
        g = Graph(directed=True)
        g.add_node(0, 1)
        g.add_node(0, 2)

        adj = g.adjacency_list
        assert adj[0] == [1, 2]
        assert adj[1] == []
        assert adj[2] == []
        assert g.total_nodes == 3

    def test_add_node_undirected(self):
        g = Graph(directed=False)
        g.add_node(0, 1)

        adj = g.adjacency_list
        assert adj[0] == [1]
        assert adj[1] == [0]
        assert g.total_nodes == 2

    def test_remove_node(self):
        g = Graph(directed=True)
        g.add_node(0, 1)
        g.add_node(1, 2)
        g.add_node(0, 2)

        assert g.total_nodes == 3

        g.remove_node(1)

        adj = g.adjacency_list
        # Node 1 should be gone from the keys
        assert 1 not in adj
        # Node 1 should be removed from other nodes' neighbor lists
        assert adj[0] == [2]
        assert adj[2] == []
        assert g.total_nodes == 2


class TestDirectedGraphDataType:

    def test_get_in_degree(self):
        g = DirectedGraph()
        g.add_node(0, 1)
        g.add_node(0, 2)
        g.add_node(1, 3)
        g.add_node(2, 3)

        # in-degrees: 0:0, 1:1, 2:1, 3:2
        indegree = g.get_in_degree()
        assert indegree == {0: 0, 1: 1, 2: 1, 3: 2}

    def test_get_in_degree_non_contiguous(self):
        # Graph with arbitrary indices, no total_nodes specified
        g = DirectedGraph()
        g.add_node(10, 20)
        g.add_node(20, 30)
        g.add_node(10, 30)

        indegree = g.get_in_degree()
        assert indegree == {10: 0, 20: 1, 30: 2}

    def test_bfs_topological_sort_valid(self):
        g = DirectedGraph()
        g.add_node(0, 1)
        g.add_node(0, 2)
        g.add_node(1, 3)
        g.add_node(2, 3)

        topo = g.bfs_topological_sort()
        # Valid topological sort orders for this graph are:
        # [0, 1, 2, 3] or [0, 2, 1, 3]
        assert topo == [0, 1, 2, 3] or topo == [0, 2, 1, 3]

    def test_bfs_topological_sort_non_contiguous(self):
        g = DirectedGraph()
        g.add_node(10, 20)
        g.add_node(10, 30)
        g.add_node(20, 30)

        topo = g.bfs_topological_sort()
        assert topo == [10, 20, 30]

    def test_bfs_topological_sort_empty(self):
        g = DirectedGraph()
        assert g.bfs_topological_sort() == []

    def test_bfs_topological_sort_disconnected(self):
        g = DirectedGraph()
        g.add_node(0, 1)
        g.add_node(2, 3)

        topo = g.bfs_topological_sort()
        # There are multiple valid orderings, let's verify it contains all unique nodes and satisfies order
        assert len(topo) == 4
        assert set(topo) == {0, 1, 2, 3}
        # In a valid topo sort: 0 must come before 1, and 2 must come before 3
        assert topo.index(0) < topo.index(1)
        assert topo.index(2) < topo.index(3)

    def test_bfs_topological_sort_circular_dependency(self):
        # Self-loop cycle
        g_self_loop = DirectedGraph()
        g_self_loop.add_node(0, 0)
        with pytest.raises(CycleError):
            g_self_loop.bfs_topological_sort()

        # Simple 2-node cycle
        g_cycle_2 = DirectedGraph()
        g_cycle_2.add_node(0, 1)
        g_cycle_2.add_node(1, 0)
        with pytest.raises(CycleError):
            g_cycle_2.bfs_topological_sort()

        # Complex cycle where part of the graph is acyclic
        g_partial_cycle = DirectedGraph()
        g_partial_cycle.add_node(0, 1)
        g_partial_cycle.add_node(1, 2)
        g_partial_cycle.add_node(2, 1)  # Cycle: 1 <-> 2
        with pytest.raises(CycleError):
            g_partial_cycle.bfs_topological_sort()
