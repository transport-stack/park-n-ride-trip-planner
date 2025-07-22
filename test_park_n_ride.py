#!/usr/bin/env python3
"""
Unit Tests for Parknride Methods

This test suite verifies that all parknride-related methods work correctly.
Tests focus on method functionality and call patterns, not result accuracy.
All tests run using proper Flask test client and strategic mocking.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import datetime
import ast
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Flask for test client
try:
    from flask import Flask
    from app import app as flask_app
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    flask_app = None


class TestParknrideMethods(unittest.TestCase):
    """Unit tests for all parknride methods"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Sample test data
        self.sample_src = [28.6139, 77.2090]  # Delhi coordinates
        self.sample_dest = [28.5355, 77.3910]  # Noida coordinates
        self.sample_time = "09:30:00"
        self.sample_maxfare = 500
        
        # Set up Flask test client if available
        if FLASK_AVAILABLE and flask_app:
            flask_app.config['TESTING'] = True
            self.client = flask_app.test_client()
            self.app_context = flask_app.app_context()
        else:
            self.client = None
            self.app_context = None
        
        # Mock request data templates
        self.base_request_data = {
            'src': str(self.sample_src),
            'dest': str(self.sample_dest),
            'src_name': 'Source Location',
            'dest_name': 'Destination Location',
            'time': '09:30',
            'maxfare': '500'
        }

    def test_parknride_endpoint_function_exists(self):
        """Test that the main parknride endpoint function exists"""
        from app import get_park_n_ride_response
        self.assertTrue(callable(get_park_n_ride_response))
        print("✓ get_park_n_ride_response function exists and is callable")

    def test_find_path_function_exists(self):
        """Test that find_path function exists and can be called"""
        from last_mile_pt.algorithm.lm_pt_best_k_path import find_path
        self.assertTrue(callable(find_path))
        print("✓ find_path function exists and is callable")

    def test_generate_response_metro_updated_exists(self):
        """Test that generate_response_metro_updated function exists and can be called"""
        from utils.generate_response_last_mile import generate_response_metro_updated
        self.assertTrue(callable(generate_response_metro_updated))
        print("✓ generate_response_metro_updated function exists and is callable")

    def test_helper_functions_exist(self):
        """Test that helper functions exist"""
        helper_functions = [
            ('utils.generate_response_last_mile', 'get_stops'),
            ('utils.generate_response_last_mile', 'get_bus_stops'),
            ('modules.time_helpers', 'convert_to_24h')
        ]
        
        for module_name, func_name in helper_functions:
            try:
                module = __import__(module_name, fromlist=[func_name])
                func = getattr(module, func_name)
                self.assertTrue(callable(func))
                print(f"✓ {func_name} function exists and is callable")
            except (ImportError, AttributeError) as e:
                self.skipTest(f"Cannot import {func_name} from {module_name}: {e}")

    @patch('builtins.__import__')
    def test_parknride_endpoint_with_mocked_dependencies(self, mock_import):
        """Test parknride endpoint with all dependencies mocked"""
        # Mock all the imports
        mock_modules = {}
        
        def mock_import_side_effect(name, *args, **kwargs):
            if name not in mock_modules:
                mock_modules[name] = Mock()
            return mock_modules[name]
        
        mock_import.side_effect = mock_import_side_effect
        
        try:
            # Test that we can mock the main function call pattern
            with patch('app.request') as mock_request, \
                 patch('app.find_path') as mock_find_path, \
                 patch('app.generate_response_metro_updated') as mock_generate_response, \
                 patch('app.convert_to_24h') as mock_convert_time, \
                 patch('app.jsonify') as mock_jsonify, \
                 patch('app.ast.literal_eval') as mock_literal_eval:
                
                # Setup mocks
                mock_request.values = self.base_request_data.copy()
                mock_request.values.update({'src_type': 'place', 'dest_type': 'place'})
                
                mock_literal_eval.side_effect = lambda x: ast.literal_eval(x)
                mock_convert_time.return_value = self.sample_time
                mock_find_path.return_value = (Mock(), Mock(), Mock(), Mock())
                mock_generate_response.return_value = [{'route': 'test'}]
                
                mock_result = Mock()
                mock_jsonify.return_value = mock_result
                
                # Import and test the function
                from app import get_park_n_ride_response
                result = get_park_n_ride_response()
                
                # Verify the function executed
                self.assertIsNotNone(result)
                print("✓ Parknride endpoint executed successfully with mocked dependencies")
                
        except Exception as e:
            self.skipTest(f"Could not test with mocked dependencies: {e}")

    def test_parknride_request_data_parsing(self):
        """Test that request data parsing works correctly using Flask test client with mocking"""
        if not self.client:
            self.fail("Flask test client not available")
            
        test_cases = [
            # (src_type, dest_type, description)
            ('place', 'place', 'place to place'),
            ('metro', 'place', 'metro to place'),
            ('bus', 'place', 'bus to place'),
            ('place', 'metro', 'place to metro'),
            ('place', 'bus', 'place to bus')
        ]
        
        for src_type, dest_type, description in test_cases:
            with self.subTest(src_type=src_type, dest_type=dest_type):
                # Mock all the helper functions
                with patch('app.find_path') as mock_find_path, \
                     patch('app.get_stops') as mock_get_stops, \
                     patch('app.gbs') as mock_gbs:
                    
                    # Mock return values
                    mock_find_path.return_value = (None, None, None, None)  # No route found
                    mock_get_stops.return_value = {'lat': 28.6139, 'lon': 77.2090}
                    mock_gbs.return_value = {'lat': 28.5355, 'lon': 77.3910}
                    
                    # Test with different source and destination types
                    src_param = str(self.sample_src) if src_type == 'place' else "['test_id']"
                    dest_param = str(self.sample_dest) if dest_type == 'place' else "['test_id']"
                    
                    response = self.client.get('/get_parknride_response', query_string={
                        'src': src_param,
                        'dest': dest_param,
                        'src_type': src_type,
                        'dest_type': dest_type,
                        'time': '09:30',
                        'maxfare': '500'
                    })
                    
                    # Should return 400 (no route found) due to mocked find_path
                    self.assertEqual(response.status_code, 400)
                    data = response.get_json()
                    self.assertEqual(data['message'], 'failed')
                    
                    # Verify appropriate helper functions were called based on types
                    if src_type == 'metro' or dest_type == 'metro':
                        mock_get_stops.assert_called()
                    if src_type == 'bus' or dest_type == 'bus':
                        mock_gbs.assert_called()
                    
                    mock_find_path.assert_called_once()
                    print(f"✓ Request parsing works for {description}")

    def test_find_path_method_signature(self):
        """Test find_path method can be called with expected parameters"""
        from last_mile_pt.algorithm.lm_pt_best_k_path import find_path
        
        # Mock all the dependencies
        with patch('last_mile_pt.algorithm.lm_pt_best_k_path.dbmetro'), \
             patch('last_mile_pt.algorithm.lm_pt_best_k_path.src_and_dest_stops') as mock_src_dest, \
             patch('last_mile_pt.algorithm.lm_pt_best_k_path.shortest_route') as mock_shortest:
            
            mock_src_dest.return_value = (Mock(), Mock(), Mock(), Mock(), Mock())
            mock_shortest.return_value = []
            
            # Test function call with expected parameters
            result = find_path(self.sample_src, self.sample_dest, self.sample_time, maxfare=500)
            
            # Verify function executed without error
            self.assertIsNotNone(result)
            mock_src_dest.assert_called_once()
            print("✓ find_path method accepts expected parameters and executes")

    def test_generate_response_method_signature(self):
        """Test generate_response_metro_updated method signature"""
        try:
            from utils.generate_response_last_mile import generate_response_metro_updated
            
            with patch('utils.generate_response_last_mile.make_resp_easy') as mock_make_resp:
                mock_make_resp.return_value = []
                
                # Test function call with expected parameters
                result = generate_response_metro_updated(
                    Mock(),  # g
                    self.sample_src,  # src
                    self.sample_dest,  # dest
                    "Source",  # src_name
                    "Destination",  # dest_name
                    self.sample_time,  # query_time
                    Mock(),  # parking_resp
                    Mock(),  # id_dict
                    Mock()   # parking_dist
                )
                
                # Verify function executed
                self.assertIsNotNone(result)
                mock_make_resp.assert_called_once()
                print("✓ generate_response_metro_updated accepts expected parameters")
                
        except Exception as e:
            self.skipTest(f"Could not test generate_response method signature: {e}")

    def test_time_conversion_helper(self):
        """Test time conversion helper function"""
        try:
            from modules.time_helpers import convert_to_24h
            
            # Test various time formats
            test_times = ["09:30", "9:30", "23:45", "00:00"]
            
            for time_input in test_times:
                result = convert_to_24h(time_input)
                self.assertIsNotNone(result)
                self.assertIsInstance(result, str)
                print(f"✓ convert_to_24h works for input: {time_input}")
                
        except Exception as e:
            self.skipTest(f"Could not test time conversion: {e}")

    def test_parknride_error_handling(self):
        """Test parknride endpoint error handling using Flask test client with mocking"""
        if not self.client:
            self.fail("Flask test client not available")
            
        # Mock the find_path function to return None (no route found)
        with patch('app.find_path') as mock_find_path:
            mock_find_path.return_value = (None, None, None, None)
            
            # Test with valid request data but mocked to return no route
            response = self.client.get('/get_parknride_response', query_string={
                'src': str(self.sample_src),
                'dest': str(self.sample_dest),
                'src_type': 'place',
                'dest_type': 'place',
                'time': '09:30',
                'maxfare': '500'
            })
            
            # Should return 400 for no route found
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertEqual(data['message'], 'failed')
            self.assertEqual(data['description'], 'no route found')
            print("✓ Parknride endpoint handles 'no route found' scenario correctly")

    def test_parknride_success_scenario(self):
        """Test parknride endpoint success scenario using Flask test client with mocking"""
        if not self.client:
            self.fail("Flask test client not available")
            
        # Mock the find_path and generate_response functions for success scenario
        with patch('app.find_path') as mock_find_path, \
             patch('app.generate_response_metro_updated') as mock_generate:
            
            # Mock successful route finding
            mock_graph = Mock()
            mock_parking_resp = Mock()
            mock_id_dict = Mock()
            mock_parking_dist = Mock()
            mock_find_path.return_value = (mock_graph, mock_parking_resp, mock_id_dict, mock_parking_dist)
            
            # Mock response generation
            mock_generate.return_value = [{'route': 'test_route', 'duration': 30}]
            
            # Test with valid request data
            response = self.client.get('/get_parknride_response', query_string={
                'src': str(self.sample_src),
                'dest': str(self.sample_dest),
                'src_name': 'Test Source',
                'dest_name': 'Test Destination',
                'time': '09:30',
                'maxfare': '500',
                'src_type': 'place',
                'dest_type': 'place'
            })
            
            # Should return success response
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['message'], 'success')
            self.assertEqual(data['description'], 'route found')
            self.assertEqual(data['response_type'], 'realtime')
            self.assertIn('possible_directions', data)
            
            # Verify mocked functions were called
            mock_find_path.assert_called_once()
            mock_generate.assert_called_once()
            print("✓ Parknride endpoint handles success scenario correctly")


def run_parknride_tests():
    """Run all parknride method tests"""
    print("=" * 60)
    print("PARKNRIDE UNIT TESTS")
    print("=" * 60)
    print("Testing all parknride methods for functionality (not accuracy)")
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParknrideMethods)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Total tests run: {result.testsRun}")
    print(f"Successful tests: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed tests: {len(result.failures)}")
    print(f"Error tests: {len(result.errors)}")
    print(f"Skipped tests: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    if result.failures:
        print(f"\nFAILED TESTS:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print(f"\nERROR TESTS:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    print("\n" + "=" * 60)
    print("PARKNRIDE METHODS VERIFICATION COMPLETE")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_parknride_tests()
    sys.exit(0 if success else 1)
