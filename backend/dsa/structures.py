"""
Data Structures & Algorithms (DSA) Core - Fundamental Abstract Data Types.

Pure Python implementations created from scratch for academic evaluation:
1. MinHeap: Array-based binary min-heap for priority queue operations.
2. FIFOQueue: Pointer-based linked list queue for O(1) breadth-first search.
3. LIFOStack: Pointer-based linked list stack for O(1) depth-first search.

No standard library queue/heap modules (heapq, queue, collections.deque) are used.
"""

from typing import Any, Dict, List, Optional, Tuple


class MinHeap:
    """
    Array-backed Binary Minimum Heap (Priority Queue).

    Maintains the min-heap invariant where every parent node has a key less than
    or equal to its children. Uses an internal monotonic counter for FIFO stability
    and to prevent arbitrary item comparison crashes when priorities are identical.

    Time Complexity:
        - push: O(log N)
        - pop:  O(log N)
        - peek: O(1)
        - is_empty: O(1)
        - len:  O(1)
    Space Complexity:
        - O(N) where N is the number of active entries.
    """

    def __init__(self) -> None:
        """Initialize an empty binary min-heap."""
        # Entries stored as tuples: (priority, counter, item)
        self._heap: List[Tuple[float, int, Any]] = []
        self._counter: int = 0

    def push(self, priority: float, item: Any, tie_breaker: Any = None) -> None:
        """
        Insert an item with an associated priority into the min-heap.

        Args:
            priority: Numerical priority (lower value = higher priority).
            item: Arbitrary data payload associated with this priority.
            tie_breaker: Optional explicit secondary sort key.
        """
        self._counter += 1
        # Store as (priority, secondary_key, counter, item) if tie_breaker provided,
        # otherwise (priority, counter, item).
        if tie_breaker is not None:
            entry = (float(priority), tie_breaker, self._counter, item)
        else:
            entry = (float(priority), self._counter, item)

        self._heap.append(entry)
        self._sift_up(len(self._heap) - 1)

    def pop(self) -> Tuple[float, Any]:
        """
        Remove and return the item with the minimum priority.

        Returns:
            Tuple of (priority, item).

        Raises:
            IndexError: If the heap is empty.
        """
        if self.is_empty():
            raise IndexError("pop from an empty MinHeap")

        min_entry = self._heap[0]
        last_entry = self._heap.pop()

        if self._heap:
            self._heap[0] = last_entry
            self._sift_down(0)

        priority = min_entry[0]
        item = min_entry[-1]
        return (priority, item)

    def peek(self) -> Tuple[float, Any]:
        """
        Return the item with the minimum priority without removing it.

        Returns:
            Tuple of (priority, item).

        Raises:
            IndexError: If the heap is empty.
        """
        if self.is_empty():
            raise IndexError("peek from an empty MinHeap")

        min_entry = self._heap[0]
        return (min_entry[0], min_entry[-1])

    def is_empty(self) -> bool:
        """Check if the min-heap contains zero elements."""
        return len(self._heap) == 0

    def __len__(self) -> int:
        """Return the number of elements in the min-heap."""
        return len(self._heap)

    def to_list(self) -> List[Dict[str, Any]]:
        """
        Return a sorted snapshot of the current heap contents for frontend visualization.
        Does not mutate the underlying heap structure.

        Returns:
            List of dicts: [{'priority': round(p, 2), 'item': item}, ...]
        """
        # Shallow copy and sort by tuple comparator
        sorted_entries = sorted(self._heap, key=lambda e: (e[0], e[1] if len(e) == 4 else e[1]))
        return [
            {"priority": round(e[0], 2), "item": e[-1]}
            for e in sorted_entries
        ]

    # --- Internal Binary Heap Navigation and Sifting ---

    def _sift_up(self, idx: int) -> None:
        """Restore min-heap invariant by floating element up towards the root."""
        while idx > 0:
            parent_idx = (idx - 1) // 2
            if self._heap[idx] < self._heap[parent_idx]:
                self._heap[idx], self._heap[parent_idx] = self._heap[parent_idx], self._heap[idx]
                idx = parent_idx
            else:
                break

    def _sift_down(self, idx: int) -> None:
        """Restore min-heap invariant by sinking element down towards the leaves."""
        size = len(self._heap)
        while True:
            smallest = idx
            left_child = 2 * idx + 1
            right_child = 2 * idx + 2

            if left_child < size and self._heap[left_child] < self._heap[smallest]:
                smallest = left_child

            if right_child < size and self._heap[right_child] < self._heap[smallest]:
                smallest = right_child

            if smallest != idx:
                self._heap[idx], self._heap[smallest] = self._heap[smallest], self._heap[idx]
                idx = smallest
            else:
                break


