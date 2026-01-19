import unittest
from src.domain.models import VectorClock, generate_node_id

class TestVectorClock(unittest.TestCase):
    def test_node_id_generation(self):
        id1 = generate_node_id()
        id2 = generate_node_id()
        self.assertIsInstance(id1, str)
        self.assertNotEqual(id1, id2)
        # simplistic check for UUID format (length is 36)
        self.assertEqual(len(id1), 36)

    def test_increment_and_merge(self):
        node_a = generate_node_id() 
        node_b = generate_node_id()
        
        vc1 = VectorClock()
        vc1.increment(node_a)
        self.assertEqual(vc1.timestamps, {node_a: 1})
        
        vc2 = VectorClock()
        vc2.increment(node_b)
        self.assertEqual(vc2.timestamps, {node_b: 1})
        
        vc1.merge(vc2)
        self.assertEqual(vc1.timestamps, {node_a: 1, node_b: 1})
        
        # Test dynamic update (new key)
        vc3 = VectorClock()
        node_c = generate_node_id()
        vc3.timestamps = {node_c: 5, node_a: 2}
        vc1.merge(vc3)
        self.assertEqual(vc1.timestamps, {node_a: 2, node_b: 1, node_c: 5})

    def test_dynamic_client_discovery(self):
        """
        Verify that a client automatically 'learns' about new clients 
        when it receives a VectorClock containing new IDs.
        """
        local_id = generate_node_id()
        remote_id = generate_node_id()
        new_client_id = generate_node_id()

        local_vc = VectorClock()
        local_vc.timestamps = {local_id: 2, remote_id: 3}

        # Message arrives from 'remote_id', but they have seen 'new_client_id'
        incoming_vc = VectorClock()
        incoming_vc.timestamps = {local_id: 2, remote_id: 4, new_client_id: 1}

        # Merge should update remote_id AND add new_client_id
        local_vc.merge(incoming_vc)
        
        self.assertEqual(local_vc.timestamps[remote_id], 4)
        self.assertEqual(local_vc.timestamps[new_client_id], 1)
        self.assertEqual(len(local_vc.timestamps), 3)

    def test_compare(self):
        node_a = generate_node_id()
        node_b = generate_node_id()
        
        vc1 = VectorClock() 
        vc1.timestamps = {node_a: 1, node_b: 1}
        
        vc2 = VectorClock()
        vc2.timestamps = {node_a: 2, node_b: 1}
        
        # vc1 < vc2
        self.assertEqual(vc1.compare(vc2), -1)
        self.assertEqual(vc2.compare(vc1), 1)
        
        # Concurrent
        vc3 = VectorClock()
        vc3.timestamps = {node_a: 1, node_b: 2}
        
        # vc2 (A:2, B:1) vs vc3 (A:1, B:2) -> Concurrent
        self.assertEqual(vc2.compare(vc3), 0)
        
        # Equal
        vc4 = VectorClock()
        vc4.timestamps = {node_a: 1, node_b: 1}
        self.assertEqual(vc1.compare(vc4), 0)

    def test_is_causally_ready(self):
        node_a = generate_node_id()
        node_b = generate_node_id()
        node_c = generate_node_id()
        
        # Local state: A:1, B:1
        local_vc = VectorClock()
        local_vc.timestamps = {node_a: 1, node_b: 1}
        
        # Test 1: Correct next message from A (A:2, B:1)
        msg_vc_1 = VectorClock()
        msg_vc_1.timestamps = {node_a: 2, node_b: 1}
        self.assertTrue(local_vc.is_causally_ready(msg_vc_1, node_a))
        
        # Test 2: Gap in A (A:3, B:1) -> Not ready
        msg_vc_2 = VectorClock()
        msg_vc_2.timestamps = {node_a: 3, node_b: 1}
        self.assertFalse(local_vc.is_causally_ready(msg_vc_2, node_a))
        
        # Test 3: Missing dependency from B (A:2, B:2) -> We only have B:1
        msg_vc_3 = VectorClock()
        msg_vc_3.timestamps = {node_a: 2, node_b: 2}
        self.assertFalse(local_vc.is_causally_ready(msg_vc_3, node_a))
        
        # Test 4: New client C involved
        # Message says: "I (A) have seen C:1". Local says: "I know nothing of C".
        # If A depends on C:1, we must see C:1 first.
        msg_vc_4 = VectorClock()
        msg_vc_4.timestamps = {node_a: 2, node_b: 1, node_c: 1}
        self.assertFalse(local_vc.is_causally_ready(msg_vc_4, node_a))
        
        # If the message IS from C
        msg_vc_5 = VectorClock()
        msg_vc_5.timestamps = {node_a: 1, node_b: 1, node_c: 1}
        self.assertTrue(local_vc.is_causally_ready(msg_vc_5, node_c))

if __name__ == '__main__':
    unittest.main()
