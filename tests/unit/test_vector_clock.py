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

    def test_merge_enlargement_demo(self):
        print("\n--- Merge Enlargement Demo ---")
        vc_local = VectorClock(timestamps={"NodeA": 1})
        vc_remote = VectorClock(timestamps={"NodeA": 1, "NodeB": 1, "NodeC": 5})
        
        print(f"Before merge: {vc_local.timestamps} (Size: {len(vc_local.timestamps)})")
        vc_local.merge(vc_remote)
        print(f"After merge:  {vc_local.timestamps} (Size: {len(vc_local.timestamps)})")
        
        self.assertEqual(len(vc_local.timestamps), 3)
        print("------------------------------")

    def test_complex_dynamic_join_causality(self):
        """
        Scenario:
        1. Node A and B are active.
        2. Node A sends Msg1 (A:1).
        3. Node B receives Msg1, then sends Msg2 (A:1, B:1).
        4. Node C joins late. 
        5. Node C receives Msg2 (from B) BEFORE receiving Msg1 (from A).
        6. Node C should NOT deliver Msg2 yet because it's missing Msg1.
        """
        node_a = "NodeA"
        node_b = "NodeB"
        node_c = "NodeC"
        
        # Node A sends Msg1
        msg1_vc = VectorClock(timestamps={node_a: 1})
        
        # Node B receives Msg1 and sends Msg2
        node_b_local_vc = VectorClock(timestamps={node_a: 1, node_b: 1})
        msg2_vc = node_b_local_vc.copy() # Msg2 has (A:1, B:1)
        
        # Node C starts fresh (late joiner)
        node_c_local_vc = VectorClock() # Initially {}
        
        # Node C receives Msg2 first
        # Crucial: C doesn't know about A yet, but when it sees msg2_vc, 
        # it sees that A is at 1. C's local A is 0.
        is_ready = node_c_local_vc.is_causally_ready(msg2_vc, node_b)
        
        print("\n--- Complex Dynamic Join Causality ---")
        print(f"Node C local clock: {node_c_local_vc.timestamps}")
        print(f"Incoming Msg2 from B: {msg2_vc.timestamps}")
        print(f"Is Msg2 causally ready at C? {is_ready}")
        
        self.assertFalse(is_ready, "Msg2 should be blocked because Msg1 (A:1) is missing")
        
        # Now Node C receives Msg1 from A
        is_ready_msg1 = node_c_local_vc.is_causally_ready(msg1_vc, node_a)
        print(f"Incoming Msg1 from A: {msg1_vc.timestamps}")
        print(f"Is Msg1 causally ready at C? {is_ready_msg1}")
        
        self.assertTrue(is_ready_msg1, "Msg1 should be deliverable")
        
        # C 'delivers' Msg1 and updates its clock
        node_c_local_vc.merge(msg1_vc)
        print(f"Node C clock after delivering Msg1: {node_c_local_vc.timestamps}")
        
        # Now try Msg2 again
        is_ready_retry = node_c_local_vc.is_causally_ready(msg2_vc, node_b)
        print(f"Retrying Msg2 from B: {msg2_vc.timestamps}")
        print(f"Is Msg2 now causally ready at C? {is_ready_retry}")
        
        self.assertTrue(is_ready_retry, "Msg2 should now be deliverable")
        print("---------------------------------------")

if __name__ == '__main__':
    unittest.main()
