from apps.core.datatypes import Queue


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
