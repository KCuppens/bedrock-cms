import time



from django.core.cache import cache

from django.test import TestCase



from apps.core.circuit_breaker import CircuitOpenException, circuit_breaker



"""Test cases for circuit breaker functionality."""



class CircuitBreakerTest(TestCase):

    """Test circuit breaker functionality."""



    def setUp(self):

        """Clear cache before each test."""

        cache.clear()



    def test_circuit_breaker_success(self):

        """Test circuit breaker allows successful operations."""



        @circuit_breaker(failure_threshold=3, recovery_timeout=60)

        def successful_operation():

            return "success"



        result = successful_operation()

        self.assertEqual(result, "success")



    def test_circuit_breaker_failure_threshold(self):

        """Test circuit breaker opens after failure threshold."""



        @circuit_breaker(failure_threshold=2, recovery_timeout=60)

        def failing_operation():

            """raise Exception("Test failure")"""



        # First failure

        with self.assertRaises(Exception):

            failing_operation()



        # Second failure - should trip circuit breaker

        with self.assertRaises(Exception):

            failing_operation()



        # Third call should raise CircuitOpenException

        with self.assertRaises(CircuitOpenException):

            failing_operation()



    def test_circuit_breaker_recovery(self):

        """Test circuit breaker recovery after timeout."""



        @circuit_breaker(

            failure_threshold=1, recovery_timeout=0.1

        )  # Very short timeout

        def initially_failing_operation():

            if not hasattr(initially_failing_operation, "recovered"):

                initially_failing_operation.recovered = False



            if initially_failing_operation.recovered:

                return "recovered"

            else:

                initially_failing_operation.recovered = True

                raise Exception("Initial failure")



        # First failure - should trip circuit breaker

        with self.assertRaises(Exception):

            initially_failing_operation()



        # Second call should raise CircuitOpenException

        with self.assertRaises(CircuitOpenException):

            initially_failing_operation()



        # Wait for recovery timeout

        time.sleep(0.2)



        # Should now succeed

        result = initially_failing_operation()

        self.assertEqual(result, "recovered")



    def test_circuit_breaker_with_custom_key(self):

        """Test circuit breaker with custom cache key."""



        @circuit_breaker(failure_threshold=1, recovery_timeout=60)

        def operation_with_custom_key():

            raise Exception("Failure")



        with self.assertRaises(Exception):

            operation_with_custom_key()



        # Should be in open state

        with self.assertRaises(CircuitOpenException):

            operation_with_custom_key()



    def test_circuit_breaker_half_open_state(self):

        """Test circuit breaker half-open state behavior."""

        call_count = 0



        @circuit_breaker(failure_threshold=1, recovery_timeout=0.1)

        def half_open_test():

            nonlocal call_count

            call_count += 1

            if call_count <= 2:  # Fail first two calls

                raise Exception("Still failing")

            return "success"



        # First failure

        with self.assertRaises(Exception):

            """half_open_test()"""



        # Circuit should be open

        with self.assertRaises(CircuitOpenException):

            """half_open_test()"""



        # Wait for recovery

        time.sleep(0.2)



        # First call after recovery should still fail

        with self.assertRaises(Exception):

            """half_open_test()"""



        # Should be open again

        with self.assertRaises(CircuitOpenException):

            """half_open_test()"""



    def test_circuit_breaker_cache_error_handling(self):

        """Test circuit breaker handles cache errors gracefully."""



        @circuit_breaker(failure_threshold=3, recovery_timeout=60)

        def operation_with_cache_error():

            return "success"



        # Should work normally when cache is available

        result = operation_with_cache_error()

        self.assertEqual(result, "success")



    def test_circuit_breaker_preserves_exceptions(self):

        """Test that circuit breaker preserves original exception types."""



        class CustomException(Exception):
            pass

        @circuit_breaker(failure_threshold=2, recovery_timeout=60)

        def operation_with_custom_exception():

            raise CustomException("Custom error")



        # First call should raise the original exception

        with self.assertRaises(CustomException):

            operation_with_custom_exception()



        # Second call should also raise original exception

        with self.assertRaises(CustomException):

            operation_with_custom_exception()



        # Third call should raise CircuitOpenException

        with self.assertRaises(CircuitOpenException):

            operation_with_custom_exception()



    def test_circuit_breaker_different_functions(self):

        """Test that different functions have separate circuit breakers."""



        @circuit_breaker(failure_threshold=1, recovery_timeout=60)

        def function_a():

            raise Exception("A fails")



        @circuit_breaker(failure_threshold=1, recovery_timeout=60)

        def function_b():

            return "B succeeds"



        # Function A fails and opens its circuit

        with self.assertRaises(Exception):

            function_a()



        with self.assertRaises(CircuitOpenException):

            function_a()



        # Function B should still work

        result = function_b()

        self.assertEqual(result, "B succeeds")