class _QueueNode:
    """Internal singly linked list node for FIFOQueue."""

    __slots__ = ("value", "next")

    def __init__(self, value: Any, next_node: Optional["_QueueNode"] = None) -> None:
        self.value: Any = value
        self.next: Optional["_QueueNode"] = next_node


class FIFOQueue:
    """
    Pointer-based First-In-First-Out (FIFO) Queue.

    Implemented using singly linked list nodes with head and tail pointers
    guaranteeing strictly O(1) worst-case time for enqueue and dequeue.

    Time Complexity:
        - enqueue: O(1)
        - dequeue: O(1)
        - peek:    O(1)
        - is_empty: O(1)
        - len:     O(1)
    Space Complexity:
        - O(N) where N is the number of active queue elements.
    """

    def __init__(self) -> None:
        """Initialize an empty FIFO queue."""
        self._head: Optional[_QueueNode] = None
        self._tail: Optional[_QueueNode] = None
        self._size: int = 0

    def enqueue(self, item: Any) -> None:
        """
        Append an item to the end (tail) of the queue.

        Args:
            item: Item to insert.
        """
        new_node = _QueueNode(item)
        if self._tail is None:
            self._head = new_node
            self._tail = new_node
        else:
            self._tail.next = new_node
            self._tail = new_node
        self._size += 1

    def dequeue(self) -> Any:
        """
        Remove and return the item at the front (head) of the queue.

        Returns:
            Item at the head of the queue.

        Raises:
            IndexError: If the queue is empty.
        """
        if self.is_empty():
            raise IndexError("dequeue from an empty FIFOQueue")

        assert self._head is not None
        value = self._head.value
        self._head = self._head.next
        if self._head is None:
            self._tail = None
        self._size -= 1
        return value

    def peek(self) -> Any:
        """
        Return the item at the front (head) of the queue without removing it.

        Returns:
            Item at the head of the queue.

        Raises:
            IndexError: If the queue is empty.
        """
        if self.is_empty():
            raise IndexError("peek from an empty FIFOQueue")
        assert self._head is not None
        return self._head.value

    def is_empty(self) -> bool:
        """Return True if queue is empty, False otherwise."""
        return self._size == 0

    def __len__(self) -> int:
        """Return number of elements currently stored in the queue."""
        return self._size

    def to_list(self) -> List[Any]:
        """
        Return an ordered snapshot list of elements from head to tail.

        Returns:
            List of items currently in the queue.
        """
        result: List[Any] = []
        curr = self._head
        while curr is not None:
            result.append(curr.value)
            curr = curr.next
        return result


class _StackNode:
    """Internal singly linked list node for LIFOStack."""

    __slots__ = ("value", "next")

    def __init__(self, value: Any, next_node: Optional["_StackNode"] = None) -> None:
        self.value: Any = value
        self.next: Optional["_StackNode"] = next_node


class LIFOStack:
    """
    Pointer-based Last-In-First-Out (LIFO) Stack.

    Implemented using singly linked list nodes with a top pointer guaranteeing
    strictly O(1) worst-case time for push and pop operations.

    Time Complexity:
        - push:     O(1)
        - pop:      O(1)
        - peek:     O(1)
        - is_empty: O(1)
        - len:      O(1)
    Space Complexity:
        - O(N) where N is the number of active stack elements.
    """

    def __init__(self) -> None:
        """Initialize an empty LIFO stack."""
        self._top: Optional[_StackNode] = None
        self._size: int = 0

    def push(self, item: Any) -> None:
        """
        Push an item onto the top of the stack.

        Args:
            item: Item to place on stack.
        """
        self._top = _StackNode(item, self._top)
        self._size += 1

    def pop(self) -> Any:
        """
        Remove and return the item at the top of the stack.

        Returns:
            Item from the top of the stack.

        Raises:
            IndexError: If the stack is empty.
        """
        if self.is_empty():
            raise IndexError("pop from an empty LIFOStack")

        assert self._top is not None
        value = self._top.value
        self._top = self._top.next
        self._size -= 1
        return value

    def peek(self) -> Any:
        """
        Return the item at the top of the stack without removing it.

        Returns:
            Item at the top of the stack.

        Raises:
            IndexError: If the stack is empty.
        """
        if self.is_empty():
            raise IndexError("peek from an empty LIFOStack")

        assert self._top is not None
        return self._top.value

    def is_empty(self) -> bool:
        """Return True if stack is empty, False otherwise."""
        return self._size == 0

    def __len__(self) -> int:
        """Return number of elements currently on the stack."""
        return self._size

    def to_list(self) -> List[Any]:
        """
        Return an ordered snapshot list of elements from top to bottom.

        Returns:
            List of items currently in the stack.
        """
        result: List[Any] = []
        curr = self._top
        while curr is not None:
            result.append(curr.value)
            curr = curr.next
        return result
