import typing

QUEUE: typing.TypeAlias = list[typing.Any]


class Queue:
    _start_index: int
    _end_index: int
    _queue: QUEUE

    def __init__(self):
        self.clean_queue()  # Start with clean queue always

    def clean_queue(self):
        """
        Currently to prevent cpu cycle's we are keeping the ``_queue`` attribute as-is,
        but when both the indice's meet, i.e. end of traversal we can clean it to free the space
        """
        self._queue = []
        self._start_index = 0
        self._end_index = 0

    @property
    def indices(self):
        return self._start_index, self._end_index

    @property
    def queue(self):
        """
        Returns the active elements in the queue.
        """
        if not self._queue:
            return []
        if self._start_index > self._end_index:
            self.clean_queue()
            return []
        return self._queue[self._start_index : self._end_index + 1]

    def peep(self) -> typing.Optional[typing.Any]:
        if not self.queue:
            return None

        return self._queue[self._start_index]

    def enqueue(self, value: typing.Any) -> tuple[int, int]:
        """
        Enque an element to queue,
        Internally increase the end_index

        Args:
            value (Any): Value to put in queue

        Returns:
            (int, int): start and end index of the queue
        """
        is_empty = len(self.queue) == 0
        self._queue.append(value)
        if is_empty:
            self._start_index = 0
            self._end_index = 0
        else:
            self._end_index += 1
        return self.indices

    def dequeue(self) -> typing.Optional[typing.Any]:
        """Pop the first element of the queue,
        Internally move's the start pointer one step ahead,

        Returns:
            (Any, optional): First element of the queue
        """
        active_q = self.queue
        if not active_q:
            self.clean_queue()
            return None

        return_value = self._queue[self._start_index]
        if len(active_q) == 1:
            self.clean_queue()
        else:
            self._start_index += 1

        return return_value


class CycleError(ValueError):
    """
    Raised when a circular dependency or cycle is detected in a graph.
    """

    pass


class Graph:
    _directed: bool
    _adjanceny_list: dict[int, list]

    def __init__(self, directed: bool = True):
        self._directed = directed
        self._adjanceny_list = {}

    @property
    def total_nodes(self) -> int:
        return len(self.get_all_nodes())

    def get_all_nodes(self) -> set:
        nodes = set(self.adjacency_list.keys())
        for targets in self.adjacency_list.values():
            nodes.update(targets)

        return nodes

    @property
    def adjacency_list(self):
        if not self._adjanceny_list:
            return {}

        return self._adjanceny_list

    def add_node(self, from_index: int, to_index: int) -> None:
        """
        Add a node to the graph, internally adds a
            ``adjaceny_list[from_index] = to_index`` entry for directed
            and vice-versa also for a non-directed graph

        Directed Graph:
            ``(Node A) ---> (Node B)``
        Non-Directional/Bi-directional Graph:
            ``(Node A) <---> (Node B)``
        """
        if from_index not in self._adjanceny_list:
            self._adjanceny_list[from_index] = []
        # Ensure the to_index node also exists in the adjacency list map
        if to_index not in self._adjanceny_list:
            self._adjanceny_list[to_index] = []

        self._adjanceny_list[from_index].append(to_index)
        if not self._directed:
            self._adjanceny_list[to_index].append(from_index)

    def remove_node(self, node_index: int) -> None:
        """
        Remove a node from graph,
        """
        self._adjanceny_list.pop(node_index, None)

        # Traverse the entire _adjanceny_list and remove from every node's mapping
        for key, val in self._adjanceny_list.items():
            new_val = [v for v in val if v != node_index]
            self._adjanceny_list[key] = new_val


class DirectedGraph(Graph):

    def __init__(self):
        super().__init__(directed=True)

    def get_in_degree(self) -> dict[int, int]:
        """
        Get in-degree for each node on graph

        Returns:
            indegree_dict (dict[int, int]): A dictionary where keys are node indices and values are node in-degree values
        """
        nodes = self.get_all_nodes()

        indegree_dict = {node: 0 for node in nodes}

        for targets in self.adjacency_list.values():
            for node in targets:
                if node in indegree_dict:
                    indegree_dict[node] += 1
                else:
                    indegree_dict[node] = 1

        return indegree_dict

    def bfs_topological_sort(self) -> list:
        """
        Topologically Sorted Graph, uses Kahn's Algorithm

        Returns:
            topo_sort (list): Topologically sorted nodes
        """
        topo_sort = []
        if not self.adjacency_list:
            return topo_sort

        indegree = self.get_in_degree()
        queue = Queue()

        def enqueue_zero_indegree():
            for node in list(indegree.keys()):
                indegree_val = indegree[node]
                if isinstance(indegree_val, int) and indegree_val == 0:
                    queue.enqueue(node)
                    indegree[node] = "X"

        enqueue_zero_indegree()  # Start Topo Sort
        while queue.peep() is not None:
            head = queue.dequeue()
            topo_sort.append(head)

            for node in self.adjacency_list.get(head, []):
                if node in indegree and isinstance(indegree[node], int):
                    indegree[node] -= 1

            enqueue_zero_indegree()

        if len(topo_sort) < len(self.get_all_nodes()):
            raise CycleError("Graph contains a cycle / circular dependency")

        return topo_sort
