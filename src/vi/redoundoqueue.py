from collections import deque


class RedoUndoQueue:
    """
    Implements a simple queue which handles undo and redo functions
    """
    def __init__(self, history=5):
        self.q = deque()
        self.q.append(None)

    def enqueue(self, region_name):
        """
        Append a new element to the queue, deletes old elements
        Args:
            region_name:

        Returns:

        """
        while self.q[0]:
            self.q.popleft()
        self.q.append(region_name)

    def pop(self):
        result = self.q.pop()
        return result

    def undo(self):
        """
        Undo
        Returns:

        """
        if len(self.q):
            if self.q[-1]:
                self.q.rotate(1)
            res = self.q[-1]
            if res:
                return res
            else:
                return self.q[0]
            return res
        else:
            return None

    def redo(self):
        """

        Returns:

        """
        if len(self.q):
            if self.q[-1] is None:
                self.q.rotate(-1)
                return self.q[0]
            res = self.q[0]
            if res:
                self.q.rotate(-1)
                return res
            else:
                return self.q[-1]
        else:
            return None

    def __str__(self):
        return self.q.__str__()

